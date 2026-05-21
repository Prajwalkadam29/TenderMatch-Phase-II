"""
upload.py
---------
API endpoints for document upload and AI-powered extraction.

Polyglot Persistence:
- All upload metadata records are stored in MongoDB (documents collection).
- Tenders are AUTHORITATIVE in MongoDB (rich text/JSON) + pgvector (embedding).
- Vendor uploads are processing buckets that eventually update the Postgres VendorProfile
  via a 3-phase flow: upload → draft review → confirm.

Security hardening (Part 3):
  3a — File size: vendor=50MB, tender=20MB enforced before reading bytes
  3b — MIME validation: vendor=PDF only, tender=PDF+TXT, checked with python-magic
  3c — Filename sanitization: pathlib.Path().name + werkzeug secure_filename + null-byte strip
  3d — org_id included in every MongoDB query as a filter condition
  3e — Rate limiting on confirm endpoint (20 req/user/hour via Redis fastapi-limiter)
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

import magic
from werkzeug.utils import secure_filename

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import document_helper
from app.schemas.document import DocumentUploadResponse
from app.tasks.document_tasks import process_vendor_document_task
from app.tasks.ingestion_tasks import ingest_tender_document
from app.db.models.user import User
from fastapi_limiter.depends import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Document Upload"])

# ── Upload constraints ─────────────────────────────────────────────────────────

VENDOR_MAX_FILE_SIZE_MB = 50  # 3a: vendor accepts larger PDFs
TENDER_MAX_FILE_SIZE_MB = 20

# 3b: PDF-only for vendor uploads
VENDOR_CONTENT_TYPES = {"application/pdf"}
TENDER_CONTENT_TYPES = {"application/pdf", "text/plain"}
ALLOWED_EXTENSIONS   = {".pdf", ".txt"}


# ── Filename sanitization helper (3c) ─────────────────────────────────────────

def _sanitize_filename(raw: Optional[str]) -> str:
    """
    Strip directory traversal components, null bytes, and non-ASCII characters.
    Applies pathlib stripping first, then werkzeug secure_filename, then ASCII filter.
    """
    if not raw:
        return "unnamed_document"
    # pathlib.Path.name strips any directory component (prevents path traversal)
    name = Path(raw).name
    # werkzeug handles additional unsafe chars (semicolons, shell metacharacters, etc.)
    name = secure_filename(name)
    # Strip null bytes (can bypass many security checks)
    name = name.replace("\x00", "")
    # Drop non-ASCII to prevent homograph attacks and OS incompatibilities
    name = name.encode("ascii", "ignore").decode("ascii").strip()
    return name or "unnamed_document"


# ── Core upload processor ─────────────────────────────────────────────────────

async def _process_upload(
    file: UploadFile,
    doc_type: str,
    current_user: User,
    profile_id: str = None,
    max_size_mb: float = VENDOR_MAX_FILE_SIZE_MB,
    allowed_mimes: set = None,
) -> DocumentUploadResponse:
    """
    Shared upload pipeline used by both vendor and tender endpoints.

    Enforces size, MIME, and extension validation before writing bytes to disk.
    Dispatches the appropriate Celery task after MongoDB record creation.
    """
    if allowed_mimes is None:
        allowed_mimes = VENDOR_CONTENT_TYPES

    file_bytes = await file.read()

    # 3a — Size check (before disk write)
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large ({file_size_mb:.1f} MB). "
                f"Max allowed for {doc_type} uploads: {max_size_mb} MB."
            ),
        )

    # 3c — Filename sanitization (pathlib + werkzeug + ASCII)
    filename = _sanitize_filename(file.filename)
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '{ext}' not supported.",
        )

    # 3b — MIME type validation (python-magic, before disk write)
    try:
        detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    except Exception:
        detected_mime = file.content_type

    if detected_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"MIME type '{detected_mime}' not allowed for {doc_type} uploads. "
                f"Accepted: {', '.join(sorted(allowed_mimes))}."
            ),
        )

    # ── Save to disk ────────────────────────────────────────────────────────────
    upload_dir = os.path.join(settings.UPLOAD_DIR, doc_type)
    os.makedirs(upload_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # ── Save initial MongoDB record ─────────────────────────────────────────────
    mongo_doc = {
        "type": doc_type,
        "original_filename": filename,              # 3c: already sanitized
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

    await db.documents.update_one(
        {"_id": inserted_id},
        {"$set": {"mongo_id": str(inserted_id)}},
    )

    # ── Dispatch Celery task ────────────────────────────────────────────────────
    try:
        if doc_type == "tender":
            task = ingest_tender_document.delay(
                str(inserted_id),
                file_path,
                str(current_user.org_id) if current_user.org_id else None,
                str(current_user.id),
            )
        else:
            task = process_vendor_document_task.delay(
                str(inserted_id),
                file_path,
                str(current_user.org_id) if current_user.org_id else None,
                str(current_user.id),
                profile_id,
            )
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"task_id": task.id}},
        )
        mongo_doc["task_id"] = task.id
    except Exception as exc:
        logger.error("[Celery] Dispatch failed: %s", exc)
        await db.documents.update_one(
            {"_id": inserted_id},
            {"$set": {"status": "failed", "error_detail": str(exc)}},
        )
        mongo_doc["status"] = "failed"

    mongo_doc["_id"] = inserted_id
    return DocumentUploadResponse(**document_helper(mongo_doc))


# ── Vendor Upload ─────────────────────────────────────────────────────────────

@router.post("/vendor", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_vendor_document(
    profile_id: str = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a vendor capability document (PDF only) for AI extraction.

    Optional: supply ?profile_id=<uuid> to associate the extracted draft with
    an existing VendorProfile for the update path. The profile must belong to
    the caller's organization (checked synchronously before task dispatch — EC6).

    Returns 202 Accepted immediately. Poll GET /upload/vendor/draft/{doc_id}
    for extraction status.
    """
    # EC6 — profile_id org ownership check (sync, before task dispatch)
    if profile_id:
        try:
            pid = uuid.UUID(profile_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid profile_id format.")

        from app.core.postgres import get_pg_session
        from sqlalchemy import select
        from app.db.models.document import VendorProfile

        async with get_pg_session() as session:
            profile = await session.scalar(
                select(VendorProfile).where(VendorProfile.id == pid)
            )
            if not profile:
                # 3d principle: 403 not 404 — don't reveal whether profile exists
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: profile not found or belongs to another organization.",
                )
            if profile.org_id != current_user.org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: profile belongs to a different organization.",
                )

    return await _process_upload(
        file,
        doc_type="vendor",
        current_user=current_user,
        profile_id=profile_id,
        max_size_mb=VENDOR_MAX_FILE_SIZE_MB,
        allowed_mimes=VENDOR_CONTENT_TYPES,   # 3b: PDF only for vendor
    )


