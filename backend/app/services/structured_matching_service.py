"""
structured_matching_service.py
------------------------------
Evaluates how well a given vendor matches a given tender using strict 
eligibility filtering and semantic field-wise scoring.

Polyglot Persistence:
- Vendor Profile is fetched from PostgreSQL (JSONB).
- Tender data is passed in (from MongoDB).
- Match results are saved to MongoDB.
"""

from datetime import datetime, timezone
import uuid
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.postgres import get_pg_session
from app.services.embedding_service import get_embedding_service
from app.db.models.document import VendorProfile
from app.db.models.user import User

async def evaluate_match(vendor_id: str, tender: dict, current_user: User = None) -> dict:
    """
    vendor_id: UUID string or vendor_id shortcut (V-...)
    tender: dict from MongoDB
    """
    mongo_db = get_db()
    
    # ── Fetch Vendor Context from PostgreSQL ───────────────────────────────
    async with get_pg_session() as session:
        # 1. Try matching by UUID if it looks like one
        vendor_uuid = None
        try:
            vendor_uuid = uuid.UUID(vendor_id)
        except ValueError:
            pass

        query = select(VendorProfile)
        if vendor_uuid:
            query = query.where(VendorProfile.id == vendor_uuid)
        else:
            query = query.where(VendorProfile.vendor_id == vendor_id)

        # Tenant isolation
        if current_user:
            query = query.where(VendorProfile.org_id == current_user.org_id)

        vendor = await session.scalar(query)
        if not vendor:
            raise ValueError(f"Vendor not found or access denied for ID: {vendor_id}")

    profile_data = vendor.profile_data

    # Default values for matching
    match_id = f"MR-{vendor.vendor_id}-{tender.get('tender_id', 'T-000')}"
    matched_at = datetime.now(timezone.utc).isoformat()
    
    # Setup results output
    result = {
        "_meta": {
            "match_id": match_id,
            "vendor_id": vendor.vendor_id,
            "tender_id": tender.get("tender_id"),
            "matched_at": matched_at,
            "engine_version": "2.1.0",
            "notification_sent": False,
            "notification_channel": None,
            "vendor_feedback": None
        },
        "hard_filter_results": {
            "overall_pass": True,
            "disqualification_reason": None,
            "filters": []
        },
        "weighted_score": {
            "final_score": 0.0,
            "eligibility_status": "Eligible",
            "breakdown": {},
            "optional_boosts": {
                "capability_description_boost": 0.0,
                "msme_emd_exemption_boost": 0.0,
                "completion_cert_boost": 0.0,
                "years_in_business_boost": 0.0,
                "total_boost": 0.0
            }
        },
        "human_readable_explanation": "",
        "recommendation": "",
        "recommendation_detail": ""
    }

    # Extract vendor fields safely from JSONB
    identity = profile_data.get('identity', {})
    geography = profile_data.get('geography', {})
    business = profile_data.get('business_domain', {})
    financials = profile_data.get('financials', {})
    projects = profile_data.get('past_project_experience', {}).get('projects', [])
    certs = profile_data.get('certifications', {})
    compliance = profile_data.get('compliance', {})

    # ─── HARD FILTERS ────────────────────────────────────────────────────────
    
    # HF-01: Blacklist Check
    vendor_debarred = compliance.get('blacklisted_or_debarred', False)
    if vendor_debarred:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-01",
            "filter_name": "Blacklist Check",
            "result": "FAIL",
            "detail": "Vendor is blacklisted or debarred."
        })
    else:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-01",
            "filter_name": "Blacklist Check",
            "result": "PASS",
            "detail": "Vendor is not blacklisted."
        })

    # HF-02: Domain Match
    tender_domain = tender.get("domain")
    vendor_primary_domains = business.get("primary_domains", [])
    if tender_domain is not None and tender_domain not in vendor_primary_domains:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-02",
            "filter_name": "Primary Domain Match",
            "result": "FAIL",
            "detail": f"Tender domain '{tender_domain}' not found in vendor's primary domains."
        })
    else:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-02",
            "filter_name": "Primary Domain Match",
            "result": "PASS",
            "detail": "Domain matched or tender domain not restricted."
        })
        
    # HF-03: Geography
    tender_state = tender.get("location_state", "")
    vendor_states = geography.get("operational_states", []) + geography.get("registered_states", [])
    willing = geography.get("willing_to_operate_in_new_states", False)
    if tender_state and tender_state not in vendor_states and not willing:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-03",
            "filter_name": "Geographic Eligibility",
            "result": "FAIL",
            "detail": f"Vendor does not operate in {tender_state} and is not willing to expand."
        })
    else:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-03",
            "filter_name": "Geographic Eligibility",
            "result": "PASS",
            "detail": "Vendor operates in tender state or is willing to operate."
        })
        
    # HF-04: Certifications
    required_certs = set(tender.get("mandatory_certifications", []))
    vendor_iso = [x.get("standard") for x in certs.get("iso_certifications", [])]
    vendor_licenses = [x.get("license_type") for x in certs.get("domain_licenses", [])]
    vendor_all_certs = set(vendor_iso + vendor_licenses)
    
    missing_certs = required_certs - vendor_all_certs
    if missing_certs:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-04",
            "filter_name": "Mandatory Certifications",
            "result": "FAIL",
            "detail": f"Missing mandatory certifications: {', '.join(missing_certs)}"
        })
    else:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-04",
            "filter_name": "Mandatory Certifications",
            "result": "PASS",
            "detail": "All mandatory certifications are met."
        })

    # HF-05: Financials
    min_turnover = tender.get("min_avg_turnover", 0)
    vendor_turnover = financials.get("avg_annual_turnover_inr", 0)
    if vendor_turnover < min_turnover:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-05",
            "filter_name": "Annual Turnover Threshold",
            "result": "FAIL",
            "detail": f"Vendor turnover ({vendor_turnover}) < Threshold ({min_turnover})."
        })
    else:
        result["hard_filter_results"]["filters"].append({
            "filter_id": "HF-05",
            "filter_name": "Annual Turnover Threshold",
            "result": "PASS",
            "detail": f"Vendor turnover meets threshold."
        })

    # Check overall pass
    failed_filters = [f for f in result["hard_filter_results"]["filters"] if f["result"] == "FAIL"]
    if failed_filters:
        result["hard_filter_results"]["overall_pass"] = False
        result["hard_filter_results"]["disqualification_reason"] = failed_filters[0]["detail"]
        result["weighted_score"]["eligibility_status"] = "Ineligible"
        result["weighted_score"]["final_score"] = 0.0
        result["recommendation"] = "NOT_ELIGIBLE"
        result["recommendation_detail"] = f"Failed {len(failed_filters)} hard filters."
        
        final_output = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "version": "1.0.0",
            "match_result": result
        }
        await mongo_db.match_results.insert_one(final_output)
        final_output.pop("_id", None)
        return final_output
        
    # ─── FIELD-WISE MATCHING (SCORING) ───────────────────────────────────────
    
    # 1. Domain Match (0.20)
    domain_score = 1.0 if tender_domain in business.get("primary_domains", []) else 0.7
    
    # 2. Geography Match (0.15)
    geo_score = 0.0
    if tender_state in geography.get("registered_states", []): geo_score = 1.0
    elif tender_state in geography.get("preferred_states", []): geo_score = 0.9
    elif tender_state in geography.get("operational_states", []): geo_score = 0.8
    elif willing: geo_score = 0.5

    # 3. Financial Capacity (0.15)
    tender_value = tender.get("estimated_value", min_turnover)
    fin_score = 0.5
    if tender_value > 0:
        ratio = vendor_turnover / tender_value
        if ratio >= 3: fin_score = 1.0
        elif ratio >= 2: fin_score = 0.9
        elif ratio >= 1: fin_score = 0.7
        else: fin_score = 0.4
    else:
        fin_score = 0.8

    # 4. Experience Match (0.20)
    exp_score = 0.0
    largest_project = max([p.get("contract_value_inr", 0) for p in projects], default=0)
    if tender_value > 0 and largest_project >= tender_value:
        exp_score = 1.0
    elif len(projects) > 2:
        exp_score = 0.8
    elif len(projects) > 0:
        exp_score = 0.6
    else:
        exp_score = 0.3

    # 5. Certification Match (0.10)
    cert_score = 1.0 if not required_certs else (len(required_certs.intersection(vendor_all_certs)) / len(required_certs))

    # 6. Semantic Match (0.15)
    sem_score = 0.0
    embedding_svc = get_embedding_service()
    tender_scope = tender.get("scope", tender.get("similar_work_definition", ""))
    vendor_capabilities = business.get("capability_description_freetext", "")
    if tender_scope and vendor_capabilities:
        tender_vec = await embedding_svc.encode_text(tender_scope)
        vendor_vec = await embedding_svc.encode_text(vendor_capabilities)
        cos_sim = float(np.dot(tender_vec, vendor_vec))
        sem_score = max(0.0, min(1.0, cos_sim))

    # 7. Compliance & Risk (0.05)
    comp_score = 1.0
    if compliance.get("active_litigation"): comp_score -= 0.5
    if not compliance.get("gst_returns_compliant"): comp_score -= 0.3
    if not compliance.get("epf_esic_compliant"): comp_score -= 0.2
    comp_score = max(0.0, comp_score)

    weights = {
        "domain": 0.20, "geography": 0.15, "financial": 0.15, "experience": 0.20,
        "certification": 0.10, "semantic": 0.15, "compliance": 0.05
    }

    raw_scores = {
        "domain": domain_score, "geography": geo_score, "financial": fin_score,
        "experience": exp_score, "certification": cert_score, "semantic": sem_score,
        "compliance": comp_score
    }

    base_score = sum(weights[k] * raw_scores[k] for k in weights)

    completeness_ratio = vendor.profile_completeness_pct / 100.0
    COMPLETENESS_BOOST_MAX = 0.05
    completeness_boost = completeness_ratio * COMPLETENESS_BOOST_MAX

    final_score = min(1.0, base_score + completeness_boost)
    
    result["weighted_score"]["breakdown"] = {
        k: {
            "weight": weights[k],
            "raw_score": round(raw_scores[k], 3),
            "weighted_score": round(weights[k] * raw_scores[k], 3)
        } for k in weights
    }
    result["weighted_score"]["final_score"] = round(final_score, 3)
    
    exp_text = f"Strong match score of {round(final_score*100)}%. "
    if domain_score == 1.0: exp_text += "Domain aligns perfectly. "
    if geo_score >= 0.8: exp_text += "Geography is a strong fit. "
    if fin_score >= 0.9: exp_text += "Financial capacity exceeds requirements. "
    
    result["human_readable_explanation"] = exp_text.strip()
    result["recommendation"] = "HIGH_MATCH" if final_score > 0.75 else "MODERATE_MATCH"
    result["recommendation_detail"] = f"Score {round(final_score*100)} — meets all hard filters."

    final_output = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": "1.0.0",
        "match_result": result
    }
    await mongo_db.match_results.insert_one(final_output)
    final_output.pop("_id", None)
    
    return final_output
