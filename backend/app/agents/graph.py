"""
graph.py
--------
TenderMatch LangGraph Pipeline — StateGraph definition and wiring.

Graph topology:
    START
      │
      ▼
  [ingestion_agent]   ← Load vendor (PG) + tender (Mongo) + embeddings
      │
      ├── error → END (early exit with error state)
      │
      ▼
  [parsing_agent]     ← Validate/enrich tender structured_data
      │
      ▼
  [filter_agent]      ← Deterministic hard filter (HF-01 to HF-05)
      │
      ├── ineligible → [explanation_agent]  ← Explain disqualification
      │
      ▼ eligible
  [scoring_agent]     ← Cosine similarity + 7-dim weighted scoring
      │
      ▼
  [explanation_agent] ← LLM explanation + v3.0.0 result assembly
      │
      ▼
  [notification_agent] ← Persist to MongoDB + optional email dispatch
      │
      ▼
    END

Features:
  - MemorySaver checkpointing for LangGraph state persistence
  - Conditional routing: ineligible vendors skip scoring_agent
  - Error routing: bad IDs / DB errors short-circuit to END
  - Thread-safe: each invocation gets a unique thread_id (via UUID)
"""

import logging
import uuid
from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import TenderMatchState
from app.agents.planner_agent import planner_agent
from app.agents.ingestion_agent import ingestion_agent
from app.agents.parsing_agent import parsing_agent
from app.agents.filter_agent import filter_agent
from app.agents.scoring_agent import scoring_agent
from app.agents.reranker_agent import reranker_agent
from app.agents.explanation_agent import explanation_agent
from app.agents.critic_agent import critic_agent
from app.agents.notification_agent import notification_agent

logger = logging.getLogger(__name__)


# ─── Conditional routing functions ────────────────────────────────────────────

def route_after_ingestion(state: TenderMatchState) -> str:
    """Route to parsing if OK, else END if a fatal error occurred."""
    if state.get("error"):
        logger.warning("[Graph] Routing to END after ingestion error: %s", state["error"])
        return "end_with_error"
    return "parsing_agent"


def route_after_filter(state: TenderMatchState) -> str:
    """Route eligible vendors to scoring; ineligible vendors to explanation directly."""
    if state.get("is_eligible", True):
        return "scoring_agent"
    return "explanation_agent"


def route_after_scoring(state: TenderMatchState) -> str:
    """Route to reranker if plan requires it, else directly to explanation."""
    plan = state.get("execution_plan") or {}
    if plan.get("rerank_results"):
        return "reranker_agent"
    return "explanation_agent"


