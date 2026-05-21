"""
explanation_agent.py
--------------------
Node 5 of the TenderMatch LangGraph pipeline.
Reached by BOTH eligible and ineligible vendors.

Responsibilities:
  - Call generate_explanation() with full context (vendor, tender, filter, score)
  - Serialize ExplanationResult to a plain dict for state storage
  - Assemble the complete final_match_result document (v3.0.0 schema)
  - Populate: explanation_result, final_match_result, match_id
"""

import logging
from datetime import datetime, timezone

from app.agents.state import TenderMatchState
from app.services.explanation_service import generate_explanation

logger = logging.getLogger(__name__)


async def explanation_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: LLM explanation generation + final result assembly.
    Never raises — falls back to programmatic explanation if Groq fails.
    """
    logger.info("[Agent:Explanation] START")

    vendor_data = state.get("vendor_profile_data") or {}
    tender_sd = state.get("tender_structured_data") or {}
    filter_result = state.get("filter_result") or {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
    score_result = state.get("score_result") or {"final_score": 0.0, "breakdown": {}}
    extraction_confidence = state.get("extraction_confidence", 0.5)

    # ── Generate LLM explanation ───────────────────────────────────────────────
    try:
        explanation = await generate_explanation(
            vendor=vendor_data,
            tender=tender_sd,
            filter_result=filter_result,
            score_result=score_result,
            extraction_confidence=extraction_confidence,
        )
    except Exception as exc:
        logger.error("[Agent:Explanation] generate_explanation raised: %s", exc)
        from app.services.explanation_service import _build_fallback_explanation
        explanation = _build_fallback_explanation(vendor_data, tender_sd, filter_result, score_result)

    # ── Serialize ExplanationResult to dict ────────────────────────────────────
    explanation_dict = {
        "executive_summary": explanation.executive_summary,
        "strengths": explanation.strengths,
        "risk_factors": explanation.risk_factors,
        "score_rationale": explanation.score_rationale.model_dump(),
        "recommendation": explanation.recommendation,
        "recommendation_detail": explanation.recommendation_detail,
        "confidence_note": explanation.confidence_note,
    }

    # ── Build complete v3.0.0 match result document ────────────────────────────
    vendor_id = state.get("vendor_vendor_id", "UNKNOWN")
    vendor_pg_uuid = state.get("vendor_pg_uuid", "")
    tender_mongo_id = state.get("tender_mongo_id", "")
    final_score = state.get("final_score", score_result.get("final_score", 0.0))
    semantic_score = state.get("semantic_score", 0.0)
    is_eligible = state.get("is_eligible", True)

    match_id = f"MR-{vendor_id}-{tender_mongo_id[:8]}"
    matched_at = datetime.now(timezone.utc).isoformat()
    plan = state.get("execution_plan") or {}
    
    final_match_result = {
        "schema_url": "http://json-schema.org/draft-07/schema#",
        "version": "3.0.0",
        "planner_decision": plan,
        "match_result": {
            "_meta": {
                "match_id": match_id,
                "vendor_profile_id": vendor_pg_uuid,
                "vendor_id": vendor_id,
                "tender_mongo_id": tender_mongo_id,
                "matched_at": matched_at,
                "engine_version": "langgraph-v3.0",
                "semantic_score": round(semantic_score, 4),
                "extraction_confidence": extraction_confidence,
                "pipeline": "langgraph",
                "retrieval_strategy": plan.get("retrieval_strategy", "hybrid"),
            },
            "hard_filter_results": {
                "overall_pass": filter_result.get("overall_pass", False),
                "disqualification_reason": filter_result.get("disqualification_reason"),
                "failed_check": filter_result.get("failed_check"),
                "check_results": filter_result.get("check_results", []),
            },
            "weighted_score": {
                "final_score": final_score,
                "eligibility_status": "Eligible" if is_eligible else "Ineligible",
                "breakdown": score_result.get("breakdown", {}),
            },
            "retrieval_scores": state.get("retrieval_scores", {}),
            "explanation": explanation_dict,
            "recommendation": explanation.recommendation,
            "recommendation_detail": explanation.recommendation_detail,
        },
    }

    logger.info(
        "[Agent:Explanation] ✓ Assembled result. match_id=%s score=%.1f recommendation=%s",
        match_id, final_score, explanation.recommendation,
    )

    return {
        "current_stage": "explanation_complete",
        "explanation_result": explanation_dict,
        "final_match_result": final_match_result,
        "match_id": match_id,
        "recommendation": explanation.recommendation,
    }
