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

class MatchScoreBreakdown(BaseModel):
    domain_fit: float
    geography_fit: float
    financial_capacity: float
    experience_track_record: float
    certifications_compliance: float
    capability_similarity: float
    confidence_score: float

class MatchDetailResponse(BaseModel):
    id: str
    tender_id: str
    tender_title: str
    final_score: float
    recommendation: str
    is_eligible: bool
    disqualification_reasons: List[str]
    score_breakdown: MatchScoreBreakdown
    explanation_text: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    created_at: str

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", response_model=List[MatchDetailResponse], status_code=201)
async def trigger_matching_run(
    req: RunMatchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Executes a fresh AI matching cycle for a specific vendor profile.
    Analyzes against all Global and Tenant-owned tenders.
    Stores results in the history for later retrieval.
    """
    db = get_db()
    
    # 1. Run Engine
    try:
        results = await run_matching_engine(
            vendor_profile_id=req.vendor_profile_id,
            current_user=current_user
        )
    except Exception as e:
        import traceback
        print(f"[ERROR] Matching Engine failed: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Engine error: {str(e)}")
    
    if not results:
        return []

    # 2. Persist to MongoDB History
    stored_results = []
    for r in results:
        # Create DB object
        db_obj = {
            "vendor_profile_id": req.vendor_profile_id,
            "user_id": str(current_user["_id"]),
            "tender_id": r["tender_id"],
            "tender_title": r["tender_title"],
            "final_score": r["final_score"],
            "recommendation": r["recommendation"],
            "is_eligible": r["is_eligible"],
            "disqualification_reasons": r["disqualification_reasons"],
            "score_breakdown": r["score_breakdown"],
            "explanation_text": r["explanation"],
            "strengths": r["strengths"],
            "weaknesses": r["weaknesses"],
            "created_at": datetime.utcnow()
        }
        res = await db.match_results.insert_one(db_obj)
        db_obj["_id"] = res.inserted_id
        stored_results.append(match_helper(db_obj))
        
    return stored_results

@router.get("/history", response_model=List[MatchDetailResponse])
async def get_match_history(
    vendor_profile_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the history of matching runs for the current user.
    """
    db = get_db()
    query = {"user_id": str(current_user["_id"])}
    if vendor_profile_id:
        query["vendor_profile_id"] = vendor_profile_id
        
    results = await db.match_results.find(query).sort("created_at", -1).to_list(100)
    return [match_helper(r) for r in results]

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
        "engine_version": "4.0.0 (Mock Production)"
    }

@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match_detail(
    match_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Fetches a specific historical match result."""
    db = get_db()
    if not ObjectId.is_valid(match_id):
        raise HTTPException(status_code=400, detail="Invalid Match ID")
        
    res = await db.match_results.find_one({"_id": ObjectId(match_id)})
    if not res:
        raise HTTPException(status_code=404, detail="Match not found")
        
    if res["user_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    return match_helper(res)

@router.get("/legacy/{vendor_id}")
async def legacy_match_bridge(
    vendor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Bridge for old frontend components that still use the vendor_id path."""
    # Find the profile for this user
    db = get_db()
    profile = await db.vendor_profiles.find_one({"user_id": str(current_user["_id"])})
    if not profile:
        return {"results": []}
        
    results = await run_matching_engine(str(profile["_id"]), current_user=current_user)
    return {"results": results}
