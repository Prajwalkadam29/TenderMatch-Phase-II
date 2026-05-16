import os
import asyncio
import logging
from bson import ObjectId
from datetime import datetime, timezone
from sqlalchemy import text, select, update
import uuid

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db
from app.core.postgres import get_pg_session
from app.services.pdf_service import extract_text_from_bytes
from app.services.groq_service import extract_with_groq
from app.services.embedding_service import get_embedding_service
from app.models.document import build_search_text
from app.db.models.document import Tender, VendorProfile

logger = logging.getLogger(__name__)

def run_async(coro):
    """Run an async coroutine synchronously inside the Celery worker thread."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

# ─── Chunking Logic (P0) ──────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """
    Split long document text into overlapping chunks to avoid LLM context window issues
    and improve embedding granularity.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

# ─── Vector Persistence ───────────────────────────────────────────────────────

async def _save_tender_vector(mongo_id: str, vector: list[float], org_id: str = None):
    """Save tender embedding and mongo_id bridge to Postgres."""
    async with get_pg_session() as session:
        vec_str = f"[{','.join(map(str, vector))}]"
        
        # Check if exists
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
        # Find the latest active vendor profile for this user
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
            logger.warning("[Celery] No active VendorProfile found in Postgres for user %s. Embedding not saved.", user_id)

# ─── Task Implementation ──────────────────────────────────────────────────────

@celery_app.task(name="process_document_task", bind=True)
def process_document_task(self, doc_id_str: str, file_path: str, doc_type: str):
    logger.info("[Celery] Starting processing of document %s, type: %s", doc_id_str, doc_type)
    
    db = get_celery_db()
    
    try:
        # 1. Read file bytes
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at: {file_path}")
            
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        filename = os.path.basename(file_path)
        
        # 2. Extract text
        raw_text = extract_text_from_bytes(file_bytes, filename)
        logger.info("[Celery] Extracted %d chars from %s", len(raw_text), filename)
        
        # 3. Handle large documents via chunking (P0 Improvement)
        # For now, we use the first chunk for LLM extraction to get structured fields,
        # but in the future, we could aggregate results from all chunks.
        chunks = chunk_text(raw_text)
        process_text = chunks[0] if chunks else raw_text
        
        # 4. Call Groq LLM (with basic retry logic)
        logger.info("[Celery] Running Groq LLM extraction for %s", filename)
        llm_result = run_async(extract_with_groq(process_text))
        
        structured_data = llm_result.get("structured_data", {})
        keywords = llm_result.get("keywords", [])
        
        # 5. Build denormalized search_text
        search_text = build_search_text(structured_data, keywords)
        
        # 6. Generate embedding and save to PostgreSQL (Polyglot Sync)
        try:
            logger.info("[Celery] Generating embedding...")
            emb_service = get_embedding_service()
            doc_vector = emb_service.encode_text_sync(search_text)
            
            # Fetch doc metadata from Mongo to get uploaded_by/org_id
            mongo_doc = db.documents.find_one({"_id": ObjectId(doc_id_str)})
            uploaded_by = mongo_doc.get("uploaded_by")
            org_id = mongo_doc.get("org_id")

            if doc_type == "tender":
                run_async(_save_tender_vector(doc_id_str, doc_vector, org_id))
            elif doc_type == "vendor":
                run_async(_save_vendor_vector(uploaded_by, doc_vector))
            
        except Exception as emb_exc:
            logger.warning("[Celery] Persistence to Postgres failed: %s", emb_exc)
            
        # 7. Update document in MongoDB (Tenders stay here, Vendor uploads are archived)
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "completed",
                "structured_data": structured_data,
                "keywords": keywords,
                "search_text": search_text,
                "raw_text": raw_text[:50_000], # Cap size in Mongo
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        # 8. Trigger real-time notifications for high-match vendors (P2 Feature)
        if doc_type == "tender":
            try:
                from app.tasks.notification_tasks import run_match_and_notify_task
                run_match_and_notify_task.delay(doc_id_str, org_id)
                logger.info("[Celery] Dispatched Match & Notify task for tender %s", doc_id_str)
            except Exception as notify_exc:
                logger.warning("[Celery] Failed to dispatch notifications: %s", notify_exc)

        logger.info("[Celery] Process document SUCCESS for %s", doc_id_str)
        return {"status": "success", "doc_id": doc_id_str}
        
    except Exception as exc:
        logger.error("[Celery] Process document FAILED: %s", exc, exc_info=True)
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "failed",
                "error_detail": str(exc),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        raise exc
