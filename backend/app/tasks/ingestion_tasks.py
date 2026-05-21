"""
ingestion_tasks.py
------------------
Production-grade Celery task for the full AI tender ingestion pipeline (v1.0).

This is the upgraded replacement for the single-chunk processing in document_tasks.py.
It implements the complete 9-stage pipeline:

  Stage 1: Read PDF bytes from disk
  Stage 2: Cascading text extraction (PyMuPDF → pdfplumber tables → Tesseract OCR)
  Stage 3: Split into 2000-char overlapping chunks (200-char overlap)
  Stage 4: Multi-chunk LLM extraction via Groq (strict 13-field schema)
  Stage 5: Intelligent multi-chunk merge (highest confidence wins, arrays unioned)
  Stage 6: Generate 384-dim embedding from synthesized search text
  Stage 7: Write structured JSON to MongoDB `documents` collection
  Stage 8: Write vector + metadata to PostgreSQL `tenders` table (bridge row)
  Stage 9: Trigger matching observer (notification_tasks)

Integration note:
  The existing `process_document_task` in document_tasks.py is preserved untouched.
  The upload API can be updated to dispatch this task instead for tender documents.
"""

import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db
from app.core.postgres import get_pg_session
from app.services.pdf_service import extract_text_from_bytes
from app.services.llm_service import extract_tender_structured_data, build_tender_search_text
from app.services.embedding_service import get_embedding_service
from app.db.models.document import Tender
# chunk_text is the shared utility — do NOT redefine locally (see app/utils/text_chunker.py)
from app.utils.text_chunker import chunk_text

logger = logging.getLogger(__name__)


# ─── Async helpers ────────────────────────────────────────────────────────────

