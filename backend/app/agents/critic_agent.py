"""
critic_agent.py
---------------
Node in the TenderMatch LangGraph pipeline (conditionally invoked).

Responsibilities:
  - Extract necessary data from state (explanation, score, filter, completeness).
  - Pass it to CriticService for deterministic evaluation.
  - If overridden, update the final recommendation.
  - Append findings/warnings to the explanation dict.
  - Update TenderMatchState with critic_report, critic_overridden, critic_severity.
"""

import logging
from typing import Dict, Any

from app.agents.state import TenderMatchState
from app.services.critic_service import critic_service
from app.db.models.critic_models import score_to_recommendation

logger = logging.getLogger(__name__)


async def critic_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: Validates the LLM explanation for consistency.
    """
    logger.info("[Agent:Critic] START")

    # Safely extract from state
    explanation_dict = state.get("explanation_result", {})
    score_result = state.get("score_result") or {"final_score": 0.0, "breakdown": {}}
    filter_result = state.get("filter_result") or {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
    vendor_data = state.get("vendor_profile_data", {})
    vendor_completeness = vendor_data.get("profile_completeness_pct", 50.0)
    
    # Check if explanation exists
    if not explanation_dict:
        logger.warning("[Agent:Critic] No explanation_result found in state. Skipping validation.")
        return {"current_stage": "critic_complete"}

    # Evaluate using CriticService
    report = critic_service.evaluate(
        explanation_dict=explanation_dict,
        score_result=score_result,
        filter_result=filter_result,
        vendor_completeness=vendor_completeness
    )

    # Convert to dict for state storage and MongoDB persistence
    report_dict = report.to_mongo_dict()
    
    # State updates
    updates: Dict[str, Any] = {
        "current_stage": "critic_complete",
        "critic_report": report_dict,
        "critic_overridden": report.overridden,
        "critic_severity": report.worst_severity,
    }

    # Modify explanation_dict in place if necessary
    if report.overridden:
        # Override recommendation based on deterministic mapping
        final_score = score_result.get("final_score", 0.0)
        overall_pass = filter_result.get("overall_pass", False)
        safe_rec = score_to_recommendation(final_score, overall_pass)
        
        logger.warning("[Agent:Critic] ERROR severity found. Overriding recommendation: %s -> %s", 
                       explanation_dict.get("recommendation"), safe_rec)
        
        explanation_dict["recommendation"] = safe_rec
        explanation_dict["_critic_override"] = True
        explanation_dict["_critic_findings"] = [f.model_dump() for f in report.errors()]
        
        # We must also update the final recommendation in state and the final_match_result
        updates["recommendation"] = safe_rec
        updates["explanation_result"] = explanation_dict
        
        # Modify the final_match_result if it's already built
        final_match_result = state.get("final_match_result")
        if final_match_result and "match_result" in final_match_result:
            final_match_result["match_result"]["recommendation"] = safe_rec
            final_match_result["match_result"]["explanation"] = explanation_dict
            final_match_result["match_result"]["critic_report"] = report_dict
            updates["final_match_result"] = final_match_result
            
    elif report.has_warnings():
        logger.info("[Agent:Critic] WARNING severity found. Appending warnings.")
        explanation_dict["_critic_warnings"] = [f.model_dump() for f in report.warnings()]
        updates["explanation_result"] = explanation_dict
        
        final_match_result = state.get("final_match_result")
        if final_match_result and "match_result" in final_match_result:
            final_match_result["match_result"]["explanation"] = explanation_dict
            final_match_result["match_result"]["critic_report"] = report_dict
            updates["final_match_result"] = final_match_result
    else:
        logger.info("[Agent:Critic] Validation clean.")
        final_match_result = state.get("final_match_result")
        if final_match_result and "match_result" in final_match_result:
            final_match_result["match_result"]["critic_report"] = report_dict
            updates["final_match_result"] = final_match_result

    return updates