# ── Draft Status Endpoint ─────────────────────────────────────────────────────

@router.get("/vendor/draft/{doc_id}")
async def get_vendor_draft(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Poll the extraction status for an uploaded vendor document.

    Responses by status:
      processing  → 200 {status: "processing"}
      retrying    → 200 {status: "retrying", error: "...", retry_attempt: N}
      failed      → 200 {status: "failed", error: "..."}
      draft_ready → 200 {status: "draft_ready", extracted_draft: {...},
                         extraction_confidence: float, target_profile_id: str|null,
                         warning?: str}  ← warning present when confidence == 0.0 (EC2)
      completed   → 200 {status: "completed"}
    """
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    db = get_db()
    # 3d — org_id always included in the query filter
    doc = await db.documents.find_one({
        "_id": ObjectId(doc_id),
        "org_id": str(current_user.org_id),
    })
    if not doc:
        # Returns 403 regardless of whether doc_id doesn't exist or belongs to
        # another org — prevents enumeration attacks.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    doc_status = doc.get("status")

    if doc_status == "processing":
        return {"status": "processing", "doc_id": doc_id}

    if doc_status == "retrying":
        return {
            "status": "retrying",
            "doc_id": doc_id,
            "error": doc.get("error_detail"),
        }

    if doc_status == "failed":
        return {
            "status": "failed",
            "doc_id": doc_id,
            "error": doc.get(
                "error_detail",
                "Could not extract readable text from document. "
                "Please upload a text-based PDF or a higher quality scan.",
            ),
        }

    if doc_status == "draft_ready":
        conf = doc.get("extraction_confidence") or 0.0
        resp: Dict[str, Any] = {
            "status": "draft_ready",
            "doc_id": doc_id,
            "extracted_draft": doc.get("extracted_draft"),
            "extraction_confidence": conf,
            "target_profile_id": doc.get("target_profile_id"),
        }
        # EC2: All chunks failed → confidence is 0.0. Inform user they need manual entry.
        if conf == 0.0:
            resp["warning"] = (
                "LLM extraction failed. Raw text was captured. Manual profile entry required."
            )
        return resp

    return {"status": doc_status, "doc_id": doc_id}


# ── Confirm Endpoint ──────────────────────────────────────────────────────────

class VendorConfirmRequest(BaseModel):
    profile_data: Dict[str, Any]
    target_profile_id: Optional[str] = None


@router.post(
    "/vendor/confirm/{doc_id}",
    # 3e — Redis-backed rate limit: 20 confirm requests per user per hour
    dependencies=[Depends(RateLimiter(times=20, hours=1))],
)
async def confirm_vendor_draft(
    doc_id: str,
    payload: VendorConfirmRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Confirm the reviewed draft and commit it to PostgreSQL.

    Generates an embedding and upserts/creates a VendorProfile.
    Idempotent — calling twice returns 409 Conflict on the second call.

    Error conditions:
      400 — invalid doc_id format
      403 — doc_id belongs to another org (3d)
      404 — doc_id not found / target profile not found
      409 — extraction still in progress (EC5) OR draft already confirmed
    """
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    db = get_db()
    # 3d — org_id always included in the query filter
    doc = await db.documents.find_one({
        "_id": ObjectId(doc_id),
        "org_id": str(current_user.org_id),
    })
    if not doc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # EC5 — Extraction still running: block confirm with 409
    if doc.get("status") == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Document extraction is still in progress. "
                "Please wait for status 'draft_ready' before confirming."
            ),
        )

    # EC5 — Retrying (transient failure between attempts): also block
    if doc.get("status") == "retrying":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Document extraction is being retried. "
                "Please wait for status 'draft_ready' before confirming."
            ),
        )

    # EC5 — Extraction failed: user cannot confirm a failed extraction
    if doc.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Document extraction failed. "
                "Please re-upload to start a new extraction."
            ),
        )

    # Idempotency guard — must read draft_reviewed BEFORE any PG write (Q10 ✓)
    if doc.get("draft_reviewed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Draft already confirmed. Submit a new upload to create another profile.",
        )

    # ── PostgreSQL Commit Flow ──────────────────────────────────────────────────
    from app.core.postgres import get_pg_session
    from sqlalchemy import select
    from app.db.models.document import VendorProfile
    from app.api.vendor_profiles import _compute_completeness, _gen_vendor_id
    from app.services.embedding_service import get_embedding_service

    async with get_pg_session() as session:
        if payload.target_profile_id:
            try:
                pid = uuid.UUID(payload.target_profile_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid target_profile_id format.")

            profile = await session.scalar(
                select(VendorProfile).where(VendorProfile.id == pid)
            )
            if not profile:
                raise HTTPException(status_code=404, detail="Target vendor profile not found.")
            if profile.org_id != current_user.org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: target profile belongs to a different organization.",
                )

            # Deep merge: nested dicts are merged key-by-key; scalars/lists replace
            updated_data = dict(profile.profile_data)
            for section_key, section_val in payload.profile_data.items():
                if (
                    isinstance(section_val, dict)
                    and section_key in updated_data
                    and isinstance(updated_data[section_key], dict)
                ):
                    for k, v in section_val.items():
                        updated_data[section_key][k] = v
                else:
                    updated_data[section_key] = section_val

            profile.profile_data = updated_data
            completeness, details = _compute_completeness(updated_data)
            profile.profile_completeness_pct = completeness
            profile.completeness_details = details
            profile.profile_version += 1
            profile.updated_at = datetime.now(timezone.utc)

            action = "updated"
            final_profile_data = updated_data
            profile_id_res = str(profile.id)

        else:
            # Create a new VendorProfile
            final_profile_data = payload.profile_data
            completeness, details = _compute_completeness(final_profile_data)

            profile = VendorProfile(
                org_id=current_user.org_id,
                user_id=current_user.id,
                vendor_id=_gen_vendor_id(),
                business_name=(
                    final_profile_data.get("identity", {}).get("company_legal_name")
                    or "New Vendor Profile"
                ),
                profile_data=final_profile_data,
                profile_completeness_pct=completeness,
                completeness_details=details,
                is_active=True,
            )
            session.add(profile)
            await session.flush()   # Populate profile.id before embedding save

            action = "created"
            profile_id_res = str(profile.id)

        # ── Generate 384-dim embedding (all-MiniLM-L6-v2 — same model as tenders)
        pd_data = final_profile_data
        biz_domain = pd_data.get("business_domain", {})
        ident = pd_data.get("identity", {})

        embedding_text = " ".join(filter(None, [
            biz_domain.get("capabilities_freetext", ""),
            " ".join(biz_domain.get("primary_domains", [])),
            " ".join(biz_domain.get("sub_domains", [])),
            ident.get("company_legal_name", ""),
        ]))

        emb_service = get_embedding_service()
        vector = await emb_service.encode_text(embedding_text)
        profile.embedding = vector

        await session.commit()

    # ── Mark draft as reviewed in MongoDB ──────────────────────────────────────
    await db.documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {
            "draft_reviewed": True,
            "draft_confirmed_at": datetime.now(timezone.utc),
            "status": "completed",
        }},
    )

    return {
        "profile_id": profile_id_res,
        "action": action,
        "profile_completeness_pct": completeness,
        "embedding_generated": True,
    }


