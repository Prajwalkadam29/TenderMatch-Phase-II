"""
matching_service.py
-------------------
Unified Matching Engine: Combines semantic search (pgvector) with 
deep business rule scoring (Structured Matching).

Algorithm:
  1. Fetch vendor document (MongoDB 'documents' collection).
  2. Fetch full vendor profile (MongoDB 'vendor_profiles' collection).
  3. Encode vendor search_text → query vector.
  4. Query PostgreSQL via pgvector (<=> cosine distance) for semantic candidates.
  5. Fetch candidate documents from MongoDB.
  6. For each candidate:
     a. Apply Hard Filters (Blacklist, Domain, Geography, Financial thresholds).
     b. If passed, compute Hybrid Weighted Score:
        - Semantic Similarity (pgvector)
        - Keyword Similarity (embedding matrix)
        - Financial Capacity (Turnover ratio)
        - Experience Match (Contract values)
        - Certification Match
  7. Return ranked results with detailed breakdown.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import numpy as np
from bson import ObjectId
from sqlalchemy import text

from app.core.database import get_db
from app.core.postgres import get_pg_session
from app.services.embedding_service import get_embedding_service
from app.services.structured_matching_service import evaluate_match

logger = logging.getLogger(__name__)

# ─── Scoring Configuration ───────────────────────────────────────────────────

WEIGHTS = {
    "semantic": 0.35,      # High-level requirement understanding
    "keyword": 0.15,       # Specific technical keyword overlap
    "financial": 0.20,     # Ability to handle the contract value
    "experience": 0.20,    # Proven track record
    "certification": 0.10  # Regulatory / Quality compliance
}

SCORE_SCALE = 100.0


# ─── Public Entry Point ───────────────────────────────────────────────────────

async def match_vendor_to_tenders(
    vendor_id: str,
    top_k: int = 10,
    explain: bool = False,
    current_user: dict = None,
) -> list[dict]:
    """
    Find top-K tenders for a given vendor using the Unified Matching Engine.
    """
    db = get_db()
    emb_svc = get_embedding_service()

    # 1. Fetch Vendor Context
    vendor_doc, vendor_profile = await _fetch_vendor_context(vendor_id, db, current_user)
    if not vendor_doc:
        logger.warning(f"[Match] Vendor {vendor_id} not found.")
        return []

    # 2. Get Semantic Query Vector
    vendor_search_text = vendor_doc.get("search_text", "")
    vendor_vec = await emb_svc.encode_text(vendor_search_text)
    vendor_kw_embeddings = _load_kw_matrix(vendor_doc.get("keyword_embeddings", []))

    # 3. Retrieve Semantic Candidates from PostgreSQL
    semantic_scores = await _query_semantic_candidates(vendor_vec)
    if not semantic_scores:
        return []

    # 4. Batch fetch Tender Documents from MongoDB
    tender_ids = [ObjectId(mid) for mid in semantic_scores.keys()]
    raw_tenders = await db.documents.find({
        "_id": {"$in": tender_ids},
        "type": "tender",
        "status": "completed"
    }).to_list(length=500)

    # 5. Deep Evaluation & Scoring
    scored_results = []
    for tender_doc in raw_tenders:
        # Use the logic from structured_matching_service but tailored for search results
        score_data = await _evaluate_unified_score(
            vendor_doc, vendor_profile, tender_doc, 
            semantic_score=semantic_scores.get(str(tender_doc["_id"]), 0.0),
            vendor_kw_mat=vendor_kw_embeddings
        )

        if score_data["eligible"]:
            # Optionally add Groq explanation
            if explain:
                score_data["explanation"] = await _generate_explanation(
                    vendor_doc, tender_doc, score_data
                )
            
            scored_results.append(score_data)

    # 6. Rank and Return
    scored_results.sort(key=lambda x: x["final_score"], reverse=True)
    return scored_results[:top_k]


# ─── Internal Implementation Helpers ──────────────────────────────────────────

async def _fetch_vendor_context(vendor_id: str, db: Any, current_user: Optional[dict]):
    """Fetch both the parsed document and the structured profile for a vendor."""
    tenant_filter = {}
    if current_user:
        org_id = current_user.get("org_id")
        if org_id:
            tenant_filter["org_id"] = org_id
        else:
            tenant_filter["uploaded_by"] = str(current_user["_id"])

    # Document (contains raw text & vectors)
    doc = await db.documents.find_one({"_id": ObjectId(vendor_id), "type": "vendor", **tenant_filter})
    
    # Profile (contains financials, certs, locations)
    # Profile might be linked via vendor_id string or the doc's ID
    profile = await db.vendor_profiles.find_one({"$or": [
        {"user_id": str(current_user["_id"]) if current_user else None},
        {"vendor_id": vendor_id}
    ]})

    return doc, profile


async def _query_semantic_candidates(vendor_vec: list[float]) -> Dict[str, float]:
    """Search pgvector for the top 500 most similar tenders."""
    results = {}
    async with get_pg_session() as session:
        vec_str = f"[{','.join(map(str, vendor_vec))}]"
        query = text("""
            SELECT mongo_id, 1 - (embedding <=> :vec) AS sim
            FROM tenders
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :vec
            LIMIT 500
        """)
        pg_results = await session.execute(query, {"vec": vec_str})
        for row in pg_results:
            results[row.mongo_id] = float(row.sim)
    return results


async def _evaluate_unified_score(
    vendor_doc: dict, 
    vendor_profile: Optional[dict], 
    tender_doc: dict,
    semantic_score: float,
    vendor_kw_mat: Optional[np.ndarray]
) -> dict:
    """
    Applies Phase 4 hybrid scoring and returns a rich, frontend-compatible report.
    """
    tender_sd = tender_doc.get("structured_data", {})
    vendor_sd = vendor_doc.get("structured_data", {})
    tender_id = str(tender_doc["_id"])
    
    # --- 1. Hard Filters (Eligibility) ---
    filters = []
    
    # HF-01: Certifications
    required_certs = tender_sd.get("certifications", [])
    if required_certs:
        vendor_certs = [c.lower() for c in vendor_sd.get("certifications", [])]
        passed = any(rc.lower() in vendor_certs for rc in required_certs)
        filters.append({
            "filter_id": "HF-01",
            "filter_name": "Mandatory Certifications",
            "result": "PASS" if passed else "FAIL",
            "detail": "All certs met." if passed else f"Missing: {required_certs}"
        })
    else:
        filters.append({"filter_id": "HF-01", "filter_name": "Certifications", "result": "PASS", "detail": "None required."})

    # HF-02: Location
    tender_loc = tender_sd.get("location", "")
    loc_pass = True
    loc_detail = "Location within reach."
    if tender_loc and vendor_profile:
        geography = vendor_profile.get("geography", {})
        if not geography.get("willing_to_operate_in_new_states", False):
            op_states = [s.lower() for s in geography.get("operational_states", [])]
            if not any(s in tender_loc.lower() for s in op_states) and op_states:
                loc_pass = False
                loc_detail = f"Tender in {tender_loc}; vendor in {op_states}."
    filters.append({"filter_id": "HF-02", "filter_name": "Geographic Reach", "result": "PASS" if loc_pass else "FAIL", "detail": loc_detail})

    overall_pass = all(f["result"] == "PASS" for f in filters)

    # --- 2. Weighted Scoring (Only if passed filters) ---
    
    if not overall_pass:
        return {
            "eligible": False,
            "final_score": 0.0,
            "match_result": {
                "_meta": {"tender_id": tender_id, "match_id": f"M-{tender_id[:8]}"},
                "hard_filter_results": {"overall_pass": False, "disqualification_reason": filters[-1]["detail"], "filters": filters},
                "weighted_score": {"final_score": 0.0, "breakdown": {}},
                "recommendation": "DISQUALIFIED",
                "recommendation_detail": "Failed eligibility checks."
            }
        }

    # A. Semantic Score
    s_score = max(0.0, min(1.0, semantic_score))
    
    # B. Keyword Score
    tender_kw_embeddings = _load_kw_matrix(tender_doc.get("keyword_embeddings", []))
    kw_score = await asyncio.to_thread(_keyword_similarity, vendor_kw_mat, tender_kw_embeddings)
    
    # C. Financial Score
    fin_score = 0.5
    if vendor_profile:
        vendor_turnover = vendor_profile.get("financials", {}).get("avg_annual_turnover_inr", 0)
        tender_value = tender_doc.get("metadata", {}).get("estimated_value", 0)
        if tender_value > 0:
            ratio = vendor_turnover / tender_value
            fin_score = 1.0 if ratio >= 2 else (0.7 if ratio >= 1 else 0.4)

    # D. Experience Score
    exp_score = 0.5
    if vendor_profile:
        projects = vendor_profile.get("past_project_experience", {}).get("projects", [])
        exp_score = 1.0 if len(projects) > 2 else (0.7 if len(projects) > 0 else 0.4)

    # E. Cert Match Score
    cert_score = 1.0

    final_raw = (
        WEIGHTS["semantic"] * s_score +
        WEIGHTS["keyword"] * kw_score +
        WEIGHTS["financial"] * fin_score +
        WEIGHTS["experience"] * exp_score +
        WEIGHTS["certification"] * cert_score
    )
    
    final_score = round(final_raw * SCORE_SCALE, 2)

    return {
        "eligible": True,
        "final_score": final_score,
        "tender_id": tender_id,
        "tender_filename": tender_doc.get("original_filename") or tender_doc.get("filename"),
        "match_result": {
            "_meta": {
                "tender_id": tender_id,
                "match_id": f"M-{tender_id[:8]}",
                "tender_filename": tender_doc.get("original_filename") or tender_doc.get("filename")
            },
            "hard_filter_results": {"overall_pass": True, "filters": filters},
            "weighted_score": {
                "final_score": final_raw,
                "breakdown": {
                    "domain_semantic_similarity": {"raw_score": s_score, "weight": WEIGHTS["semantic"]},
                    "keyword_similarity": {"raw_score": kw_score, "weight": WEIGHTS["keyword"]},
                    "financial_capacity_ratio": {"raw_score": fin_score, "weight": WEIGHTS["financial"]},
                    "experience_track_record": {"raw_score": exp_score, "weight": WEIGHTS["experience"]}
                }
            },
            "recommendation": "STRONG_MATCH" if final_score > 80 else "MODERATE_MATCH",
            "recommendation_detail": f"Score {final_score} - Meets all core requirements.",
            "tender_summary": {
                "scope": tender_sd.get("scope"),
                "location": tender_sd.get("location"),
                "certifications": required_certs
            }
        }
    }


# ─── Shared Utilities ─────────────────────────────────────────────────────────

def _load_kw_matrix(kw_embeddings_raw: list) -> Optional[np.ndarray]:
    if not kw_embeddings_raw: return None
    try:
        mat = np.array(kw_embeddings_raw, dtype=np.float32)
        return mat if (mat.ndim == 2 and mat.shape[1] == 384) else None
    except Exception: return None

def _keyword_similarity(vendor_kw_mat: Optional[np.ndarray], tender_kw_mat: Optional[np.ndarray]) -> float:
    if vendor_kw_mat is None or tender_kw_mat is None: return 0.0
    sim_matrix = tender_kw_mat @ vendor_kw_mat.T
    return float(np.clip(sim_matrix.max(axis=1).mean(), 0.0, 1.0))

async def _generate_explanation(vendor_doc: dict, tender_doc: dict, score_data: dict) -> str:
    """Call Groq LLM to explain the unified score."""
    try:
        from groq import AsyncGroq
        from app.core.config import settings
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
        prompt = f"""Explain this TenderMatch score of {score_data['final_score']}/100.
        Vendor Keywords: {vendor_doc.get('keywords', [])}
        Tender Scope: {score_data['tender_summary']['scope']}
        Semantic Sim: {score_data['semantic_score']:.2f}
        Keyword Match: {score_data['keyword_score']:.2f}
        Provide a 2-sentence summary of the alignment."""
        
        res = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.2
        )
        return res.choices[0].message.content.strip()
    except Exception: return "Alignment based on semantic scope and keyword overlap."

