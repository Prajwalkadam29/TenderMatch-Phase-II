"""
match.py
--------
Production-Grade AI Matching API (v4.0)
POST /match/run             → trigger fresh match analysis
GET  /match/history         → fetch past match results
GET  /match/{match_id}      → detailed breakdown of a specific match
GET  /match/status          → platform health & index stats
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel
from bson import ObjectId

from app.services.matching_service import run_matching_engine
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.match_result import match_helper

router = APIRouter(prefix="/match", tags=["AI Matching Engine"])

# ─── Schemas ──────────────────────────────────────────────────────────────────

class RunMatchRequest(BaseModel):
    vendor_profile_id: str
    tender_mongo_id: str
    use_langgraph: bool = False

class TaskResponse(BaseModel):
    task_id: str
    status: str

class MatchHistoryItem(BaseModel):
    match_id: str
    vendor_id: str
    tender_id: str
    final_score: float
    recommendation: str
    created_at: str
    pipeline: str

class MatchDetailResponse(BaseModel):
    match_id: str
    vendor_profile_id: str
    vendor_id: str
    tender_mongo_id: str
    matched_at: str
    pipeline: str
    semantic_score: float
    hard_filter_results: dict
    weighted_score: dict
    explanation: dict
    recommendation: str
    recommendation_detail: str
    critic_report: Optional[dict] = None
    retrieval_scores: Optional[dict] = None

class MatchFeedbackRequest(BaseModel):
    match_id: str
    signal: str

class MatchFeedbackResponse(BaseModel):
    acknowledged: bool

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_matching_run(
    req: RunMatchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Executes a fresh AI matching cycle for a specific vendor profile against a single tender.
    Returns immediately with a task_id for polling.
    """
    from app.tasks.matching_tasks import run_match_task
    import logging
    
    try:
        task = run_match_task.delay(
            vendor_profile_id=req.vendor_profile_id,
            tender_mongo_id=req.tender_mongo_id,
            org_id=str(current_user.org_id) if current_user.org_id else None,
            use_langgraph=req.use_langgraph,
        )
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        logging.error(f"[MatchAPI] Failed to dispatch match task: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue match task.")

@router.get("/status/{task_id}")
async def get_match_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Poll the status of an asynchronous matching task.
    """
    from app.core.celery_app import celery_app
    from celery.result import AsyncResult

    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        return {"task_id": task_id, "status": "PENDING"}
    elif task_result.state == 'STARTED':
        return {"task_id": task_id, "status": "STARTED"}
    elif task_result.state == 'SUCCESS':
        return {"task_id": task_id, "status": "SUCCESS", "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"task_id": task_id, "status": "FAILURE", "error": str(task_result.info)}
    else:
        return {"task_id": task_id, "status": task_result.state}

@router.get("/history", response_model=List[MatchHistoryItem])
async def get_match_history(
    vendor_profile_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the history of matching runs for the current user's organization.
    """
    db = get_db()
    
    # 1. Tenancy: get allowed vendor_profile_ids for this org from Postgres
    from app.core.postgres import get_pg_session
    from app.db.models.document import VendorProfile
    from sqlalchemy import select
    
    if not current_user.org_id:
        return []
        
    async with get_pg_session() as session:
        stmt = select(VendorProfile.id).where(VendorProfile.org_id == current_user.org_id)
        if vendor_profile_id:
            try:
                stmt = stmt.where(VendorProfile.id == uuid.UUID(vendor_profile_id))
            except ValueError:
                return []
        rows = await session.execute(stmt)
        allowed_vp_ids = [str(r[0]) for r in rows.all()]

    if not allowed_vp_ids:
        return []

    # 2. Query MongoDB
    query = {"match_result._meta.vendor_profile_id": {"$in": allowed_vp_ids}}
    
    results = await db.match_results.find(query).sort("match_result._meta.matched_at", -1).skip(offset).limit(limit).to_list(limit)
    
    history = []
    for r in results:
        mr = r.get("match_result", {})
        meta = mr.get("_meta", {})
        score = mr.get("weighted_score", {})
        history.append(MatchHistoryItem(
            match_id=meta.get("match_id", ""),
            vendor_id=meta.get("vendor_id", ""),
            tender_id=meta.get("tender_mongo_id", ""),
            final_score=score.get("final_score", 0.0),
            recommendation=mr.get("recommendation", "UNKNOWN"),
            created_at=meta.get("matched_at", ""),
            pipeline=meta.get("pipeline", "direct")
        ))
        
    return history

