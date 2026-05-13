"""
upload.py
---------
API endpoints for document upload and AI-powered extraction.

POST /upload/vendor  → uploads a vendor profile document
POST /upload/tender  → uploads a tender document

Pipeline for each:
  1. Receive uploaded file
  2. Save to local disk (UPLOAD_DIR)
  3. Extract text via PyMuPDF
  4. Send text to Groq LLM → structured JSON + keywords
  5. Build search_text from extracted fields
  6. Generate embeddings (sentence-transformers → FAISS)
  7. Persist document record to MongoDB (with embedding_id)
  8. Return structured response
"""

import os
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends
from typing import List

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.pdf_service import extract_text_from_bytes
from app.services.groq_service import extract_with_groq
from app.services.embedding_service import get_embedding_service
from app.models.document import build_search_text, document_helper
from app.schemas.document import DocumentUploadResponse
from app.tasks.document_tasks import process_document_task
from fastapi_limiter.depends import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Document Upload"])

# ─── Allowed MIME / extension check ──────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
}
MAX_FILE_SIZE_MB = 20


# ─── Shared internal pipeline ────────────────────────────────────────────────

async def _process_upload(file: UploadFile, doc_type: str, current_user: dict) -> DocumentUploadResponse:
    """
    Core pipeline: read → validate → extract text → LLM → store.
    Returns the serialised document record.
    """
    # 1. Read bytes
    file_bytes = await file.read()

    # 2. Basic validation
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file_size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB."
        )

    filename = file.filename or "unnamed_document"
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 3. Save file to disk
    upload_dir = os.path.join(settings.UPLOAD_DIR, doc_type)
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    logger.info("[Upload] Saved %s → %s", filename, file_path)

    # 4. Save initial document to MongoDB with status "processing"
    now = datetime.utcnow()
    mongo_doc = {
        "type": doc_type,
        "original_filename": filename,
        "uploaded_by": str(current_user["_id"]),
        "org_id": current_user.get("org_id"),
        "status": "processing",
        "task_id": None,
        "structured_data": {},
        "keywords": [],
        "search_text": "",
        "raw_text": "",
        "file_url": file_path,
        "embedding_id": None,
        "keyword_embeddings": [],
        "created_at": now,
    }

    db = get_db()
    result = await db.documents.insert_one(mongo_doc)
    inserted_id = result.inserted_id
    mongo_doc["_id"] = inserted_id

    # 5. Enqueue background Celery task
    try:
        task = process_document_task.delay(str(inserted_id), file_path, doc_type)
        task_id = task.id
        logger.info("[Celery] Dispatched document processing task %s for doc %s", task_id, inserted_id)
        
        # Update task_id in DB
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"task_id": task_id}}
        )
        mongo_doc["task_id"] = task_id
    except Exception as exc:
        logger.error("[Celery] Failed to dispatch background task: %s", exc)
        # Mark as failed in DB
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"status": "failed", "error_detail": f"Failed to enqueue background processing: {exc}"}}
        )
        mongo_doc["status"] = "failed"

    # 6. Return response immediately with "processing" status
    serialised = document_helper(mongo_doc)
    return DocumentUploadResponse(**serialised)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/vendor",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a vendor document for AI extraction",
    description=(
        "Upload a vendor profile or capability document (PDF/TXT). "
        "The system extracts structured data and semantic keywords using Groq LLM "
        "and stores the result in MongoDB."
    ),
)
async def upload_vendor_document(
    file: UploadFile = File(..., description="Vendor document (PDF or TXT, max 20 MB)"),
    current_user: dict = Depends(get_current_user),
):
    return await _process_upload(file, doc_type="vendor", current_user=current_user)


@router.post(
    "/tender",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a tender document for AI extraction",
    description=(
        "Upload a government or enterprise tender document (PDF/TXT). "
        "The system extracts scope, eligibility, certifications, technical specs, "
        "keywords, and stores everything in MongoDB for matching."
    ),
)
async def upload_tender_document(
    file: UploadFile = File(..., description="Tender document (PDF or TXT, max 20 MB)"),
    current_user: dict = Depends(get_current_user),
):
    return await _process_upload(file, doc_type="tender", current_user=current_user)

@router.get(
    "/my-documents",
    response_model=List[DocumentUploadResponse],
    summary="Get logged in user's uploaded documents",
)
async def get_my_documents(
    doc_type: str = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    query = {"uploaded_by": str(current_user["_id"])}  
    if doc_type:
        query["type"] = doc_type
    
    docs = await db.documents.find(query).sort("created_at", -1).to_list(100)
    return [DocumentUploadResponse(**document_helper(doc)) for doc in docs]


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentUploadResponse,
    summary="Get status and details of a single uploaded document",
)
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    from bson import ObjectId
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID format")
        
    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    # Check tenant access
    user_id_str = str(current_user["_id"])
    user_org_id = current_user.get("org_id")
    
    if doc.get("uploaded_by") != user_id_str and doc.get("org_id") != user_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this document")
        
    return DocumentUploadResponse(**document_helper(doc))


