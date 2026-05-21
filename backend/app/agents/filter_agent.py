"""
filter_agent.py
---------------
Node 3 of the TenderMatch LangGraph pipeline.

Responsibilities:
  - Run HardFilterEngine.evaluate(vendor_profile_data, tender_structured_data)
  - Populate: filter_result, is_eligible
  - If ineligible: sets final_score=0, recommendation=NOT_ELIGIBLE
    The graph routes ineligible vendors directly to explanation_agent,
    skipping the scoring node.
"""

import logging

from app.agents.state import TenderMatchState
from app.services.matching_service import HardFilterEngine

logger = logging.getLogger(__name__)


async def filter_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: deterministic hard filter evaluation.
    Pure Python — no LLM, no external calls.
    """
    logger.info("[Agent:Filter] START")

    vendor_data = state.get("vendor_profile_data") or {}
    tender_sd = state.get("tender_structured_data") or {}

    try:
        filter_result = HardFilterEngine.evaluate(vendor_data, tender_sd)
    except Exception as exc:
        logger.error("[Agent:Filter] HardFilterEngine raised: %s", exc)
        # Fail open — allow matching to continue so no vendor is incorrectly blocked
        filter_result = {
            "overall_pass": True,
            "disqualification_reason": None,
            "failed_check": None,
            "check_results": [],
        }

    is_eligible = filter_result.get("overall_pass", False)

    if is_eligible:
        logger.info("[Agent:Filter] ✓ PASS — vendor is eligible.")
    else:
        logger.info(
            "[Agent:Filter] ✗ FAIL — %s",
            filter_result.get("disqualification_reason", "unknown reason"),
        )

    update = {
        "current_stage": "filter_complete",
        "filter_result": filter_result,
        "is_eligible": is_eligible,
    }

    # Pre-set score to 0 for ineligible vendors (scoring node will be skipped)
    if not is_eligible:
        update["final_score"] = 0.0
        update["score_result"] = {"final_score": 0.0, "breakdown": {}}
        update["recommendation"] = "NOT_ELIGIBLE"
        update["semantic_score"] = 0.0

    return update