def route_after_explanation(state: TenderMatchState) -> str:
    """Route to critic if invoked by plan, or if score is in ambiguous zone (55-85)."""
    plan = state.get("execution_plan") or {}
    final_score = state.get("final_score", 0.0)
    
    if plan.get("invoke_critic", False) or (55.0 <= final_score <= 85.0):
        return "critic_agent"
    return "notification_agent"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct and compile the TenderMatch LangGraph StateGraph.
    Returns a compiled graph ready for invocation.
    """
    checkpointer = MemorySaver()
    builder = StateGraph(TenderMatchState)

    # ── Register nodes ─────────────────────────────────────────────────────────
    builder.add_node("planner_agent", planner_agent)
    builder.add_node("ingestion_agent", ingestion_agent)
    builder.add_node("parsing_agent", parsing_agent)
    builder.add_node("filter_agent", filter_agent)
    builder.add_node("scoring_agent", scoring_agent)
    builder.add_node("reranker_agent", reranker_agent)
    builder.add_node("explanation_agent", explanation_agent)
    builder.add_node("critic_agent", critic_agent)
    builder.add_node("notification_agent", notification_agent)

    # ── Register edges ─────────────────────────────────────────────────────────

    # START → planner
    builder.add_edge(START, "planner_agent")
    
    # planner → ingestion
    builder.add_edge("planner_agent", "ingestion_agent")

    # ingestion → parsing OR end_with_error
    builder.add_conditional_edges(
        "ingestion_agent",
        route_after_ingestion,
        {
            "parsing_agent": "parsing_agent",
            "end_with_error": END,
        },
    )

    # parsing → filter (always)
    builder.add_edge("parsing_agent", "filter_agent")

    # filter → scoring (eligible) OR explanation (ineligible)
    builder.add_conditional_edges(
        "filter_agent",
        route_after_filter,
        {
            "scoring_agent": "scoring_agent",
            "explanation_agent": "explanation_agent",
        },
    )

    # scoring → reranker OR explanation
    builder.add_conditional_edges(
        "scoring_agent",
        route_after_scoring,
        {
            "reranker_agent": "reranker_agent",
            "explanation_agent": "explanation_agent",
        }
    )
    
    # reranker → explanation (always)
    builder.add_edge("reranker_agent", "explanation_agent")

    # explanation → critic OR notification
    builder.add_conditional_edges(
        "explanation_agent",
        route_after_explanation,
        {
            "critic_agent": "critic_agent",
            "notification_agent": "notification_agent",
        }
    )
    
    # critic → notification (always)
    builder.add_edge("critic_agent", "notification_agent")

    # notification → END
    builder.add_edge("notification_agent", END)

    return builder.compile(checkpointer=checkpointer)


# ─── Singleton graph instance ─────────────────────────────────────────────────
# Built once at module load time for reuse across requests.
_graph = None


def get_graph():
    """Lazy singleton: build the graph once, reuse forever."""
    global _graph
    if _graph is None:
        _graph = build_graph()
        logger.info("[Graph] TenderMatch LangGraph compiled successfully.")
    return _graph


# ─── Public invocation API ────────────────────────────────────────────────────

async def run_match_pipeline(
    vendor_profile_id: str,
    tender_mongo_id: str,
    org_id: Optional[str] = None,
    score_threshold: float = 70.0,
) -> dict:
    """
    Invoke the full TenderMatch LangGraph pipeline for a vendor-tender pair.

    This is the primary entry point for the LangGraph agent. It:
      1. Initializes state with the required inputs
      2. Runs the full graph (ingestion → parsing → filter → scoring → explanation → notification)
      3. Returns the final_match_result from the terminal state

    Args:
        vendor_profile_id:  PostgreSQL UUID string of the VendorProfile
        tender_mongo_id:    MongoDB ObjectId string of the tender document
        org_id:             Optional org UUID string for tenancy scoping
        score_threshold:    Min score for email notification (default 70.0)

    Returns:
        final_match_result dict (v3.0.0 schema) or error dict
    """
    graph = get_graph()

    # Each invocation gets a unique thread_id for MemorySaver checkpointing
    thread_id = str(uuid.uuid4())

    initial_state: TenderMatchState = {
        "vendor_profile_id": vendor_profile_id,
        "tender_mongo_id": tender_mongo_id,
        "org_id": org_id,
        "score_threshold": score_threshold,
        "current_stage": "start",
        "is_eligible": True,
        "tender_parsed": False,
        "persisted": False,
        "notification_sent": False,
        "final_score": 0.0,
        "semantic_score": 0.0,
        "extraction_confidence": 0.5,
    }

    config = {"configurable": {"thread_id": thread_id}}

    logger.info(
        "[Graph] Invoking pipeline. vendor=%s tender=%s thread=%s",
        vendor_profile_id, tender_mongo_id, thread_id,
    )

    try:
        final_state = await graph.ainvoke(initial_state, config=config)

        if final_state.get("error"):
            logger.error(
                "[Graph] Pipeline ended with error at stage=%s: %s",
                final_state.get("error_stage"), final_state["error"],
            )
            return {
                "status": "error",
                "error": final_state["error"],
                "error_stage": final_state.get("error_stage"),
                "vendor_profile_id": vendor_profile_id,
                "tender_mongo_id": tender_mongo_id,
            }

        result = final_state.get("final_match_result")
        if result:
            result.pop("_id", None)  # Strip any lingering Mongo _id

        logger.info(
            "[Graph] ✓ Pipeline complete. match_id=%s score=%.1f recommendation=%s thread=%s",
            final_state.get("match_id"),
            final_state.get("final_score", 0.0),
            final_state.get("recommendation"),
            thread_id,
        )
        return result or {"status": "error", "error": "No final_match_result in terminal state."}

    except Exception as exc:
        logger.error("[Graph] Unhandled exception in pipeline: %s", exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "vendor_profile_id": vendor_profile_id,
            "tender_mongo_id": tender_mongo_id,
        }
