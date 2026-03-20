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

    # 4. Extract text from document
    try:
        raw_text = extract_text_from_bytes(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        )

    logger.info("[Extract] Extracted %d chars from '%s'", len(raw_text), filename)

    # 5. Call Groq LLM
    try:
        llm_result = await extract_with_groq(raw_text)
    except Exception as exc:
        # Catch ALL Groq SDK exceptions (AuthenticationError, APIStatusError,
        # network timeouts, etc.) — not just ValueError
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM extraction failed: {type(exc).__name__}: {exc}"
        )

    structured_data: dict = llm_result.get("structured_data", {})
    keywords: list = llm_result.get("keywords", [])

    logger.info("[LLM] Extracted %d keywords", len(keywords))

    # 6. Build denormalized search_text
    search_text = build_search_text(structured_data, keywords)

    # 7. Generate embeddings and add to FAISS index
    embedding_id: int | None = None
    keyword_embeddings: list = []
    try:
        emb_service = get_embedding_service()
        emb_result = await emb_service.add_document(
            mongo_id="pending",        # placeholder — updated after DB insert
            search_text=search_text,
            keywords=keywords,
        )
        embedding_id = emb_result["embedding_id"]
        keyword_embeddings = emb_result["keyword_embeddings"]
        logger.info("[Embedding] Assigned faiss_id=%s", embedding_id)
    except Exception as exc:
        # Embedding is non-fatal — document is still stored and usable
        logger.warning("[Embedding] Failed (non-fatal): %s", exc)

    # 8. Build MongoDB document
    now = datetime.utcnow()
    mongo_doc = {
        "type": doc_type,
        "original_filename": filename,
        "uploaded_by": str(current_user["_id"]),
        "org_id": current_user.get("org_id"),
        "structured_data": structured_data,
        "keywords": keywords,
        "search_text": search_text,
        "raw_text": raw_text[:50_000],
        "file_url": file_path,
        "embedding_id": embedding_id,
        "keyword_embeddings": keyword_embeddings,
        "created_at": now,
    }

    db = get_db()
    result = await db.documents.insert_one(mongo_doc)
    inserted_id = result.inserted_id
    mongo_doc["_id"] = inserted_id

    # 9. Patch FAISS mapping with the real mongo_id now that we have it
    if embedding_id is not None:
        try:
            emb_service = get_embedding_service()
            emb_service._mapping[embedding_id] = str(inserted_id)
            emb_service._persist()
        except Exception as exc:
            logger.warning("[Embedding] Mapping patch failed: %s", exc)

    logger.info("[DB] Document inserted with _id=%s", inserted_id)

    # 10. Return serialised response
    serialised = document_helper(mongo_doc)
    return DocumentUploadResponse(**serialised)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/vendor",
    response_model=DocumentUploadResponse,
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

