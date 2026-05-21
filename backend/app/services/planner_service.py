"""
planner_service.py
------------------
Dynamic Planning Engine for the TenderMatch AI Pipeline.

Evaluates the incoming context (vendor completeness, tender source) and produces
an ExecutionPlan that dictates how downstream nodes should behave. Utilizes Redis
caching to make re-runs cheap. Falls back to a lightweight LLM call if the context
is genuinely ambiguous.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from groq import AsyncGroq
from redis.asyncio import Redis

from app.core.config import settings
from app.db.models.planner_models import (
    ExecutionPlanResult,
    PlannerInput,
    PlannerCacheEntry,
)

logger = logging.getLogger(__name__)


class PlannerService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get_or_create_plan(self, planner_input: PlannerInput) -> ExecutionPlanResult:
        """
        Main entry point. Checks cache first, else generates and caches a new plan.
        """
        cache_key = planner_input.cache_key()
        
        # 1. Try Cache
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            try:
                entry = PlannerCacheEntry.from_redis_dict(json.loads(cached_data))
                entry.cache_hit_count += 1
                await self.redis.setex(cache_key, 3600, json.dumps(entry.to_redis_dict()))
                logger.info("[Planner] ✓ Cache hit for %s", cache_key)
                return entry.plan
            except Exception as e:
                logger.warning("[Planner] Failed to parse cached plan, re-generating: %s", e)

        # 2. Generate Plan
        logger.info("[Planner] Cache miss for %s. Generating new plan.", cache_key)
        plan, used_llm = await self._generate_plan(planner_input)

        # 3. Cache Result
        try:
            entry = PlannerCacheEntry(
                plan=plan,
                cached_at=datetime.now(timezone.utc),
                cache_hit_count=0,
                planner_used_llm=used_llm
            )
            await self.redis.setex(cache_key, 3600, json.dumps(entry.to_redis_dict()))
        except Exception as e:
            logger.error("[Planner] Failed to cache plan: %s", e)
            
        return plan

    async def _generate_plan(self, planner_input: PlannerInput) -> tuple[ExecutionPlanResult, bool]:
        """
        Generates a plan deterministically. If ambiguous, calls LLM.
        Returns: (ExecutionPlanResult, used_llm: bool)
        """
        # --- Deterministic Rules ---
        
        # skip_reingestion is always True if embeddings already exist
        skip_reingestion = planner_input.embeddings_exist
        
        require_ocr = False # Defaults to False, could be overridden if PDF is image-based (not passed in input, but standard behavior)
        
        if planner_input.is_high_completeness:
            # Clear cut high-quality profile
            return ExecutionPlanResult(
                skip_reingestion=skip_reingestion,
                retrieval_strategy="vector_only",
                require_ocr=require_ocr,
                filter_strictness="strict",
                explanation_depth="full",
                invoke_critic=False, # Wait, only invoke critic if ambiguous. Actually, if prior score is known, we can check.
                rerank_results=False,
                plan_reasoning="High completeness vendor; proceeding with strict vector search."
            ), False

        if planner_input.is_low_completeness:
            # Clear cut low-quality profile
            return ExecutionPlanResult(
                skip_reingestion=skip_reingestion,
                retrieval_strategy="bm25_fallback",
                require_ocr=require_ocr,
                filter_strictness="relaxed",
                explanation_depth="summary",
                invoke_critic=False,
                rerank_results=False,
                plan_reasoning="Low completeness vendor; using BM25 fallback and relaxed filters."
            ), False

        # If it's a re-run and we have prior scores, we can be smart
        if planner_input.is_rerun and planner_input.prior_final_score is not None:
            score = planner_input.prior_final_score
            invoke_critic = 55 <= score <= 85
            return ExecutionPlanResult(
                skip_reingestion=skip_reingestion,
                retrieval_strategy=planner_input.prior_retrieval_strategy or "hybrid",
                require_ocr=require_ocr,
                filter_strictness="strict",
                explanation_depth="full" if score >= 40 else "summary",
                invoke_critic=invoke_critic,
                rerank_results=invoke_critic, # Rerank if ambiguous
                plan_reasoning="Re-run with known score; preserving strategy and conditionally triggering critic."
            ), False

        # --- Ambiguous Zone (40-55% completeness OR unknown source) ---
        logger.info("[Planner] Ambiguous context (completeness=%.1f). Invoking LLM for plan.", planner_input.profile_completeness_pct)
        try:
            plan = await self._call_llm_planner(planner_input)
            plan.skip_reingestion = skip_reingestion # Preserve deterministic override
            plan.invoke_critic = True # Always True for ambiguous zone
            return plan, True
        except Exception as e:
            logger.error("[Planner] LLM failed, falling back to safe default: %s", e)
            return ExecutionPlanResult(
                skip_reingestion=skip_reingestion,
                retrieval_strategy="hybrid",
                require_ocr=require_ocr,
                filter_strictness="strict",
                explanation_depth="full",
                invoke_critic=True,
                rerank_results=True,
                plan_reasoning="Fallback plan after LLM failure."
            ), False

    async def _call_llm_planner(self, planner_input: PlannerInput) -> ExecutionPlanResult:
        """Lightweight LLM call to decide plan."""
        system_prompt = """You are the TenderMatch Execution Planner.
Decide the best execution plan based on the input context.
Respond ONLY with a JSON object matching this structure:
{
    "retrieval_strategy": "vector_only" | "hybrid" | "bm25_fallback",
    "filter_strictness": "strict" | "relaxed",
    "explanation_depth": "full" | "summary",
    "rerank_results": true | false,
    "plan_reasoning": "<1 sentence reasoning>"
}
"""
        user_prompt = f"""Context:
- Vendor Completeness: {planner_input.profile_completeness_pct}%
- Tender Source: {planner_input.tender_source_type}
- Re-run: {planner_input.is_rerun}
"""
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        
        raw = response.choices[0].message.content.strip()
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
        else:
            data = json.loads(raw)
            
        return ExecutionPlanResult(
            retrieval_strategy=data.get("retrieval_strategy", "hybrid"),
            filter_strictness=data.get("filter_strictness", "strict"),
            explanation_depth=data.get("explanation_depth", "full"),
            rerank_results=data.get("rerank_results", False),
            plan_reasoning=data.get("plan_reasoning", "LLM decided plan.")
        )
