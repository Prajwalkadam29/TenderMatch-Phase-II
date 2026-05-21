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

# ─── Hard Filter Engine ───────────────────────────────────────────────────────

class HardFilterEngine:
    """
    Pure Deterministic Hard Filters for TenderMatch.
    No LLMs used. Evaluates binary eligibility based on vendor profile and tender JSON.
    """
    
    # Common synonyms mapping for domain matching
    DOMAIN_SYNONYMS = {
        "it & software": ["information technology", "software", "it services", "tech", "it"],
        "information technology": ["it & software", "software", "it services", "tech", "it"],
        "construction": ["infrastructure", "building", "civil engineering"],
        "healthcare": ["medical", "health", "pharma", "pharmaceuticals"],
    }
    
    @classmethod
    def evaluate(cls, vendor_profile: dict, tender: dict) -> dict:
        """
        Runs all 5 sequential binary checks.
        Returns a dict indicating overall pass/fail, and the detailed results of checks.
        """
        checks = [
            cls.check_blacklist,
            cls.check_domain_match,
            cls.check_geographic_eligibility,
            cls.check_financial_threshold,
            cls.check_mandatory_certifications
        ]
        
        results = []
        for check in checks:
            res = check(vendor_profile, tender)
            results.append(res)
            if not res["passed"]:
                return {
                    "overall_pass": False,
                    "disqualification_reason": res["reason"],
                    "failed_check": res["field_checked"],
                    "check_results": results
                }
                
        return {
            "overall_pass": True,
            "disqualification_reason": None,
            "failed_check": None,
            "check_results": results
        }

    @staticmethod
    def check_blacklist(vendor: dict, tender: dict) -> dict:
        compliance = vendor.get("compliance", {})
        is_blacklisted = compliance.get("blacklisted_or_debarred", False)
        if is_blacklisted:
            return {"passed": False, "reason": "Vendor is blacklisted or debarred.", "field_checked": "blacklist_status"}
        return {"passed": True, "reason": "Vendor is not blacklisted.", "field_checked": "blacklist_status"}

    @classmethod
    def check_domain_match(cls, vendor: dict, tender: dict) -> dict:
        tender_domain = tender.get("domain")
        if not tender_domain:
            return {"passed": True, "reason": "Tender domain not specified.", "field_checked": "domain"}
            
        vendor_domains = vendor.get("business_domain", {}).get("primary_domains", [])
        if not vendor_domains:
            return {"passed": False, "reason": "Vendor has no primary domains.", "field_checked": "domain"}
            
        t_domain_lower = str(tender_domain).strip().lower()
        
        for v_dom in vendor_domains:
            v_dom_lower = str(v_dom).strip().lower()
            if v_dom_lower == t_domain_lower:
                return {"passed": True, "reason": f"Domain match: {t_domain_lower}.", "field_checked": "domain"}
                
            if t_domain_lower in cls.DOMAIN_SYNONYMS.get(v_dom_lower, []) or \
               v_dom_lower in cls.DOMAIN_SYNONYMS.get(t_domain_lower, []):
                return {"passed": True, "reason": f"Domain synonym match: {v_dom_lower} matches {t_domain_lower}.", "field_checked": "domain"}
                
            if t_domain_lower in v_dom_lower or v_dom_lower in t_domain_lower:
                return {"passed": True, "reason": f"Domain partial match: {v_dom_lower} and {t_domain_lower}.", "field_checked": "domain"}
                
        return {"passed": False, "reason": f"Domain mismatch. Tender requires {tender_domain}.", "field_checked": "domain"}

    @staticmethod
    def check_geographic_eligibility(vendor: dict, tender: dict) -> dict:
        tender_loc = tender.get("location_state")
        if not tender_loc:
            return {"passed": True, "reason": "Tender location not specified.", "field_checked": "geography"}
            
        tender_loc_lower = str(tender_loc).strip().lower()
        if tender_loc_lower in ["pan india", "global", "any"]:
            return {"passed": True, "reason": "Tender is Pan India or Global.", "field_checked": "geography"}
            
        geo = vendor.get("geography", {})
        op_states = [str(s).strip().lower() for s in geo.get("operational_states", [])]
        reg_states = [str(s).strip().lower() for s in geo.get("registered_states", [])]
        
        all_vendor_states = set(op_states + reg_states)
        
        if "pan india" in all_vendor_states or "global" in all_vendor_states:
            return {"passed": True, "reason": "Vendor operates Pan India/Global.", "field_checked": "geography"}
            
        if tender_loc_lower in all_vendor_states:
            return {"passed": True, "reason": f"Geographic match for {tender_loc}.", "field_checked": "geography"}
            
        if geo.get("willing_to_operate_in_new_states", False):
             return {"passed": True, "reason": "Vendor willing to operate in new states.", "field_checked": "geography"}
             
        return {"passed": False, "reason": f"Vendor not operating in {tender_loc}.", "field_checked": "geography"}

    @staticmethod
    def check_financial_threshold(vendor: dict, tender: dict) -> dict:
        tender_turnover = tender.get("min_avg_turnover")
        if not tender_turnover:
            return {"passed": True, "reason": "Tender does not specify minimum turnover.", "field_checked": "financials"}
            
        vendor_turnover = vendor.get("financials", {}).get("avg_annual_turnover_inr", 0)
        
        try:
            t_val = float(tender_turnover)
            v_val = float(vendor_turnover)
        except (ValueError, TypeError):
            return {"passed": True, "reason": "Could not parse turnover values.", "field_checked": "financials"}
            
        if v_val >= t_val:
            return {"passed": True, "reason": "Vendor meets financial threshold.", "field_checked": "financials"}
            
        return {"passed": False, "reason": f"Vendor turnover ({v_val}) < tender threshold ({t_val}).", "field_checked": "financials"}

    @staticmethod
    def check_mandatory_certifications(vendor: dict, tender: dict) -> dict:
        req_certs = tender.get("mandatory_certifications", [])
        if not req_certs:
            return {"passed": True, "reason": "No mandatory certifications required.", "field_checked": "certifications"}
            
        req_certs_lower = {str(c).strip().lower() for c in req_certs if str(c).strip()}
        if not req_certs_lower:
            return {"passed": True, "reason": "No valid mandatory certifications required.", "field_checked": "certifications"}
            
        certs_node = vendor.get("certifications", {})
        if isinstance(certs_node, dict):
            vendor_iso = [str(x.get("standard", "")).strip().lower() for x in certs_node.get("iso_certifications", []) if isinstance(x, dict)]
            vendor_domain = [str(x.get("license_type", "")).strip().lower() for x in certs_node.get("domain_licenses", []) if isinstance(x, dict)]
            vendor_all_certs = set(vendor_iso + vendor_domain)
        elif isinstance(certs_node, list):
            vendor_all_certs = {str(c).strip().lower() for c in certs_node}
        else:
            vendor_all_certs = set()
        
        missing = req_certs_lower - vendor_all_certs
        
        if not missing:
            return {"passed": True, "reason": "Vendor has all mandatory certifications.", "field_checked": "certifications"}
            
        return {"passed": False, "reason": f"Missing mandatory certifications: {', '.join(missing)}.", "field_checked": "certifications"}