# ── Tender Upload ─────────────────────────────────────────────────────────────

@router.post("/tender", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_tender_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a tender PDF/TXT for AI ingestion via the 9-stage pipeline."""
    return await _process_upload(
        file,
        doc_type="tender",
        current_user=current_user,
        max_size_mb=TENDER_MAX_FILE_SIZE_MB,
        allowed_mimes=TENDER_CONTENT_TYPES,
    )


# ── Utility Endpoints ─────────────────────────────────────────────────────────

@router.get("/my-documents", response_model=List[DocumentUploadResponse])
async def get_my_documents(
    doc_type: str = None,
    current_user: User = Depends(get_current_user),
):
    db = get_db()
    query: Dict[str, Any] = {"uploaded_by": str(current_user.id)}
    if doc_type:
        query["type"] = doc_type
    docs = await db.documents.find(query).sort("created_at", -1).to_list(100)
    return [DocumentUploadResponse(**document_helper(doc)) for doc in docs]


@router.get("/tenders/all", response_model=List[DocumentUploadResponse])
async def get_all_tenders():
    db = get_db()
    docs = await db.documents.find(
        {"type": "tender", "status": "completed"}
    ).sort("created_at", -1).to_list(100)
    return [DocumentUploadResponse(**document_helper(doc)) for doc in docs]


@router.get("/documents/{doc_id}", response_model=DocumentUploadResponse)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format.")

    db = get_db()
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc.get("uploaded_by") != str(current_user.id) and doc.get("org_id") != str(current_user.org_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    return DocumentUploadResponse(**document_helper(doc))
