"""
match.py
--------
GET /match/{vendor_id}          → top-K tender matches for a vendor
GET /match/{vendor_id}?k=5      → limit results
GET /match/{vendor_id}?explain=true  → include Groq LLM explanation per match
GET /match/status               → index statistics
"""

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel
from typing import Optional

from app.services.matching_service import match_vendor_to_tenders
from app.services.embedding_service import get_embedding_service
from app.core.database import get_db
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/match", tags=["Matching Engine"])


# ─── Response schemas ─────────────────────────────────────────────────────────

class TenderSummary(BaseModel):
    scope:          Optional[str]       = None
    location:       Optional[str]       = None
    certifications: list[str]           = []

class MatchResult(BaseModel):
    tender_id:       str
    tender_filename: str                = ""
    semantic_score:  float              # cosine sim of document embeddings [0,1]
    keyword_score:   float              # avg best-match keyword cosine sim [0,1]
    final_score:     float              # 0-100, weighted combo
    tender_summary:  TenderSummary      = TenderSummary()
    tender_keywords: list[str]          = []
    explanation:     Optional[str]      = None   # Groq explanation (only if explain=True)

class MatchResponse(BaseModel):
    vendor_id:    str
    total_matches: int
    results:      list[MatchResult]

class StatusResponse(BaseModel):
    faiss_index_size: int
    total_documents:  int
    total_vendors:    int
    total_tenders:    int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Index and database statistics",
)
async def get_match_status(current_user: dict = Depends(get_current_user)):
    """
    Returns counts of documents in MongoDB and vectors in FAISS index.
    Useful for verifying uploads went through correctly before matching.
    """
    db      = get_db()
    emb_svc = get_embedding_service()

    tenant_filter = {}
    if current_user:
        org_id = current_user.get("org_id")
        if org_id:
            tenant_filter["org_id"] = org_id
        else:
            tenant_filter["uploaded_by"] = str(current_user["_id"])

    total_docs    = await db.documents.count_documents(tenant_filter)
    total_vendors = await db.documents.count_documents({**tenant_filter, "type": "vendor"})
    total_tenders = await db.documents.count_documents({**tenant_filter, "type": "tender"})

    return StatusResponse(
        faiss_index_size=emb_svc.index_size,
        total_documents=total_docs,
        total_vendors=total_vendors,
        total_tenders=total_tenders,
    )


@router.get(
    "/{vendor_id}",
    response_model=MatchResponse,
    summary="Match a vendor to top-K tenders",
    description=(
        "Given a vendor document's MongoDB ID, computes semantic similarity "
        "against all indexed tenders using FAISS embeddings + keyword matching "
        "and returns ranked results with scores scaled 0–100."
    ),
)
async def match_vendor(
    vendor_id: str,
    k: int  = Query(default=10, ge=1, le=50, description="Number of top matches to return"),
    explain: bool = Query(default=False, description="Generate Groq LLM explanation per match"),
    current_user: dict = Depends(get_current_user),
):
    """
    Matching pipeline:
    1. Encode vendor search_text → query vector
    2. Reconstruct tender vectors from FAISS
    3. Compute semantic_doc_score + keyword_score
    4. Combine: final_score = 0.75 * doc + 0.25 * keyword  (×100)
    5. Return sorted results
    """
    if len(vendor_id) != 24:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vendor_id must be a 24-character MongoDB ObjectId string.",
        )

    matches = await match_vendor_to_tenders(
        vendor_id=vendor_id,
        top_k=k,
        explain=explain,
        current_user=current_user,
    )

    if matches is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with id '{vendor_id}' not found or has no embeddings.",
        )

    # Convert to Pydantic response models
    results = [
        MatchResult(
            tender_id       = m["tender_id"],
            tender_filename = m.get("tender_filename", ""),
            semantic_score  = m["semantic_score"],
            keyword_score   = m["keyword_score"],
            final_score     = m["final_score"],
            tender_summary  = TenderSummary(**m.get("tender_summary", {})),
            tender_keywords = m.get("tender_keywords", []),
            explanation     = m.get("explanation"),
        )
        for m in matches
    ]

    return MatchResponse(
        vendor_id=vendor_id,
        total_matches=len(results),
        results=results,
    )