# ─── Weighted Scoring Engine ──────────────────────────────────────────────────

class WeightedScoringEngine:
    """
    Weighted Scoring Engine for TenderMatch.
    Calculates a 0-100 score based on 7 dimensions.
    """
    
    WEIGHTS = {
        "domain": 0.25,
        "geography": 0.15,
        "financial": 0.20,
        "experience": 0.15,
        "certification": 0.10,
        "semantic": 0.10,
        "confidence": 0.05
    }

    @classmethod
    def calculate_score(cls, vendor: dict, tender: dict, semantic_score: float, custom_weights: dict = None) -> dict:
        """
        Calculates the weighted score.
        Returns the final score and a breakdown of each dimension.
        """
        weights_to_use = custom_weights if custom_weights else cls.WEIGHTS
        
        raw_scores = {
            "domain": cls.score_domain(vendor, tender),
            "geography": cls.score_geography(vendor, tender),
            "financial": cls.score_financial(vendor, tender),
            "experience": cls.score_experience(vendor, tender),
            "certification": cls.score_certification(vendor, tender),
            "semantic": max(0.0, min(1.0, semantic_score)),
            "confidence": cls.score_confidence(vendor)
        }
        
        breakdown = {}
        total_score = 0.0
        
        for dim, weight in weights_to_use.items():
            if dim not in raw_scores:
                continue
            weighted = raw_scores[dim] * weight
            total_score += weighted
            breakdown[dim] = {
                "weight": weight,
                "raw_score": round(raw_scores[dim], 3),
                "weighted_score": round(weighted, 3)
            }
            
        final_score_100 = round(total_score * 100, 2)
        
        return {
            "final_score": final_score_100,
            "breakdown": breakdown
        }

    @classmethod
    def score_domain(cls, vendor: dict, tender: dict) -> float:
        tender_domain = tender.get("domain")
        if not tender_domain:
            return 1.0
            
        vendor_domains = vendor.get("business_domain", {}).get("primary_domains", [])
        if not vendor_domains:
            return 0.0
            
        t_domain_lower = str(tender_domain).strip().lower()
        
        best_score = 0.0
        for v_dom in vendor_domains:
            v_dom_lower = str(v_dom).strip().lower()
            if v_dom_lower == t_domain_lower:
                return 1.0
            if t_domain_lower in HardFilterEngine.DOMAIN_SYNONYMS.get(v_dom_lower, []) or \
               v_dom_lower in HardFilterEngine.DOMAIN_SYNONYMS.get(t_domain_lower, []):
                best_score = max(best_score, 0.8)
            elif t_domain_lower in v_dom_lower or v_dom_lower in t_domain_lower:
                best_score = max(best_score, 0.5)
                
        return best_score

    @classmethod
    def score_geography(cls, vendor: dict, tender: dict) -> float:
        tender_loc = tender.get("location_state")
        if not tender_loc:
            return 1.0
            
        tender_loc_lower = str(tender_loc).strip().lower()
        if tender_loc_lower in ["pan india", "global", "any"]:
            return 1.0
            
        geo = vendor.get("geography", {})
        op_states = [str(s).strip().lower() for s in geo.get("operational_states", [])]
        reg_states = [str(s).strip().lower() for s in geo.get("registered_states", [])]
        
        if "pan india" in reg_states or "global" in reg_states:
            return 1.0
        if tender_loc_lower in reg_states:
            return 1.0
            
        if "pan india" in op_states or "global" in op_states:
            return 0.9
        if tender_loc_lower in op_states:
            return 0.8
            
        if geo.get("willing_to_operate_in_new_states", False):
            return 0.5
            
        return 0.0

    @classmethod
    def score_financial(cls, vendor: dict, tender: dict) -> float:
        tender_val = tender.get("estimated_value")
        if not tender_val:
            return 0.8
            
        vendor_turnover = vendor.get("financials", {}).get("avg_annual_turnover_inr", 0)
        
        try:
            t_val = float(tender_val)
            v_val = float(vendor_turnover)
        except (ValueError, TypeError):
            return 0.8
            
        if t_val <= 0:
            return 0.8
            
        ratio = v_val / t_val
        if ratio >= 3.0:
            return 1.0
        if ratio >= 2.0:
            return 0.9
        if ratio >= 1.0:
            return 0.8
        if ratio >= 0.5:
            return 0.5
        return 0.2

    @classmethod
    def score_experience(cls, vendor: dict, tender: dict) -> float:
        tender_val = tender.get("estimated_value")
        projects = vendor.get("past_project_experience", {}).get("projects", [])
        
        if not projects:
            return 0.0
            
        try:
            t_val = float(tender_val) if tender_val else 0.0
        except (ValueError, TypeError):
            t_val = 0.0
            
        largest_project = 0.0
        for p in projects:
            try:
                val = float(p.get("contract_value_inr", 0))
                if val > largest_project:
                    largest_project = val
            except (ValueError, TypeError):
                pass
                
        if t_val > 0:
            if largest_project >= t_val:
                return 1.0
            elif largest_project >= (t_val * 0.5):
                return 0.7
            else:
                return 0.4
        else:
            if len(projects) >= 5:
                return 1.0
            elif len(projects) >= 3:
                return 0.8
            return 0.5

    @classmethod
    def score_certification(cls, vendor: dict, tender: dict) -> float:
        req_certs = tender.get("mandatory_certifications", [])
        opt_certs = tender.get("optional_certifications", [])
        
        if not req_certs and not opt_certs:
            return 1.0
            
        target_certs = {str(c).strip().lower() for c in (req_certs + opt_certs) if str(c).strip()}
        if not target_certs:
            return 1.0
            
        certs_node = vendor.get("certifications", {})
        if isinstance(certs_node, dict):
            vendor_iso = [str(x.get("standard", "")).strip().lower() for x in certs_node.get("iso_certifications", []) if isinstance(x, dict)]
            vendor_domain = [str(x.get("license_type", "")).strip().lower() for x in certs_node.get("domain_licenses", []) if isinstance(x, dict)]
            vendor_all_certs = set(vendor_iso + vendor_domain)
        elif isinstance(certs_node, list):
            vendor_all_certs = {str(c).strip().lower() for c in certs_node}
        else:
            vendor_all_certs = set()
            
        match_count = len(target_certs.intersection(vendor_all_certs))
        return min(1.0, match_count / len(target_certs))

    @classmethod
    def score_confidence(cls, vendor: dict) -> float:
        pct = vendor.get("profile_completeness_pct", 50)
        try:
            return min(1.0, max(0.0, float(pct) / 100.0))
        except (ValueError, TypeError):
            return 0.5


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
            
        from app.services.weight_resolver import WeightResolver
        custom_weights = await WeightResolver.get_weights(session, str(vendor_profile.id), str(vendor_profile.org_id))

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
            semantic_score=semantic_scores.get(tender_doc["mongo_id"], 0.0),
            custom_weights=custom_weights
        )
        results.append(match_data)

    # 6. Sort by score
    results.sort(key=lambda x: x["final_score"], reverse=True)
    top_results = results[:top_k]

    # 7. Multi-Agent Evaluation: Devil's Advocate
    if explain:
        from app.services.groq_service import generate_devils_advocate_critique
        # Run critiques concurrently for speed
        critique_tasks = []
        for res in top_results:
            # Re-fetch tender for summary if needed, but we have it in raw_tenders
            # or just pass a simplified version to save tokens
            t_summary = {
                "title": res["tender_title"],
                "sector": res["sector"],
                "disqualifications": res["disqualification_reasons"]
            }
            # We don't have the full profile here easily except vendor_profile.profile_data
            critique_tasks.append(generate_devils_advocate_critique(
                vendor_profile.profile_data,
                t_summary,
                res["final_score"]
            ))
            
        critiques = await asyncio.gather(*critique_tasks)
        
        for i, res in enumerate(top_results):
            critique = critiques[i]
            res["devil_advocate"] = {
                "critical_risks": critique.get("critical_risks", []),
                "summary": critique.get("devil_advocate_summary", "")
            }
            # Adjust the final score based on the Devil's Advocate critique
            adjusted = critique.get("adjusted_score", res["final_score"])
            res["original_algorithmic_score"] = res["final_score"]
            res["final_score"] = min(res["final_score"], adjusted) # Advocate can only lower it, not raise it higher than algorithm
            
            # Re-evaluate recommendation label based on new score
            if res["final_score"] >= 85: label = "Strongly Recommended"
            elif res["final_score"] >= 70: label = "Recommended"
            elif res["final_score"] >= 50: label = "Partially Suitable"
            else: label = "Weak Fit / Not Eligible"
            res["recommendation"] = label

    # Sort again just in case the Devil's Advocate re-ordered the top K
    top_results.sort(key=lambda x: x["final_score"], reverse=True)
    return top_results


