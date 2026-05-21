"""
planner_models.py
-----------------
Pydantic / TypedDict models for the TenderMatch Planner Agent.

The Planner Agent is the first node in the LangGraph pipeline. It observes
incoming request context and produces a dynamic ExecutionPlan that all
downstream nodes consult to decide their behavior.

Design principles:
  - ExecutionPlan is a TypedDict (not Pydantic) so it can be stored directly
    inside TenderMatchState (which is itself a TypedDict for LangGraph compat).
  - PlannerInput is a plain Pydantic model used internally by the PlannerAgent
    service to validate and document its inputs.
  - PlannerCacheKey contains the fields used to compute the Redis cache key.
  - ExecutionPlanResult is the Pydantic-validated version used in tests and
    the Direct Orchestrator path where stricter validation is desirable.

Redis cache key format:  plan:{tender_id}:{vendor_profile_id}
Redis TTL: 3600 seconds (1 hour)
"""

from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field, field_validator, ConfigDict

# ─── Retrieval strategy options ───────────────────────────────────────────────

RetrievalStrategy = Literal["vector_only", "hybrid", "bm25_fallback"]
FilterStrictness = Literal["strict", "relaxed"]
ExplanationDepth = Literal["full", "summary"]


# ─── ExecutionPlan TypedDict ──────────────────────────────────────────────────
# TypedDict is used here (not Pydantic BaseModel) for direct compatibility with
# TenderMatchState, which LangGraph requires to be a TypedDict.

class ExecutionPlan(TypedDict, total=False):
    """
    Dynamic execution plan produced by the PlannerAgent node.
    Stored in TenderMatchState and consulted by all downstream nodes.

    Fields:
        skip_reingestion    — If True, the ingestion_agent skips re-fetching tender
                              embeddings from PG (they already exist and are current).
        retrieval_strategy  — Controls how HybridRetriever weights vector vs BM25:
                                "vector_only"   → alpha=1.0 (current behavior)
                                "hybrid"        → alpha=0.7 (default blend)
                                "bm25_fallback" → alpha=0.3 (BM25 dominant)
        require_ocr         — If True, the ingestion agent must use OCR on the PDF
                              (image-based document detected).
        filter_strictness   — "strict"  → all 5 hard filters enforced normally
                              "relaxed" → tolerance on profile-completeness-dependent
                              filters when vendor profile is < 50% complete
        explanation_depth   — "full"    → all explanation fields (default)
                              "summary" → condensed explanation to save LLM tokens
                              (used for low-scoring matches to reduce cost)
        invoke_critic       — Whether the critic_agent node should run.
                              Always True when score is in the ambiguous 55–85 range.
        rerank_results      — Whether to run the cross-encoder reranker on top-K
                              retrieved tender chunks before final scoring.
        plan_reasoning      — One-sentence justification for the choices made.
    """

    skip_reingestion: bool
    retrieval_strategy: RetrievalStrategy
    require_ocr: bool
    filter_strictness: FilterStrictness
    explanation_depth: ExplanationDepth
    invoke_critic: bool
    rerank_results: bool
    plan_reasoning: str


# ─── Default plan factory ─────────────────────────────────────────────────────

def default_execution_plan() -> ExecutionPlan:
    """
    Returns a safe, conservative default ExecutionPlan.
    Used when the planner is bypassed or fails gracefully.
    """
    return ExecutionPlan(
        skip_reingestion=False,
        retrieval_strategy="hybrid",
        require_ocr=False,
        filter_strictness="strict",
        explanation_depth="full",
        invoke_critic=True,
        rerank_results=False,
        plan_reasoning="Default plan: no context available for dynamic planning.",
    )


# ─── PlannerInput (Pydantic) ──────────────────────────────────────────────────