@router.get("/status")
async def get_matching_status():
    """Returns total tenders and active vendor profiles in the system."""
    db = get_db()
    total_tenders = await db.documents.count_documents({"type": "tender", "status": "completed"})
    total_globals = await db.documents.count_documents({"is_global": True})
    return {
        "status": "ready",
        "tenders_analyzed": total_tenders,
        "global_tenders": total_globals,
        "engine_version": "v3.0.0 (Agentic Pipeline)"
    }

@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match_detail(
    match_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetches a specific historical match result."""
    db = get_db()
    
    res = await db.match_results.find_one({"match_result._meta.match_id": match_id})
    if not res:
        # Fallback to checking by Mongo ObjectId if it's an old legacy record
        if ObjectId.is_valid(match_id):
            res = await db.match_results.find_one({"_id": ObjectId(match_id)})
        
        if not res:
            raise HTTPException(status_code=404, detail="Match not found")
            
    mr = res.get("match_result", {})
    meta = mr.get("_meta", {})
    vp_id = meta.get("vendor_profile_id")
    
    if not vp_id:
        raise HTTPException(status_code=404, detail="Invalid match record format")

    # Tenancy check
    from app.core.postgres import get_pg_session
    from app.db.models.document import VendorProfile
    from sqlalchemy import select

    async with get_pg_session() as session:
        try:
            vp = await session.scalar(select(VendorProfile).where(VendorProfile.id == uuid.UUID(vp_id)))
            if not vp or str(vp.org_id) != str(current_user.org_id):
                raise HTTPException(status_code=403, detail="Unauthorized")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid vendor ID in match record")
            
    return MatchDetailResponse(
        match_id=meta.get("match_id", ""),
        vendor_profile_id=meta.get("vendor_profile_id", ""),
        vendor_id=meta.get("vendor_id", ""),
        tender_mongo_id=meta.get("tender_mongo_id", ""),
        matched_at=meta.get("matched_at", ""),
        pipeline=meta.get("pipeline", "direct"),
        semantic_score=meta.get("semantic_score", 0.0),
        hard_filter_results=mr.get("hard_filter_results", {}),
        weighted_score=mr.get("weighted_score", {}),
        explanation=mr.get("explanation", {}),
        recommendation=mr.get("recommendation", "UNKNOWN"),
        recommendation_detail=mr.get("recommendation_detail", ""),
        critic_report=mr.get("critic_report"),
        retrieval_scores=mr.get("retrieval_scores")
    )

@router.get("/{match_id}/export")
async def export_match_proposal(
    match_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generates and returns a downloadable Word document (.docx) 
    containing a pre-filled compliance matrix and bid proposal draft.
    """
    from fastapi.responses import StreamingResponse
    from app.services.export_service import generate_bid_proposal_docx
    from app.core.postgres import get_pg_session
    from app.db.models.document import VendorProfile
    from sqlalchemy import select
    import uuid
    
    db = get_db()
    if not ObjectId.is_valid(match_id):
        raise HTTPException(status_code=400, detail="Invalid Match ID")
        
    res = await db.match_results.find_one({"_id": ObjectId(match_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Match not found")
        
    if res["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Fetch the Vendor Profile from Postgres
    async with get_pg_session() as session:
        vendor_profile = await session.scalar(
            select(VendorProfile).where(VendorProfile.id == uuid.UUID(res["vendor_profile_id"]))
        )
        if not vendor_profile:
            raise HTTPException(status_code=404, detail="Vendor Profile not found")
            
        profile_data = vendor_profile.profile_data

    # Generate document
    doc_stream = generate_bid_proposal_docx(match_data=res, vendor_profile={"profile_data": profile_data})
    
    # Safe filename
    title = res.get('tender_title', 'Tender').replace(' ', '_').replace('/', '-')
    filename = f"Bid_Proposal_{title}.docx"
    
    return StreamingResponse(
        doc_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/legacy/{vendor_id}")
async def legacy_match_bridge(
    vendor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Bridge for old frontend components that still use the vendor_id path."""
    # Find the profile for this user
    db = get_db()
    profile = await db.vendor_profiles.find_one({"user_id": str(current_user.id)})
    if not profile:
        return {"results": []}
        
    from app.services.matching_service import run_matching_engine
    results = await run_matching_engine(str(profile["_id"]), current_user=current_user)
    return {"results": results}

@router.post("/feedback", response_model=MatchFeedbackResponse)
async def submit_match_feedback(
    req: MatchFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit user feedback on a match result.
    Allowed signals: interested, not_relevant, submitted, won, lost.
    """
    valid_signals = {"interested", "not_relevant", "submitted", "won", "lost"}
    if req.signal not in valid_signals:
        raise HTTPException(status_code=400, detail=f"Invalid signal. Must be one of {valid_signals}")
        
    db = get_db()
    
    res = await db.match_results.find_one({"match_result._meta.match_id": req.match_id})
    if not res:
        if ObjectId.is_valid(req.match_id):
            res = await db.match_results.find_one({"_id": ObjectId(req.match_id)})
        if not res:
            raise HTTPException(status_code=404, detail="Match not found")
            
    mr = res.get("match_result", {})
    vp_id = mr.get("_meta", {}).get("vendor_profile_id")
    
    if not vp_id:
        raise HTTPException(status_code=404, detail="Invalid match record format")
        
    # Tenancy check
    from app.core.postgres import get_pg_session
    from app.db.models.document import VendorProfile
    from sqlalchemy import select
    import uuid

    async with get_pg_session() as session:
        try:
            vp = await session.scalar(select(VendorProfile).where(VendorProfile.id == uuid.UUID(vp_id)))
            if not vp or str(vp.org_id) != str(current_user.org_id):
                raise HTTPException(status_code=403, detail="Unauthorized")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid vendor ID in match record")
            
    # Update feedback in MongoDB
    await db.match_results.update_one(
        {"_id": res["_id"]},
        {"$set": {"feedback_signal": req.signal, "feedback_updated_at": datetime.utcnow()}}
    )
    
    # Trigger Celery task to update weights via EMA
    from app.tasks.matching_tasks import process_feedback_task
    process_feedback_task.delay(
        match_id=req.match_id,
        signal=req.signal,
        vendor_profile_id=vp_id,
        org_id=str(vp.org_id) if vp and vp.org_id else None
    )
    
    return {"acknowledged": True}


@router.get("/weights/{vendor_profile_id}")
async def get_vendor_weights(
    vendor_profile_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch the currently active learned weights for a specific vendor profile.
    Uses the 3-tier fallback logic (Vendor -> Org -> Global).
    """
    from app.core.postgres import get_pg_session
    from app.db.models.document import VendorProfile
    from app.services.weight_resolver import WeightResolver
    from sqlalchemy import select
    import uuid

    try:
        vp_uuid = uuid.UUID(vendor_profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Vendor Profile ID format")

    async with get_pg_session() as session:
        # Tenancy check
        vp = await session.scalar(select(VendorProfile).where(VendorProfile.id == vp_uuid))
        if not vp or str(vp.org_id) != str(current_user.org_id):
            raise HTTPException(status_code=403, detail="Unauthorized access to this vendor profile")

        weights = await WeightResolver.get_weights(session, vendor_profile_id, str(vp.org_id))
        
    return {"status": "success", "vendor_profile_id": vendor_profile_id, "weights": weights}
