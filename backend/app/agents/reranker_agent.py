"""
reranker_agent.py
-----------------
Optional node in the TenderMatch LangGraph pipeline.

Responsibilities:
  - If Planner determined reranking is needed, and vector/BM25 scores diverge,
    run cross-encoder over the tender chunks.
  - Updates semantic_score and final_score if reranking happens.
"""

import logging

from app.agents.state import TenderMatchState
from app.services.hybrid_retriever import HybridRetriever
from app.services.matching_service import WeightedScoringEngine

logger = logging.getLogger(__name__)


async def reranker_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: cross-encoder reranking.
    """
    logger.info("[Agent:Reranker] START")

    plan = state.get("execution_plan", {})
    if not plan.get("rerank_results"):
        logger.info("[Agent:Reranker] Reranking not requested by plan. Skipping.")
        return {"current_stage": "reranker_skipped"}

    retrieval_scores = state.get("retrieval_scores", {})
    vector_score = retrieval_scores.get("vector_score", 0.0)
    bm25_score = retrieval_scores.get("bm25_score", 0.0)

    # Trigger reranking if scores diverge significantly
    if abs(vector_score - bm25_score) <= 0.3:
        logger.info("[Agent:Reranker] Scores agree (diff <= 0.3). Skipping reranking.")
        return {"current_stage": "reranker_skipped"}

    logger.info("[Agent:Reranker] Scores diverge (vector=%.2f, bm25=%.2f). Reranking chunks...", 
                vector_score, bm25_score)

    vendor_data = state.get("vendor_profile_data", {})
    tender_sd = state.get("tender_structured_data", {})

    identity = vendor_data.get("identity", {})
    business_domain = vendor_data.get("business_domain", {})
    vendor_text = f"{identity.get('company_legal_name', '')} {business_domain.get('capability_description_freetext', '')}"
    
    tender_title = tender_sd.get("title", "")
    tender_scope = tender_sd.get("scope_summary", "")

    # Retrieve top 10 BM25 chunks
    retriever = HybridRetriever()
    top_chunks = retriever.retrieve_top_chunks(vendor_text, tender_title, tender_scope, top_k=10)
    
    if not top_chunks:
        logger.warning("[Agent:Reranker] No chunks retrieved. Skipping.")
        return {"current_stage": "reranker_skipped"}

    # Apply cross-encoder
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
        
        pairs = [[vendor_text, chunk] for chunk, _ in top_chunks]
        scores = model.predict(pairs)
        
        # Max score among top chunks
        max_rerank_score = float(max(scores)) if len(scores) > 0 else 0.0
        
        # Normalize score (CrossEncoder scores are logits, usually not strictly 0-1)
        # Using a sigmoid for normalization
        import math
        normalized_score = 1 / (1 + math.exp(-max_rerank_score))
        
        new_semantic_score = normalized_score
        logger.info("[Agent:Reranker] Reranked semantic_score: %.4f", new_semantic_score)
        
        # Recalculate final score
        custom_weights = state.get("custom_weights")
        score_result = WeightedScoringEngine.calculate_score(
            vendor_data, tender_sd, new_semantic_score, custom_weights
        )
        
        final_score = score_result.get("final_score", 0.0)
        
        if final_score >= 80:
            recommendation = "HIGH_MATCH"
        elif final_score >= 60:
            recommendation = "MODERATE_MATCH"
        elif final_score >= 40:
            recommendation = "LOW_MATCH"
        else:
            recommendation = "NOT_ELIGIBLE"
            
        return {
            "current_stage": "reranker_complete",
            "semantic_score": new_semantic_score,
            "score_result": score_result,
            "final_score": final_score,
            "recommendation": recommendation,
        }
        
    except ImportError:
        logger.error("[Agent:Reranker] sentence-transformers not installed. Skipping.")
        return {"current_stage": "reranker_skipped"}
    except Exception as e:
        logger.error("[Agent:Reranker] Error during reranking: %s", e)
        return {"current_stage": "reranker_skipped"}
