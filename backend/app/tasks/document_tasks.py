import os
import asyncio
import logging
from bson import ObjectId
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db
from app.services.pdf_service import extract_text_from_bytes
from app.services.groq_service import extract_with_groq
from app.services.embedding_service import get_embedding_service
from app.models.document import build_search_text

logger = logging.getLogger(__name__)

def run_async(coro):
    """Run an async coroutine synchronously inside the Celery worker thread cleanly."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

@celery_app.task(name="process_document_task", bind=True)
def process_document_task(self, doc_id_str: str, file_path: str, doc_type: str):
    logger.info("[Celery] Starting processing of document %s, type: %s", doc_id_str, doc_type)
    
    db = get_celery_db()
    
    try:
        # 1. Read file bytes from local disk
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found at: {file_path}")
            
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        filename = os.path.basename(file_path)
        
        # 2. Extract text from document
        raw_text = extract_text_from_bytes(file_bytes, filename)
        logger.info("[Celery] Extracted %d chars from %s", len(raw_text), filename)
        
        # 3. Call Groq LLM
        logger.info("[Celery] Running Groq LLM extraction for %s", filename)
        llm_result = run_async(extract_with_groq(raw_text))
        
        structured_data = llm_result.get("structured_data", {})
        keywords = llm_result.get("keywords", [])
        
        # 4. Build denormalized search_text
        search_text = build_search_text(structured_data, keywords)
        
        # 5. Generate embeddings and add to FAISS index
        embedding_id = None
        keyword_embeddings = []
        try:
            logger.info("[Celery] Generating embeddings and updating FAISS index...")
            emb_service = get_embedding_service()
            emb_result = run_async(emb_service.add_document(
                mongo_id=doc_id_str,
                search_text=search_text,
                keywords=keywords
            ))
            embedding_id = emb_result["embedding_id"]
            keyword_embeddings = emb_result["keyword_embeddings"]
        except Exception as emb_exc:
            logger.warning("[Celery] Embedding failed (non-fatal): %s", emb_exc)
            
        # 6. Update document in MongoDB to Completed state
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "completed",
                "structured_data": structured_data,
                "keywords": keywords,
                "search_text": search_text,
                "raw_text": raw_text[:50_000],
                "embedding_id": embedding_id,
                "keyword_embeddings": keyword_embeddings,
                "updated_at": datetime.utcnow()
            }}
        )
        logger.info("[Celery] Process document SUCCESS for %s", doc_id_str)
        return {"status": "success", "doc_id": doc_id_str, "embedding_id": embedding_id}
        
    except Exception as exc:
        logger.error("[Celery] Process document FAILED: %s", exc, exc_info=True)
        # Update MongoDB doc to Failed status
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "failed",
                "error_detail": str(exc),
                "updated_at": datetime.utcnow()
            }}
        )
        raise exc