class PlannerInput(BaseModel):
    """
    Validated inputs to the PlannerAgent service.
    Derived from TenderMatchState fields at the start of the pipeline.

    Fields:
        tender_id               — MongoDB ObjectId of the tender (for cache key).
        vendor_profile_id       — PostgreSQL UUID of the vendor profile (for cache key).
        profile_completeness_pct— Vendor profile completeness (0–100). Controls
                                  retrieval strategy and filter strictness.
        embeddings_exist        — True if tender embeddings already exist in PG,
                                  enabling skip_reingestion optimization.
        tender_source_type      — Source of the tender document:
                                  "pdf" | "api" | "scraped" | "unknown"
        is_rerun                — True if this is a re-run (not first-time matching).
        prior_final_score       — Final score from a prior run (if is_rerun=True).
                                  Used to determine invoke_critic and explanation_depth.
        prior_retrieval_strategy— Retrieval strategy used in the prior run.
    """

    tender_id: str = Field(description="MongoDB ObjectId of the tender.")
    vendor_profile_id: str = Field(description="PostgreSQL UUID of the vendor profile.")
    profile_completeness_pct: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Vendor profile completeness percentage (0–100).",
    )
    embeddings_exist: bool = Field(
        default=False,
        description="True if tender embeddings already exist in PostgreSQL.",
    )
    tender_source_type: Literal["pdf", "api", "scraped", "unknown"] = Field(
        default="unknown",
        description="How the tender document was sourced.",
    )
    is_rerun: bool = Field(
        default=False,
        description="True if this is a re-run of a previously matched pair.",
    )
    prior_final_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Final score from a prior run. Only set when is_rerun=True.",
    )
    prior_retrieval_strategy: Optional[RetrievalStrategy] = Field(
        default=None,
        description="Retrieval strategy used in the prior run (for continuity).",
    )

    @field_validator("profile_completeness_pct")
    @classmethod
    def clamp_completeness(cls, v: float) -> float:
        """Clamp to [0, 100] — defensive against bad data upstream."""
        return max(0.0, min(100.0, v))

    model_config = ConfigDict(extra="forbid")

    # ── Convenience properties ─────────────────────────────────────────────────

    @property
    def is_low_completeness(self) -> bool:
        """True if profile completeness is below 40% (BM25 fallback territory)."""
        return self.profile_completeness_pct < 40.0

    @property
    def is_borderline_completeness(self) -> bool:
        """True if profile completeness is in the ambiguous 40–55% range."""
        return 40.0 <= self.profile_completeness_pct < 55.0

    @property
    def is_high_completeness(self) -> bool:
        """True if profile completeness is at or above 70%."""
        return self.profile_completeness_pct >= 70.0

    def cache_key(self) -> str:
        """Redis cache key for this planner input."""
        return f"plan:{self.tender_id}:{self.vendor_profile_id}"


# ─── ExecutionPlanResult (Pydantic) ──────────────────────────────────────────
# Pydantic-validated version of ExecutionPlan for tests and Direct Orchestrator.
# Kept as a separate model to avoid mixing TypedDict and Pydantic in state.

class ExecutionPlanResult(BaseModel):
    """
    Pydantic-validated mirror of ExecutionPlan TypedDict.
    Used in tests, Direct Orchestrator, and Redis serialization/deserialization.

    All fields mirror ExecutionPlan exactly — see that docstring for semantics.
    """

    skip_reingestion: bool = Field(default=False)
    retrieval_strategy: RetrievalStrategy = Field(default="hybrid")
    require_ocr: bool = Field(default=False)
    filter_strictness: FilterStrictness = Field(default="strict")
    explanation_depth: ExplanationDepth = Field(default="full")
    invoke_critic: bool = Field(default=True)
    rerank_results: bool = Field(default=False)
    plan_reasoning: str = Field(
        default="Default plan.",
        description="One-sentence justification for the plan choices.",
    )

    model_config = ConfigDict(extra="forbid")

    def to_typed_dict(self) -> ExecutionPlan:
        """Convert to ExecutionPlan TypedDict for injection into TenderMatchState."""
        return ExecutionPlan(
            skip_reingestion=self.skip_reingestion,
            retrieval_strategy=self.retrieval_strategy,
            require_ocr=self.require_ocr,
            filter_strictness=self.filter_strictness,
            explanation_depth=self.explanation_depth,
            invoke_critic=self.invoke_critic,
            rerank_results=self.rerank_results,
            plan_reasoning=self.plan_reasoning,
        )

    def to_redis_dict(self) -> dict:
        """Serialize to a flat dict for Redis storage (JSON-safe)."""
        return self.model_dump()

    @classmethod
    def from_redis_dict(cls, data: dict) -> "ExecutionPlanResult":
        """Deserialize from Redis-stored dict."""
        return cls(**data)


# ─── PlannerCacheEntry ────────────────────────────────────────────────────────

class PlannerCacheEntry(BaseModel):
    """
    Full Redis cache entry stored under key plan:{tender_id}:{vendor_profile_id}.
    Wraps the ExecutionPlanResult with metadata for cache management.
    """

    plan: ExecutionPlanResult = Field(description="The cached execution plan.")
    cached_at: datetime = Field(description="UTC timestamp when the plan was cached.")
    cache_hit_count: int = Field(
        default=0,
        description="Number of times this cached plan has been served.",
    )
    planner_used_llm: bool = Field(
        default=False,
        description="True if the Planner used a Groq LLM call (ambiguous input).",
    )

    model_config = ConfigDict(extra="forbid")

    def to_redis_dict(self) -> dict:
        """Serialize to a JSON-safe dict for Redis SETEX."""
        return {
            "plan": self.plan.to_redis_dict(),
            "cached_at": self.cached_at.isoformat(),
            "cache_hit_count": self.cache_hit_count,
            "planner_used_llm": self.planner_used_llm,
        }

    @classmethod
    def from_redis_dict(cls, data: dict) -> "PlannerCacheEntry":
        """Deserialize from Redis-stored dict."""
        return cls(
            plan=ExecutionPlanResult(**data["plan"]),
            cached_at=datetime.fromisoformat(data["cached_at"]),
            cache_hit_count=data.get("cache_hit_count", 0),
            planner_used_llm=data.get("planner_used_llm", False),
        )
