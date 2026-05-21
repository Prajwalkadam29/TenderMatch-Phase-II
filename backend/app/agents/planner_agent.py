"""
planner_agent.py
----------------
Node 1 of the TenderMatch LangGraph pipeline.

Responsibilities:
  - Extract context from TenderMatchState.
  - Call PlannerService to generate or retrieve an ExecutionPlan.
  - Update TenderMatchState with the ExecutionPlan so downstream nodes can adapt.
"""

import logging
from typing import Dict, Any

from app.agents.state import TenderMatchState
from app.services.planner_service import PlannerService
from app.db.models.planner_models import PlannerInput
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)


async def planner_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: Dynamically plans the execution path.
    """
    logger.info("[Agent:Planner] START")

    vendor_profile_id = state.get("vendor_profile_id")
    tender_mongo_id = state.get("tender_mongo_id")
    
    # Extract hints from state (might be populated by API entrypoint or ingestion)
    # If this is the absolute first node, we might not have full vendor_data yet,
    # but the API endpoint might have injected hints into the state, or we default to 50.
    vendor_data = state.get("vendor_profile_data", {})
    completeness = vendor_data.get("profile_completeness_pct")
    
    if completeness is None:
        from app.core.postgres import get_pg_session
        from app.db.models.document import VendorProfile
        from sqlalchemy import select
        try:
            async with get_pg_session() as session:
                stmt = select(VendorProfile.profile_completeness_pct).where(VendorProfile.id == vendor_profile_id)
                res = await session.execute(stmt)
                fetched = res.scalar_one_or_none()
                if fetched is not None:
                    completeness = float(fetched)
        except Exception as e:
            logger.error("[Agent:Planner] Failed to fetch completeness: %s", e)
            
    if completeness is None:
        completeness = 50.0
    
    # We might know if it's a rerun from state flags
    is_rerun = state.get("is_rerun", False)
    prior_score = state.get("prior_final_score")
    
    # For now, default to unknown source and false embeddings unless explicitly passed
    source_type = state.get("tender_source_type", "unknown")
    embeddings_exist = state.get("tender_embeddings_exist", False)

    planner_input = PlannerInput(
        tender_id=tender_mongo_id,
        vendor_profile_id=vendor_profile_id,
        profile_completeness_pct=completeness,
        embeddings_exist=embeddings_exist,
        tender_source_type=source_type,
        is_rerun=is_rerun,
        prior_final_score=prior_score
    )

    redis_client = get_redis()
    
    if not redis_client:
        logger.warning("[Agent:Planner] Redis not available, using default plan.")
        from app.db.models.planner_models import default_execution_plan
        plan_dict = default_execution_plan()
    else:
        service = PlannerService(redis_client)
        plan_result = await service.get_or_create_plan(planner_input)
        plan_dict = plan_result.to_typed_dict()

    logger.info("[Agent:Planner] ✓ Plan generated. Strategy=%s, Depth=%s", 
                plan_dict.get("retrieval_strategy"), 
                plan_dict.get("explanation_depth"))

    return {
        "current_stage": "planning_complete",
        "execution_plan": plan_dict
    }
