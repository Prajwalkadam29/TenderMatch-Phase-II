import os
import asyncio
import logging
from bson import ObjectId
from datetime import datetime
from sqlalchemy import text
import uuid

from app.core.celery_app import celery_app
from app.core.celery_db import get_celery_db
from app.core.postgres import get_pg_session
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

from sqlalchemy import create_engine, text
from app.core.config import settings

def _get_sync_pg_engine():
    # Convert async URI to sync psycopg2 URI for Celery
    sync_uri = settings.POSTGRES_URI.replace("+asyncpg", "+psycopg2")
    return create_engine(sync_uri, pool_pre_ping=True)

def _save_vector_to_postgres(doc_id_str: str, doc_type: str, vector: list[float], keywords: list[str]):
    """Insert or update the generated vector into PostgreSQL."""
    vec_str = f"[{','.join(map(str, vector))}]"
    
    engine = _get_sync_pg_engine()
    new_uuid = str(uuid.uuid4())
    
    with engine.begin() as conn:
        if doc_type == "tender":
            conn.execute(
                text("INSERT INTO tenders (id, mongo_id, embedding) VALUES (:uuid, :id, :vec) ON CONFLICT (mongo_id) DO UPDATE SET embedding = EXCLUDED.embedding"),
                {"uuid": new_uuid, "id": doc_id_str, "vec": vec_str}
            )
        elif doc_type == "vendor":
            conn.execute(
                text("INSERT INTO vendor_profiles (id, mongo_id, embedding) VALUES (:uuid, :id, :vec) ON CONFLICT (mongo_id) DO UPDATE SET embedding = EXCLUDED.embedding"),
                {"uuid": new_uuid, "id": doc_id_str, "vec": vec_str}
            )

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
        
        # 5. Generate embedding and save to PostgreSQL
        embedding_id = 1  # Marker for MongoDB to satisfy schema (int or null)
        keyword_embeddings = []
        try:
            logger.info("[Celery] Generating embedding via SentenceTransformer...")
            emb_service = get_embedding_service()
            
            # Generate doc vector
            doc_vector = emb_service.encode_text_sync(search_text)
            
            # Generate keyword vectors for keyword scoring
            if keywords:
                keyword_embeddings = emb_service.encode_texts_sync(keywords)
                
            # Save strictly to PostgreSQL
            logger.info("[Celery] Writing vector to PostgreSQL...")
            _save_vector_to_postgres(doc_id_str, doc_type, doc_vector, keywords)
            
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
        db.documents.update_one(
            {"_id": ObjectId(doc_id_str)},
            {"$set": {
                "status": "failed",
                "error_detail": str(exc),
                "updated_at": datetime.utcnow()
            }}
        )
        raise exc
