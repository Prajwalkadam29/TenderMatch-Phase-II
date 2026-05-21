"""
document_tasks.py
-----------------
Celery task for the vendor document auto-fill ingestion pipeline.

Flow:
  1. Read PDF bytes from disk
  2. Cascading text extraction (PyMuPDF → pdfplumber → Tesseract OCR)
     via shared pdf_service — same chain used by tender ingestion
  3. Zero-text guard — fails immediately without retrying (no LLM will fix a blank scan)
  4. Call VendorExtractionService for multi-chunk LLM structuring
  5. Store VendorExtractionResult as draft in MongoDB (status → draft_ready)
  6. Human review via GET /upload/vendor/draft/{doc_id}
  7. Commit confirmed data to PostgreSQL via POST /upload/vendor/confirm/{doc_id}

Chunking: imported from app.utils.text_chunker (shared with ingestion_tasks and vendor_extraction_service).
"""

import os
import asyncio
import logging
from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone
from sqlalchemy import select
import uuid

from celery.exceptions import MaxRetriesExceededError

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db
from app.core.postgres import get_pg_session
from app.services.pdf_service import extract_text_from_bytes
from app.services.embedding_service import get_embedding_service
from app.services.vendor_extraction_service import VendorExtractionService
from app.db.models.document import Tender, VendorProfile

# chunk_text is imported from the shared utility — do NOT redefine locally.
# ingestion_tasks.py uses the same import to prevent algorithm drift.
from app.utils.text_chunker import chunk_text  # noqa: F401 (re-exported for callers)

logger = logging.getLogger(__name__)

# Minimum character count required for LLM extraction to be attempted.
# A PDF yielding fewer than 50 chars is effectively blank — retrying won't help.
MIN_EXTRACTABLE_CHARS = 50