# ─── Core Logic ───────────────────────────────────────────────────────────────

async def _evaluate_mock_production_score(
    vendor: VendorProfile, 
    tender: dict,
    semantic_score: float,
    custom_weights: dict = None
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

    weights_to_use = custom_weights if custom_weights else WeightedScoringEngine.WEIGHTS
    
    # Final Weighted Calculation
    final_raw = (
        weights_to_use["domain"] * score_domain +
        weights_to_use["geography"] * score_geo +
        weights_to_use["financial"] * score_fin +
        weights_to_use["experience"] * score_exp +
        weights_to_use["certification"] * score_certs +
        weights_to_use["semantic"] * score_sim +
        weights_to_use["confidence"] * score_conf
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
            .where(VendorProfile.is_active == True)
        )
        if org_id:
            stmt = stmt.where(VendorProfile.org_id == uuid.UUID(org_id))
            
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

        # Need a session for WeightResolver, create one per iteration or open one.
        # Since we are iterating, we create a short-lived session.
        from app.services.weight_resolver import WeightResolver
        async with get_pg_session() as inner_session:
            custom_weights = await WeightResolver.get_weights(inner_session, str(profile_orm.id), str(profile_orm.org_id))
            
        match_data = await _evaluate_mock_production_score(
            profile_orm, 
            tender_doc, 
            semantic_score=sim,
            custom_weights=custom_weights
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


# ─── Match Orchestrator (Component 5) ────────────────────────────────────────

async def orchestrate_match(
    vendor_profile_id: str,
    tender_mongo_id: str,
    org_id: Optional[str] = None,
) -> dict:
    """
    Single-pair match orchestrator — the authoritative pipeline for matching
    one vendor against one tender.

    Pipeline:
      1. Fetch VendorProfile from PostgreSQL (profile_data JSONB + embedding)
      2. Fetch tender structured_data from MongoDB by mongo_id
      3. Fetch tender vector from PostgreSQL tenders table
      4. Run HardFilterEngine — fail fast on disqualification
      5. Compute semantic score via cosine similarity of embedding vectors
      6. Run WeightedScoringEngine — 7-dimension weighted score (0-100)
      7. Run LLM ExplanationEngine — structured explanation with strengths/risks
      8. Persist complete result to MongoDB match_results collection
      9. Return the complete result dict

    Args:
        vendor_profile_id:  UUID string of the VendorProfile (PostgreSQL PK)
        tender_mongo_id:    MongoDB ObjectId string of the tender document
        org_id:             Optional org UUID string for tenancy scoping

    Returns:
        Complete match result dict with all fields populated
    """
    from app.services.explanation_service import generate_explanation

    mongo_db = get_db()
    if mongo_db is None:
        from app.core.celery_db import get_celery_db
        mongo_db = get_celery_db()
    logger.info(
        "[Orchestrator] START vendor=%s tender=%s",
        vendor_profile_id, tender_mongo_id,
    )

    # ── Step 1: Fetch vendor from PostgreSQL ─────────────────────────────────
    try:
        vp_uuid = uuid.UUID(vendor_profile_id)
    except ValueError:
        raise ValueError(f"Invalid vendor_profile_id format: {vendor_profile_id}")

    async with get_pg_session() as session:
        query = select(VendorProfile).where(VendorProfile.id == vp_uuid)
        if org_id:
            try:
                query = query.where(VendorProfile.org_id == uuid.UUID(org_id))
            except ValueError:
                pass
        vendor_orm = await session.scalar(query)

        if not vendor_orm:
            raise ValueError(f"VendorProfile not found: {vendor_profile_id}")

        # Also fetch tender vector from PostgreSQL bridge table
        pg_tender = await session.scalar(
            select(Tender).where(Tender.mongo_id == tender_mongo_id)
        )
        
        from app.services.weight_resolver import WeightResolver
        custom_weights = await WeightResolver.get_weights(session, str(vendor_orm.id), str(vendor_orm.org_id))

    vendor_profile_data = vendor_orm.profile_data or {}
    vendor_embedding = vendor_orm.embedding

    logger.info("[Orchestrator] Step 1 ✓ Fetched vendor: %s", vendor_orm.vendor_id)

    # ── Step 2: Fetch tender structured_data from MongoDB ────────────────────
    tender_doc = await mongo_db.documents.find_one({
        "_id": {"$in": [tender_mongo_id]},  # try string first
    })
    if not tender_doc:
        # Try by mongo_id field
        tender_doc = await mongo_db.documents.find_one({"mongo_id": tender_mongo_id})

    if not tender_doc:
        try:
            from bson import ObjectId
            tender_doc = await mongo_db.documents.find_one({"_id": ObjectId(tender_mongo_id)})
        except Exception:
            pass

    if not tender_doc:
        raise ValueError(f"Tender document not found in MongoDB: {tender_mongo_id}")

    tender_sd = tender_doc.get("structured_data") or {}
    extraction_confidence = tender_doc.get("extraction_confidence", 0.5)

    logger.info("[Orchestrator] Step 2 ✓ Fetched tender. domain=%s", tender_sd.get("domain"))

    # ── Step 3: Compute semantic score ───────────────────────────────────────
    semantic_score = 0.0

    if vendor_embedding is not None and pg_tender is not None and pg_tender.embedding is not None:
        v_vec = np.array(vendor_embedding)
        t_vec = np.array(pg_tender.embedding)

        v_norm = np.linalg.norm(v_vec)
        t_norm = np.linalg.norm(t_vec)

        if v_norm > 0 and t_norm > 0:
            semantic_score = float(np.dot(v_vec, t_vec) / (v_norm * t_norm))
            semantic_score = max(0.0, min(1.0, semantic_score))  # clamp

    logger.info("[Orchestrator] Step 3 ✓ Semantic score: %.3f", semantic_score)

    # ── Step 4: Hard Filter ───────────────────────────────────────────────────
    filter_result = HardFilterEngine.evaluate(vendor_profile_data, tender_sd)

    logger.info(
        "[Orchestrator] Step 4 ✓ Hard filter: %s | reason=%s",
        "PASS" if filter_result["overall_pass"] else "FAIL",
        filter_result.get("disqualification_reason"),
    )

    # ── Step 5: Weighted Score ────────────────────────────────────────────────
    if filter_result["overall_pass"]:
        score_result = WeightedScoringEngine.calculate_score(
            vendor_profile_data, tender_sd, semantic_score, custom_weights
        )
    else:
        # Short-circuit: disqualified vendors get a 0 score with empty breakdown
        score_result = {
            "final_score": 0.0,
            "breakdown": {}
        }

    logger.info("[Orchestrator] Step 5 ✓ Final score: %.1f/100", score_result["final_score"])

    # ── Step 6: LLM Explanation ───────────────────────────────────────────────
    explanation = await generate_explanation(
        vendor=vendor_profile_data,
        tender=tender_sd,
        filter_result=filter_result,
        score_result=score_result,
        extraction_confidence=extraction_confidence,
    )

    logger.info(
        "[Orchestrator] Step 6 ✓ Explanation generated. recommendation=%s",
        explanation.recommendation,
    )

    # ── Step 7: Build complete result document ────────────────────────────────
    match_id = f"MR-{vendor_orm.vendor_id}-{tender_mongo_id[:8]}"
    matched_at = datetime.now(timezone.utc).isoformat()

    final_result = {
        "schema_url": "http://json-schema.org/draft-07/schema#",
        "version": "3.0.0",
        "match_result": {
            "_meta": {
                "match_id": match_id,
                "vendor_profile_id": str(vendor_orm.id),
                "vendor_id": vendor_orm.vendor_id,
                "tender_mongo_id": tender_mongo_id,
                "matched_at": matched_at,
                "engine_version": "orchestrator-v3.0",
                "semantic_score": round(semantic_score, 4),
                "extraction_confidence": extraction_confidence,
            },
            "hard_filter_results": {
                "overall_pass": filter_result["overall_pass"],
                "disqualification_reason": filter_result.get("disqualification_reason"),
                "failed_check": filter_result.get("failed_check"),
                "check_results": filter_result.get("check_results", []),
            },
            "weighted_score": {
                "final_score": score_result["final_score"],
                "eligibility_status": "Eligible" if filter_result["overall_pass"] else "Ineligible",
                "breakdown": score_result.get("breakdown", {}),
            },
            "explanation": {
                "executive_summary": explanation.executive_summary,
                "strengths": explanation.strengths,
                "risk_factors": explanation.risk_factors,
                "score_rationale": explanation.score_rationale.model_dump(),
                "confidence_note": explanation.confidence_note,
            },
            "recommendation": explanation.recommendation,
            "recommendation_detail": explanation.recommendation_detail,
        },
    }

    # ── Step 8: Persist to MongoDB match_results ──────────────────────────────
    await mongo_db.match_results.replace_one(
        {"match_result._meta.match_id": match_id},
        final_result,
        upsert=True,
    )

    # Strip MongoDB _id from return payload
    final_result.pop("_id", None)
    logger.info("[Orchestrator] Step 8 ✓ Persisted to match_results. match_id=%s", match_id)

    return final_result
