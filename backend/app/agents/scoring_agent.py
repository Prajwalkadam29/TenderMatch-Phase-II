"""
scoring_agent.py
----------------
Node 4 of the TenderMatch LangGraph pipeline.
Only reached if filter_agent set is_eligible=True.

Responsibilities:
  - Compute semantic score via HybridRetriever (Vector + BM25)
  - Run WeightedScoringEngine.calculate_score() with 7-dimension weighted scoring
  - Populate: semantic_score, score_result, final_score, retrieval_scores
"""

import logging

from app.agents.state import TenderMatchState
from app.services.matching_service import WeightedScoringEngine
from app.services.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


async def scoring_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: semantic similarity + 7-dimension weighted scoring.
    """
    logger.info("[Agent:Scoring] START")

    vendor_data = state.get("vendor_profile_data") or {}
    tender_sd = state.get("tender_structured_data") or {}
    filter_result = state.get("filter_result") or {}
    vendor_emb = state.get("vendor_embedding")
    tender_emb = state.get("tender_pg_embedding")
    
    plan = state.get("execution_plan") or {}
    retrieval_strategy = plan.get("retrieval_strategy", "hybrid")

    # ── Semantic score (Hybrid Retrieval) ─────────────────────────────────────
    
    identity = vendor_data.get("identity", {})
    business_domain = vendor_data.get("business_domain", {})
    vendor_text = f"{identity.get('company_legal_name', '')} {business_domain.get('capability_description_freetext', '')}"
    
    tender_title = tender_sd.get("title", "")
    tender_scope = tender_sd.get("scope_summary", "")

    retriever = HybridRetriever()
    retrieval_scores = retriever.calculate_hybrid_score(
        vendor_text=vendor_text,
        tender_title=tender_title,
        tender_scope=tender_scope,
        vendor_vector=vendor_emb,
        tender_vector=tender_emb,
        retrieval_strategy=retrieval_strategy
    )
    
    retrieval_scores = {
        k: float(v)
        for k, v in retrieval_scores.items()
    }
    
    semantic_score = retrieval_scores["hybrid_score"]
    logger.info("[Agent:Scoring] Hybrid score: %.4f (Vector: %.4f, BM25: %.4f, Alpha: %.1f)", 
                semantic_score, retrieval_scores["vector_score"], 
                retrieval_scores["bm25_score"], retrieval_scores["alpha_used"])

    # ── Weighted score ────────────────────────────────────────────────────────
    custom_weights = state.get("custom_weights")
    try:
        score_result = WeightedScoringEngine.calculate_score(
            vendor_data, tender_sd, semantic_score, custom_weights
        )
    except Exception as exc:
        logger.error("[Agent:Scoring] WeightedScoringEngine failed: %s", exc)
        score_result = {"final_score": 0.0, "breakdown": {}}

    final_score = score_result.get("final_score", 0.0)

    # Map score to recommendation label
    if final_score >= 80:
        recommendation = "HIGH_MATCH"
    elif final_score >= 60:
        recommendation = "MODERATE_MATCH"
    elif final_score >= 40:
        recommendation = "LOW_MATCH"
    else:
        recommendation = "NOT_ELIGIBLE"

    logger.info("[Agent:Scoring] ✓ Final score: %.1f → %s", final_score, recommendation)

    return {
        "current_stage": "scoring_complete",
        "semantic_score": semantic_score,
        "retrieval_scores": retrieval_scores,
        "score_result": score_result,
        "final_score": final_score,
        "recommendation": recommendation,
    }
