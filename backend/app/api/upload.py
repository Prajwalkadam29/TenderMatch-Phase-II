"""
upload.py
---------
API endpoints for document upload and AI-powered extraction.

Polyglot Persistence:
- All upload metadata records are stored in MongoDB (documents collection).
- Tenders are AUTHORITATIVE in MongoDB (rich text/JSON) + pgvector (embedding).
- Vendor uploads are processing buckets that eventually update the Postgres VendorProfile.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
import magic
from werkzeug.utils import secure_filename

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends
from typing import List
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import document_helper
from app.schemas.document import DocumentUploadResponse
from app.tasks.document_tasks import process_document_task
from app.db.models.user import User
from fastapi_limiter.depends import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Document Upload"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
}
MAX_FILE_SIZE_MB = 20

async def _process_upload(file: UploadFile, doc_type: str, current_user: User) -> DocumentUploadResponse:
    file_bytes = await file.read()

    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file_size_mb:.1f} MB). Max allowed: {MAX_FILE_SIZE_MB} MB."
        )

    filename = secure_filename(file.filename or "unnamed_document")
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{ext}' not supported."
        )

    try:
        detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    except Exception:
        detected_mime = file.content_type

    if detected_mime not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"MIME type '{detected_mime}' not allowed."
        )

    upload_dir = os.path.join(settings.UPLOAD_DIR, doc_type)
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Save initial record to MongoDB
    mongo_doc = {
        "type": doc_type,
        "original_filename": filename,
        "uploaded_by": str(current_user.id),
        "org_id": str(current_user.org_id) if current_user.org_id else None,
        "status": "processing",
        "task_id": None,
        "structured_data": {},
        "keywords": [],
        "search_text": "",
        "raw_text": "",
        "file_url": file_path,
        "created_at": datetime.now(timezone.utc),
    }

    db = get_db()
    result = await db.documents.insert_one(mongo_doc)
    inserted_id = result.inserted_id
    
    # Update with a generated mongo_id string to stay consistent across DBs
    await db.documents.update_one(
        {"_id": inserted_id},
        {"$set": {"mongo_id": str(inserted_id)}}
    )

    try:
        task = process_document_task.delay(str(inserted_id), file_path, doc_type)
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"task_id": task.id}}
        )
        mongo_doc["task_id"] = task.id
    except Exception as exc:
        logger.error("[Celery] Dispatch failed: %s", exc)
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"status": "failed", "error_detail": str(exc)}}
        )
        mongo_doc["status"] = "failed"

    mongo_doc["_id"] = inserted_id
    return DocumentUploadResponse(**document_helper(mongo_doc))

@router.post("/vendor", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_vendor_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await _process_upload(file, doc_type="vendor", current_user=current_user)

@router.post("/tender", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_tender_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await _process_upload(file, doc_type="tender", current_user=current_user)

@router.get("/my-documents", response_model=List[DocumentUploadResponse])
async def get_my_documents(
    doc_type: str = None,
    current_user: User = Depends(get_current_user),
):
    db = get_db()
    query = {"uploaded_by": str(current_user.id)}  
    if doc_type:
        query["type"] = doc_type
    
    docs = await db.documents.find(query).sort("created_at", -1).to_list(100)
    return [DocumentUploadResponse(**document_helper(doc)) for doc in docs]

@router.get("/tenders/all", response_model=List[DocumentUploadResponse])
async def get_all_tenders():
    db = get_db()
    docs = await db.documents.find({"type": "tender", "status": "completed"}).sort("created_at", -1).to_list(100)
    return [DocumentUploadResponse(**document_helper(doc)) for doc in docs]

@router.get("/documents/{doc_id}", response_model=DocumentUploadResponse)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format")
        
    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.get("uploaded_by") != str(current_user.id) and doc.get("org_id") != str(current_user.org_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    return DocumentUploadResponse(**document_helper(doc))
