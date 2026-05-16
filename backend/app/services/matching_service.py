"""
matching_service.py
-------------------
Refactored AI Matching Engine (v5.0)

Polyglot Persistence Implementation:
- Vendor Profile is fetched from PostgreSQL.
- Tender Metadata & Embeddings are queried from PostgreSQL (pgvector).
- Full Tender Documents are fetched from MongoDB for detailed scoring.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import numpy as np
from bson import ObjectId
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.postgres import get_pg_session, get_pg_db
from app.services.embedding_service import get_embedding_service
from app.db.models.document import Tender, VendorProfile
from app.db.models.user import User
from app.db.models.organization import Organization

logger = logging.getLogger(__name__)

# ─── Scoring Configuration ───────────────────────────────────────────────────

WEIGHTS = {
    "domain": 0.25,
    "geography": 0.15,
    "financial": 0.20,
    "experience": 0.15,
    "certification": 0.10,
    "similarity": 0.10,
    "confidence": 0.05
}

SCORE_SCALE = 100.0

# ─── Public Entry Point ───────────────────────────────────────────────────────

async def run_matching_engine(
    vendor_profile_id: str,
    top_k: int = 10,
    explain: bool = True,
    current_user: User = None,
) -> list[dict]:
    """
    Matches a vendor profile (Postgres) against all active tenders (Postgres + Mongo).
    """
    mongo_db = get_db()
    emb_svc = get_embedding_service()

    # 1. Fetch Vendor Context from PostgreSQL
    try:
        vp_id = uuid.UUID(vendor_profile_id)
    except ValueError:
        logger.error(f"[Match] Invalid Vendor Profile ID format: {vendor_profile_id}")
        return []

    async with get_pg_session() as session:
        vendor_profile = await session.scalar(select(VendorProfile).where(VendorProfile.id == vp_id))
        if not vendor_profile:
            logger.error(f"[Match] Vendor Profile {vendor_profile_id} not found in Postgres.")
            return []

    # 2. Get Semantic Query Vector
    # Use business_name + capability description for embedding
    profile_data = vendor_profile.profile_data
    identity = profile_data.get("identity", {})
    business_domain = profile_data.get("business_domain", {})
    
    search_text = f"{identity.get('company_legal_name', '')} {business_domain.get('capability_description_freetext', '')}"
    vendor_vec = await emb_svc.encode_text(search_text)

    # 3. Retrieve ALL active tenders via pgvector
    semantic_scores = await _query_all_candidates(vendor_vec)
    if not semantic_scores:
        return []

    tender_ids = [mid for mid in semantic_scores.keys()]
    
    # 4. Filter by tenancy in MongoDB
    # org_id is a UUID in Postgres, needs to be string for Mongo if that's how it's stored
    org_id = str(current_user.org_id) if current_user and current_user.org_id else None
    
    tenant_filter = {"$or": [{"is_global": True}]}
    if org_id:
        tenant_filter["$or"].append({"org_id": org_id})
    elif current_user:
        tenant_filter["$or"].append({"uploaded_by": str(current_user.id)})

    raw_tenders = await mongo_db.documents.find({
        "mongo_id": {"$in": tender_ids}, # Assuming we store the mongo_id field in the doc itself now
        "type": "tender",
        "status": "completed",
        **tenant_filter
    }).to_list(length=200)

    # 5. Evaluation Loop
    results = []
    for tender_doc in raw_tenders:
        match_data = await _evaluate_mock_production_score(
            vendor_profile, 
            tender_doc, 
            semantic_score=semantic_scores.get(tender_doc["mongo_id"], 0.0)
        )
        results.append(match_data)

    # 6. Sort by score
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:top_k]


# ─── Core Logic ───────────────────────────────────────────────────────────────

async def _evaluate_mock_production_score(
    vendor: VendorProfile, 
    tender: dict,
    semantic_score: float
) -> dict:
    """
    Weighted scoring logic.
    vendor: VendorProfile ORM object
    tender: dict from MongoDB
    """
    tender_sd = tender.get("structured_data", {})
    profile_data = vendor.profile_data
    
    # --- 1. Deterministic Hard Filters ---
    reasons = []
    
    # HF-1: Sector/Domain Match
    vendor_sector = profile_data.get("business_domain", {}).get("primary_domains", [])
    tender_sector = str(tender_sd.get("sector", ""))
    sector_pass = any(str(s).lower() in tender_sector.lower() for s in vendor_sector) if vendor_sector else True
    if not sector_pass: 
        reasons.append(f"Domain Mismatch: Vendor ({vendor_sector}) vs Tender ({tender_sector})")
    
    # HF-2: Turnover Requirement
    min_turnover = tender_sd.get("min_turnover", 0)
    vendor_turnover = profile_data.get("financials", {}).get("avg_annual_turnover_inr", 0)
    turnover_pass = vendor_turnover >= min_turnover
    if not turnover_pass: 
        reasons.append(f"Financial Ineligibility: Turnover below required {min_turnover:,}")

    # HF-3: Geography
    tender_loc = str(tender_sd.get("location", "")).lower()
    geo = profile_data.get("geography", {})
    op_states = [s.lower() for s in geo.get("operational_states", [])]
    geo_pass = True
    if not geo.get("willing_to_operate_in_new_states", False) and op_states:
        geo_pass = any(s in tender_loc for s in op_states)
        if not geo_pass: 
            reasons.append(f"Geography Restriction: Vendor not operating in {tender_loc}")

    # HF-4: Compliance
    compliance = profile_data.get("compliance", {})
    comp_pass = not compliance.get("blacklisted_or_debarred", False)
    if not comp_pass: 
        reasons.append("Security Risk: Vendor is blacklisted/debarred.")

    is_eligible = len(reasons) == 0

    # --- 2. Weighted Soft Scoring ---
    
    # A. Domain Fit (25%)
    score_domain = 0.9 if sector_pass else 0.3
    
    # B. Geography Fit (15%)
    score_geo = 0.5
    if geo_pass:
        score_geo = 1.0 if any(s in tender_loc for s in op_states) else 0.7
    elif geo.get("willing_to_operate_in_new_states", False):
        score_geo = 0.6
    
    # C. Financial Capacity (20%)
    score_fin = 0.4
    if turnover_pass:
        ratio = vendor_turnover / (min_turnover or 1)
        score_fin = 1.0 if ratio > 5 else (0.8 if ratio > 2 else 0.6)

    # D. Experience (15%)
    projects = profile_data.get("past_project_experience", {}).get("projects", [])
    min_exp = tender_sd.get("min_experience_years", 0)
    total_exp = len(projects) * 3
    score_exp = min(1.0, total_exp / (min_exp or 5))

    # E. Certifications (10%)
    req_certs = tender_sd.get("certifications", [])
    v_certs_raw = profile_data.get("certifications", {}).get("iso_certifications", [])
    v_certs = [str(c.get("standard", "")).lower() for c in v_certs_raw if isinstance(c, dict)]
    v_certs += [str(c).lower() for c in v_certs_raw if isinstance(c, str)]
    
    cert_matches = [c for c in req_certs if str(c).lower() in v_certs]
    score_certs = len(cert_matches) / len(req_certs) if req_certs else 1.0

    # F. Capability Similarity (10%)
    score_sim = max(0.0, min(1.0, semantic_score))

    # G. Confidence / Completeness (5%)
    score_conf = vendor.profile_completeness_pct / 100.0

    # Final Weighted Calculation
    final_raw = (
        WEIGHTS["domain"] * score_domain +
        WEIGHTS["geography"] * score_geo +
        WEIGHTS["financial"] * score_fin +
        WEIGHTS["experience"] * score_exp +
        WEIGHTS["certification"] * score_certs +
        WEIGHTS["similarity"] * score_sim +
        WEIGHTS["confidence"] * score_conf
    )
    
    if not is_eligible:
        final_raw *= 0.5

    final_score = round(final_raw * 100, 1)

    # Labels
    if final_score >= 85: label = "Strongly Recommended"
    elif final_score >= 70: label = "Recommended"
    elif final_score >= 50: label = "Partially Suitable"
    else: label = "Weak Fit / Not Eligible"

    return {
        "tender_id": str(tender.get("_id")),
        "mongo_id": tender.get("mongo_id"),
        "tender_title": tender_sd.get("title", "Untitled Tender"),
        "sector": tender_sector,
        "deadline": tender_sd.get("submission_deadline"),
        "final_score": final_score,
        "recommendation": label,
        "is_eligible": is_eligible,
        "disqualification_reasons": reasons,
        "score_breakdown": {
            "domain_fit": round(score_domain * 100, 1),
            "geography_fit": round(score_geo * 100, 1),
            "financial_capacity": round(score_fin * 100, 1),
            "experience_track_record": round(score_exp * 100, 1),
            "certifications_compliance": round(score_certs * 100, 1),
            "capability_similarity": round(score_sim * 100, 1),
            "confidence_score": round(score_conf * 100, 1)
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _query_all_candidates(vendor_vec: list[float]) -> Dict[str, float]:
    """Search pgvector for ALL similar tenders."""
    results = {}
    async with get_pg_session() as session:
        vec_str = f"[{','.join(map(str, vendor_vec))}]"
        query = text("""
            SELECT mongo_id, 1 - (embedding <=> :vec) AS sim
            FROM tenders
            ORDER BY embedding <=> :vec
            LIMIT 200
        """)
        pg_results = await session.execute(query, {"vec": vec_str})
        for row in pg_results:
            results[row.mongo_id] = float(row.sim)
    return results

async def match_tender_to_all_vendors(
    tender_mongo_id: str,
    org_id: str | None = None,
    threshold: float = 75.0
) -> int:
    """
    Called after a new tender is processed.
    Matches it against all active vendor profiles for the target organization.
    Returns the number of notifications triggered.
    """
    from app.tasks.notification_tasks import send_match_notification_email
    
    mongo_db = get_db()
    
    # 1. Fetch Tender from Mongo
    tender_doc = await mongo_db.documents.find_one({"_id": ObjectId(tender_mongo_id)})
    if not tender_doc:
        logger.error(f"[Notify] Tender {tender_mongo_id} not found in Mongo.")
        return 0

    # 2. Fetch Tender Vector from Postgres
    async with get_pg_session() as session:
        pg_tender = await session.scalar(select(Tender).where(Tender.mongo_id == tender_mongo_id))
        if not pg_tender or pg_tender.embedding is None:
            logger.error(f"[Notify] Tender {tender_mongo_id} has no embedding in Postgres.")
            return 0
        tender_vec = pg_tender.embedding

        # 3. Fetch all active VendorProfiles for this Org
        # We also fetch the associated user to get their email address.
        stmt = (
            select(VendorProfile, User)
            .join(User, VendorProfile.user_id == User.id)
            .where(
                VendorProfile.org_id == uuid.UUID(org_id) if org_id else None,
                VendorProfile.is_active == True
            )
        )
        profile_results = await session.execute(stmt)
        active_profiles = profile_results.all()

    # 4. Evaluation Loop
    notified_count = 0
    for profile_orm, user_orm in active_profiles:
        # Calculate semantic score (cosine similarity)
        # 1 - (A <=> B) in pgvector is cosine similarity
        # Here we manually compute it using the ORM objects if we had the vectors,
        # but for simplicity, we use the evaluate function.
        # Note: profile_orm.embedding is the vector.
        
        sim = 0.0
        if profile_orm.embedding and tender_vec:
            v_vec = np.array(profile_orm.embedding)
            t_vec = np.array(tender_vec)
            sim = float(np.dot(v_vec, t_vec) / (np.linalg.norm(v_vec) * np.linalg.norm(t_vec)))

        match_data = await _evaluate_mock_production_score(
            profile_orm, 
            tender_doc, 
            semantic_score=sim
        )
        
        score = match_data["final_score"]
        if score >= threshold:
            logger.info(f"[Notify] High match ({score}%) for {user_orm.email} on {tender_doc.get('original_filename')}")
            
            # Trigger asynchronous email task
            send_match_notification_email.delay(
                vendor_email=user_orm.email,
                vendor_name=user_orm.name,
                tender_title=match_data["tender_title"],
                match_score=score,
                explanation=match_data["explanation_text"] if "explanation_text" in match_data else match_data.get("recommendation", "")
            )
            notified_count += 1
            
    return notified_count