def run_async(coro):
    """Run an async coroutine synchronously inside the Celery worker thread."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


# ─── Vector Persistence (internal helpers) ────────────────────────────────────

async def _save_tender_vector(mongo_id: str, vector: list[float], org_id: str = None):
    """Save tender embedding and mongo_id bridge to Postgres."""
    async with get_pg_session() as session:
        stmt = select(Tender).where(Tender.mongo_id == mongo_id)
        result = await session.execute(stmt)
        tender = result.scalar_one_or_none()

        if tender:
            tender.embedding = vector
        else:
            new_tender = Tender(
                mongo_id=mongo_id,
                org_id=uuid.UUID(org_id) if org_id else None,
                embedding=vector
            )
            session.add(new_tender)
        await session.commit()


async def _save_vendor_vector(user_id: str, vector: list[float]):
    """Update the vendor profile embedding in Postgres for a specific user."""
    async with get_pg_session() as session:
        stmt = select(VendorProfile).where(
            VendorProfile.user_id == uuid.UUID(user_id),
            VendorProfile.is_active == True
        ).order_by(VendorProfile.created_at.desc())

        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            profile.embedding = vector
            await session.commit()
            logger.info("[Celery] Updated vector for VendorProfile %s", profile.id)
        else:
            logger.warning(
                "[Celery] No active VendorProfile found in Postgres for user %s. "
                "Embedding not saved.", user_id
            )


# ─── Vendor Document Ingestion Task ──────────────────────────────────────────

@celery_app.task(
    name="process_vendor_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def process_vendor_document_task(
    self,
    doc_id_str: str,
    file_path: str,
    org_id: str,
    user_id: str,
    profile_id: Optional[str] = None,
):
    """
    Vendor document ingestion pipeline.

    Produces a MongoDB draft (status=draft_ready) that the user reviews and
    confirms via the /upload/vendor/confirm/{doc_id} endpoint before any
    PostgreSQL write occurs.

    Retry behaviour:
      - Transient errors (network, Groq timeouts): retries up to max_retries
        with exponential backoff. Status written as "retrying" between attempts.
      - Zero-text PDF: no retry, immediate terminal "failed" status.
      - All retries exhausted (MaxRetriesExceededError): terminal "failed" status.
    """
    logger.info("[VendorTask] ═══ START ═══ doc_id=%s file=%s",
                doc_id_str, os.path.basename(file_path))
    db = get_celery_db()

    try:
        # ── Stage 1: Read PDF bytes ──────────────────────────────────────────
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at: {file_path}")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        filename = os.path.basename(file_path)
        logger.info("[VendorTask] Stage 1 ✓ Read %d bytes from %s", len(file_bytes), filename)

        # ── Stage 2: Cascading text extraction (shared fallback chain) ───────
        # Uses pdf_service.extract_text_from_bytes:
        #   PyMuPDF (fast text) → pdfplumber (table markdown) → Tesseract OCR
        # This is the SAME function used by ingest_tender_document — no drift.
        try:
            raw_text = extract_text_from_bytes(file_bytes, filename)
        except ValueError:
            # pdf_service raises ValueError when all extraction methods yield nothing
            raw_text = ""

        logger.info("[VendorTask] Stage 2 ✓ Extracted %d chars from %s",
                    len(raw_text), filename)

        # ── Stage 3: Zero-text guard ──────────────────────────────────────────
        # EC1: A completely image-based PDF returns empty/near-empty text.
        # Retrying is pointless — the content won't change. Fail immediately.
        if len(raw_text.strip()) < MIN_EXTRACTABLE_CHARS:
            logger.warning(
                "[VendorTask] Zero-text PDF for %s — terminating without retry.", doc_id_str
            )
            db.documents.update_one(
                {"_id": ObjectId(doc_id_str)},
                {"$set": {
                    "status": "failed",
                    "extracted_draft": None,
                    "error_detail": (
                        "Could not extract readable text from document. "
                        "Please upload a text-based PDF or a higher quality scan."
                    ),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            # Return normally — do NOT call self.retry() or raise. This is not
            # a transient error and should never be retried by Celery.
            return {"status": "failed", "doc_id": doc_id_str, "reason": "zero_text"}

        # ── Stage 4: Vendor LLM extraction (multi-chunk with Groq) ───────────
        # VendorExtractionService handles EC2 (Groq down) and EC3 (partial failure)
        # internally: always returns a VendorExtractionResult — never raises.
        # If all chunks fail, extraction_confidence = 0.0 and status → draft_ready.
        extraction_service = VendorExtractionService()
        result = run_async(extraction_service.extract_full_document(raw_text))
        logger.info(
            "[VendorTask] Stage 4 ✓ Extraction complete. confidence=%.3f warnings=%d",
            result.extraction_confidence, len(result.extraction_warnings),
        )

        # ── Stage 5: Store draft in MongoDB ───────────────────────────────────
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "draft_ready",
                "raw_text": raw_text[:50_000],
                "extracted_draft": result.model_dump(mode="json"),
                "extraction_confidence": result.extraction_confidence,
                "target_profile_id": profile_id,
                "user_id": user_id,
                "org_id": org_id,
                "draft_reviewed": False,
                "draft_confirmed_at": None,
                "updated_at": datetime.now(timezone.utc),
            }},
        )

        logger.info("[VendorTask] ═══ COMPLETE ═══ doc_id=%s status=draft_ready", doc_id_str)
        return {"status": "draft_ready", "doc_id": doc_id_str}

    except MaxRetriesExceededError:
        # All retry attempts exhausted — write terminal failed status once.
        logger.error("[VendorTask] Max retries exceeded for doc_id=%s", doc_id_str)
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "failed",
                "error_detail": "Extraction failed after maximum retries.",
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        raise  # Let Celery record the failure

    except Exception as exc:
        logger.error("[VendorTask] FAILED doc_id=%s error=%s", doc_id_str, exc, exc_info=True)

        retry_num = self.request.retries  # 0-indexed current attempt

        if retry_num < self.max_retries:
            # Intermediate failure — write "retrying" (not "failed") so the
            # GET /draft endpoint can show meaningful in-progress status.
            db.documents.update_one(
                {"_id": ObjectId(doc_id_str)},
                {"$set": {
                    "status": "retrying",
                    "error_detail": (
                        f"Attempt {retry_num + 1} of {self.max_retries + 1} failed: "
                        f"{str(exc)[:200]}. Retrying..."
                    ),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            # Exponential backoff: 60s, 120s, 240s
            countdown = 60 * (2 ** retry_num)
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # This is the last attempt — mark terminal failed.
            db.documents.update_one(
                {"_id": ObjectId(doc_id_str)},
                {"$set": {
                    "status": "failed",
                    "error_detail": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            raise
