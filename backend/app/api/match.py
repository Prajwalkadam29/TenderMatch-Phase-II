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
from typing import Optional, Dict, Any

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
    eligible:        bool
    final_score:     float
    tender_id:       str
    tender_filename: Optional[str]      = None
    match_result:    Dict[str, Any]     # Rich detailed report
    explanation:     Optional[str]      = None

class MatchResponse(BaseModel):
    vendor_id:    str
    total_matches: int
    results:      list[MatchResult]

class StatusResponse(BaseModel):
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
    Returns counts of documents in MongoDB and vectors in PostgreSQL.
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
        total_documents=total_docs,
        total_vendors=total_vendors,
        total_tenders=total_tenders,
    )


from fastapi_limiter.depends import RateLimiter

@router.get(
    "/{vendor_id}",
    response_model=MatchResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
    summary="Match a vendor to top-K tenders",
    description=(
        "Given a vendor document's MongoDB ID, computes semantic similarity "
        "against all indexed tenders using pgvector cosine similarity + keyword matching "
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
    2. Query PostgreSQL (pgvector) for top semantic matches
    3. Apply Hard Filters & Keyword similarity
    4. Combine scores into final_score (0-100)
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
            eligible        = m["eligible"],
            final_score     = m["final_score"],
            tender_id       = m["tender_id"],
            tender_filename = m.get("tender_filename", ""),
            match_result    = m["match_result"],
            explanation     = m.get("explanation"),
        )
        for m in matches
    ]

    return MatchResponse(
        vendor_id=vendor_id,
        total_matches=len(results),
        results=results,
    )


@router.get(
    "/{vendor_id}/{tender_id}",
    response_model=MatchResult,
    summary="Get detailed match analysis for a specific pair",
)
async def get_detailed_match(
    vendor_id: str,
    tender_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Evaluates a specific vendor against a specific tender.
    Returns the full MatchResult including breakdown and eligibility.
    """
    from bson import ObjectId
    from app.services.matching_service import _fetch_vendor_context, _evaluate_unified_score, _load_kw_matrix, _query_semantic_candidates, _generate_explanation
    
    db = get_db()
    
    # 1. Fetch Context
    vendor_doc, vendor_profile = await _fetch_vendor_context(vendor_id, db, current_user)
    if not vendor_doc:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    tender_doc = await db.documents.find_one({"_id": ObjectId(tender_id), "type": "tender"})
    if not tender_doc:
        raise HTTPException(status_code=404, detail="Tender not found")

    # 2. Get Semantic Score (specific for this pair)
    # We could re-encode or fetch from a cache, but for now we'll re-calculate or assume 0 if not indexed.
    # Actually, let's just do a quick semantic check.
    emb_svc = get_embedding_service()
    vendor_vec = await emb_svc.encode_text(vendor_doc.get("search_text", ""))
    
    from sqlalchemy import text
    from app.core.postgres import get_pg_session
    sem_score = 0.0
    async with get_pg_session() as session:
        vec_str = f"[{','.join(map(str, vendor_vec))}]"
        query = text("SELECT 1 - (embedding <=> :vec) AS sim FROM tenders WHERE mongo_id = :tid")
        res = await session.execute(query, {"vec": vec_str, "tid": tender_id})
        row = res.fetchone()
        if row:
            sem_score = float(row.sim)

    # 3. Evaluate
    vendor_kw_mat = _load_kw_matrix(vendor_doc.get("keyword_embeddings", []))
    score_data = await _evaluate_unified_score(
        vendor_doc, vendor_profile, tender_doc,
        semantic_score=sem_score,
        vendor_kw_mat=vendor_kw_mat
    )
    
    # 4. Generate Explanation (Mandatory for details page)
    score_data["explanation"] = await _generate_explanation(vendor_doc, tender_doc, score_data)

    return MatchResult(
        eligible        = score_data["eligible"],
        final_score     = score_data["final_score"],
        tender_id       = tender_id,
        tender_filename = tender_doc.get("original_filename") or tender_doc.get("filename"),
        match_result    = score_data["match_result"],
        explanation     = score_data["explanation"],
    )
