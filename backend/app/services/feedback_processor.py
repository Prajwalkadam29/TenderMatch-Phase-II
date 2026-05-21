"""
feedback_processor.py
---------------------
Processes user feedback signals to adjust dimension weights using EMA.
"""

import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.postgres import get_pg_session
from app.db.models.document import VendorProfileWeight
from app.services.weight_resolver import WeightResolver, GLOBAL_DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)

SIGNAL_VALUES = {
    "won": 1.0,
    "submitted": 0.6,
    "interested": 0.3,
    "not_relevant": -0.4,
    "lost": -0.2
}

LEARNING_RATE = 0.05
DIMENSIONS = [
    "domain", "geography", "financial", 
    "experience", "certification", "semantic", "confidence"
]

# Map backend dimension names to breakdown keys if they differ
BREAKDOWN_MAP = {
    "domain": "domain_fit",
    "geography": "geography_fit",
    "financial": "financial_capacity",
    "experience": "experience_track_record",
    "certification": "certifications_compliance",
    "semantic": "capability_similarity",
    "confidence": "confidence_score"
}

async def process_match_feedback(
    match_id: str,
    signal: str,
    vendor_profile_id: str,
    org_id: str = None
) -> dict:
    """
    Fetches the match score breakdown from MongoDB, calculates the new weights using EMA,
    and upserts both Org-level and Profile-level weights to PostgreSQL.
    """
    signal_lower = signal.lower()
    if signal_lower not in SIGNAL_VALUES:
        raise ValueError(f"Unknown signal: {signal}")
        
    signal_val = SIGNAL_VALUES[signal_lower]
    
    # 1. Fetch match result from MongoDB
    db = get_db()
    res = await db.match_results.find_one({"match_result._meta.match_id": match_id})
    if not res:
        # Fallback check just in case
        from bson import ObjectId
        if ObjectId.is_valid(match_id):
            res = await db.match_results.find_one({"_id": ObjectId(match_id)})
            
    if not res:
        raise ValueError(f"Match not found: {match_id}")

    breakdown = res.get("match_result", {}).get("weighted_score", {}).get("breakdown", {})
    if not breakdown:
        logger.warning(f"No score breakdown found for match {match_id}. Cannot update weights.")
        return {"status": "skipped", "reason": "no_breakdown"}
        
    # Extract raw scores (0-100) from breakdown. If not found, assume 50 (neutral).
    raw_scores = {}
    for dim in DIMENSIONS:
        bd_key = BREAKDOWN_MAP[dim]
        # the breakdown has {"raw_score": ..., "weighted_score": ...} or similar depending on pipeline.
        # Direct pipeline produces round(score * 100).
        # We will extract it.
        val = 0.0
        if isinstance(breakdown.get(bd_key), dict):
            val = breakdown[bd_key].get("raw_score", 0.5) * 100
        elif isinstance(breakdown.get(bd_key), (int, float)):
            val = breakdown[bd_key]
        else:
            # Fallback for old schema if it doesn't match
            val = 50.0
            
        raw_scores[dim] = max(0.0, float(val))
        
    total_raw = sum(raw_scores.values())
    if total_raw <= 0:
        total_raw = 1.0

    # Target distribution based on this match's raw scores
    target_dist = {dim: (raw_scores[dim] / total_raw) for dim in DIMENSIONS}

    async with get_pg_session() as session:
        # Update Vendor Profile Level
        vp_weights = await _upsert_and_update_weights(
            session=session,
            target_dist=target_dist,
            signal_val=signal_val,
            vendor_profile_id=vendor_profile_id,
            org_id=None
        )
        
        # Update Org Level
        org_weights = None
        if org_id:
            org_weights = await _upsert_and_update_weights(
                session=session,
                target_dist=target_dist,
                signal_val=signal_val,
                vendor_profile_id=None,
                org_id=org_id
            )
            
        await session.commit()
        
    return {
        "status": "success",
        "vendor_weights_updated": vp_weights,
        "org_weights_updated": org_weights
    }


async def _upsert_and_update_weights(
    session: AsyncSession,
    target_dist: dict,
    signal_val: float,
    vendor_profile_id: str = None,
    org_id: str = None
) -> dict:
    vp_uuid = uuid.UUID(vendor_profile_id) if vendor_profile_id else None
    org_uuid = uuid.UUID(org_id) if org_id else None
    
    # 1. Fetch current weights
    stmt = select(VendorProfileWeight)
    if vp_uuid:
        stmt = stmt.where(VendorProfileWeight.vendor_profile_id == vp_uuid)
    else:
        stmt = stmt.where((VendorProfileWeight.org_id == org_uuid) & (VendorProfileWeight.vendor_profile_id.is_(None)))
        
    record = await session.scalar(stmt)
    
    if not record:
        # Get fallback weights if record doesn't exist
        fallback_weights = await WeightResolver.get_weights(
            session=session,
            vendor_profile_id=vendor_profile_id if vendor_profile_id else "",
            org_id=org_id if org_id else ""
        )
        
        record = VendorProfileWeight(
            vendor_profile_id=vp_uuid,
            org_id=org_uuid,
            weight_domain=fallback_weights.get("domain", GLOBAL_DEFAULT_WEIGHTS["domain"]),
            weight_geography=fallback_weights.get("geography", GLOBAL_DEFAULT_WEIGHTS["geography"]),
            weight_financial=fallback_weights.get("financial", GLOBAL_DEFAULT_WEIGHTS["financial"]),
            weight_experience=fallback_weights.get("experience", GLOBAL_DEFAULT_WEIGHTS["experience"]),
            weight_certification=fallback_weights.get("certification", GLOBAL_DEFAULT_WEIGHTS["certification"]),
            weight_semantic=fallback_weights.get("semantic", GLOBAL_DEFAULT_WEIGHTS["semantic"]),
            weight_confidence=fallback_weights.get("confidence", GLOBAL_DEFAULT_WEIGHTS["confidence"]),
            total_feedback_count=0
        )
        session.add(record)
        
    # 2. Calculate EMA update
    current_weights = {
        "domain": record.weight_domain,
        "geography": record.weight_geography,
        "financial": record.weight_financial,
        "experience": record.weight_experience,
        "certification": record.weight_certification,
        "semantic": record.weight_semantic,
        "confidence": record.weight_confidence
    }
    
    new_weights = {}
    for dim in DIMENSIONS:
        current = current_weights[dim]
        target = target_dist[dim]
        
        # EMA Formula: new = current + alpha * signal * (target - current)
        delta = target - current
        updated = current + (LEARNING_RATE * signal_val * delta)
        
        # Clamp between 0.001 and 1.0 to prevent a weight from completely zeroing out
        new_weights[dim] = max(0.001, min(1.0, updated))
        
    # Normalize
    normalized = WeightResolver.normalize_weights(new_weights)
    
    # 3. Apply updates to record
    record.weight_domain = normalized["domain"]
    record.weight_geography = normalized["geography"]
    record.weight_financial = normalized["financial"]
    record.weight_experience = normalized["experience"]
    record.weight_certification = normalized["certification"]
    record.weight_semantic = normalized["semantic"]
    record.weight_confidence = normalized["confidence"]
    record.total_feedback_count += 1
    
    return normalized