def _run_async(coro):
    """Run an async coroutine synchronously inside a Celery worker thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)



# ─── PostgreSQL persistence ───────────────────────────────────────────────────

async def _upsert_tender_postgres(
    mongo_id: str,
    org_id: Optional[str],
    embedding: list[float],
    extracted: dict,
    filename: str,
) -> None:
    """
    Upsert the thin Tender row in PostgreSQL.
    Stores: mongo_id bridge, embedding vector, scope, location, filename, summary JSONB.
    """
    async with get_pg_session() as session:
        stmt = select(Tender).where(Tender.mongo_id == mongo_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        # Build the summary JSONB cache (key filterable fields duplicated from Mongo)
        summary = {
            "domain": extracted.get("domain"),
            "estimated_value": extracted.get("estimated_value"),
            "min_avg_turnover": extracted.get("min_avg_turnover"),
            "mandatory_certifications": extracted.get("mandatory_certifications", []),
            "deadline": extracted.get("deadline", {}),
            "extraction_confidence": extracted.get("extraction_confidence", 0.0),
            "source_portal": extracted.get("source_portal"),
            "tender_ref_id": extracted.get("tender_id"),
        }

        if existing:
            existing.embedding = embedding
            existing.scope = extracted.get("scope_summary") or ""
            existing.location = extracted.get("location_state") or ""
            existing.filename = filename
            existing.summary = summary
            logger.info("[Ingestion] PostgreSQL: updated existing tender row for mongo_id=%s", mongo_id)
        else:
            new_tender = Tender(
                mongo_id=mongo_id,
                org_id=uuid.UUID(org_id) if org_id else None,
                embedding=embedding,
                scope=extracted.get("scope_summary") or "",
                location=extracted.get("location_state") or "",
                filename=filename,
                summary=summary,
            )
            session.add(new_tender)
            logger.info("[Ingestion] PostgreSQL: inserted new tender row for mongo_id=%s", mongo_id)

        await session.commit()


# ─── Celery Task ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="ingest_tender_document",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,   # 5 min soft limit — raises SoftTimeLimitExceeded
    time_limit=360,        # 6 min hard kill — prevents zombie workers
)
def ingest_tender_document(
    self,
    doc_id_str: str,
    file_path: str,
    org_id: Optional[str] = None,
    uploaded_by: Optional[str] = None,
) -> dict:
    """
    Full 9-stage AI ingestion pipeline for a tender PDF.

    Args:
        doc_id_str:   MongoDB ObjectId string for the pre-created document record
        file_path:    Absolute path to the uploaded PDF on disk
        org_id:       Organization UUID string (for tenancy scoping in Postgres)
        uploaded_by:  User UUID string (for audit trail)

    Returns:
        dict with status, doc_id, domain, extraction_confidence, chunks_processed
    """
    logger.info(
        "[Ingestion] ═══ START ═══ doc_id=%s file=%s",
        doc_id_str, os.path.basename(file_path),
    )
    db = get_celery_db()

    try:
        # ── Stage 1: Read PDF bytes ────────────────────────────────────────────
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at: {file_path}")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        filename = os.path.basename(file_path)
        logger.info("[Ingestion] Stage 1 ✓ Read %d bytes from %s", len(file_bytes), filename)

        # ── Stage 2: Cascading text extraction ────────────────────────────────
        # pdf_service.py handles: PyMuPDF (fast text) → pdfplumber (tables as
        # markdown) → Tesseract OCR (scanned image pages)
        raw_text = extract_text_from_bytes(file_bytes, filename)
        logger.info("[Ingestion] Stage 2 ✓ Extracted %d chars from PDF", len(raw_text))

        # ── Stage 3: Chunking (2000-char, 200-char overlap) ───────────────────
        # Uses the shared utility from app.utils.text_chunker — same algorithm
        # used by VendorExtractionService to prevent drift.
        chunks = chunk_text(raw_text, chunk_size=2000, overlap=200)
        logger.info("[Ingestion] Stage 3 ✓ Created %d chunks", len(chunks))

        # ── Stages 4 & 5: Multi-chunk LLM extraction + intelligent merge ──────
        logger.info("[Ingestion] Stage 4+5: Starting multi-chunk LLM extraction...")
        extracted = _run_async(
            extract_tender_structured_data(
                full_text=raw_text,
                chunks=chunks,
                max_chunks=5,
            )
        )
        logger.info(
            "[Ingestion] Stage 4+5 ✓ Extraction complete. "
            "confidence=%.2f domain=%s location=%s",
            extracted.get("extraction_confidence", 0.0),
            extracted.get("domain", "unknown"),
            extracted.get("location_state", "unknown"),
        )

        # ── Stage 6: Generate 384-dim embedding ───────────────────────────────
        search_text = build_tender_search_text(extracted)
        logger.info("[Ingestion] Stage 6: Search text: %.150s...", search_text)

        emb_service = get_embedding_service()
        embedding_vector = emb_service.encode_text_sync(search_text)
        logger.info("[Ingestion] Stage 6 ✓ Generated 384-dim embedding vector")

        # ── Stage 7: Update MongoDB document record ────────────────────────────
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {
                "$set": {
                    "status": "completed",
                    "structured_data": extracted,
                    "search_text": search_text,
                    "raw_text": raw_text[:50_000],   # Cap to 50k chars in Mongo
                    "keywords": extracted.get("mandatory_certifications", []),
                    "domain": extracted.get("domain"),
                    "location_state": extracted.get("location_state"),
                    "extraction_confidence": extracted.get("extraction_confidence", 0.0),
                    "is_global": False,               # Tenant-scoped by default
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        logger.info("[Ingestion] Stage 7 ✓ MongoDB document updated: %s", doc_id_str)

        # ── Stage 8: Persist to PostgreSQL (vector bridge) ────────────────────
        _run_async(
            _upsert_tender_postgres(
                mongo_id=doc_id_str,
                org_id=org_id,
                embedding=embedding_vector,
                extracted=extracted,
                filename=filename,
            )
        )
        logger.info("[Ingestion] Stage 8 ✓ PostgreSQL tender row upserted")

        # ── Stage 9: Trigger matching observer ────────────────────────────────
        try:
            from app.tasks.matching_tasks import run_bulk_match_task
            run_bulk_match_task.delay(tender_mongo_id=doc_id_str, org_id=org_id)
            logger.info(
                "[Ingestion] Stage 9 ✓ Dispatched bulk match task for: %s",
                doc_id_str,
            )
        except Exception as notify_exc:
            # Non-fatal: ingestion succeeded even if notification dispatch fails
            logger.warning(
                "[Ingestion] Stage 9 ⚠ Failed to dispatch bulk match task: %s",
                notify_exc,
            )

        logger.info("[Ingestion] ═══ COMPLETE ═══ doc_id=%s", doc_id_str)
        return {
            "status": "success",
            "doc_id": doc_id_str,
            "domain": extracted.get("domain"),
            "location_state": extracted.get("location_state"),
            "extraction_confidence": extracted.get("extraction_confidence", 0.0),
            "chunks_total": len(chunks),
            "chunks_sent_to_llm": min(len(chunks), 5),
            "certifications_found": len(extracted.get("mandatory_certifications", [])),
        }

    except FileNotFoundError as exc:
        logger.error("[Ingestion] ✗ File not found: %s", exc)
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {
                "$set": {
                    "status": "failed",
                    "error_detail": f"File not found: {exc}",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        # Do NOT retry FileNotFoundError — the file won't magically appear
        raise

    except Exception as exc:
        logger.error(
            "[Ingestion] ✗ FAILED doc_id=%s error=%s",
            doc_id_str, exc, exc_info=True,
        )
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {
                "$set": {
                    "status": "failed",
                    "error_detail": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        # Exponential backoff: 60s, 120s, 240s
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
