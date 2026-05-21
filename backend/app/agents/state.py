"""
state.py
--------
TenderMatchState — the single shared state object that flows through
every node of the TenderMatch LangGraph pipeline.

Using TypedDict (not a Pydantic model) as required by LangGraph's
StateGraph. All fields have defaults to allow partial updates from nodes.
"""

from typing import Optional, TypedDict


class TenderMatchState(TypedDict, total=False):
    """
    Immutable-by-convention state that is threaded through every node.
    Each node returns a partial dict — LangGraph merges it into the state.

    Fields are grouped by pipeline stage for readability.
    """

    # ── Inputs (required at graph invocation) ─────────────────────────────────
    vendor_profile_id: str        # PostgreSQL UUID of VendorProfile
    tender_mongo_id: str          # MongoDB ObjectId of the tender document
    org_id: Optional[str]         # Org UUID for multi-tenancy scoping
    score_threshold: float        # Min score for email notification (default 70.0)

    # ── Stage 1: Data Loading (ingestion_agent) ───────────────────────────────
    vendor_profile_data: Optional[dict]    # profile_data JSONB from Postgres
    vendor_embedding: Optional[list]       # 384-dim embedding from VendorProfile
    vendor_vendor_id: Optional[str]        # Vendor ID string e.g. "V-001"
    vendor_pg_uuid: Optional[str]          # Postgres UUID string of vendor
    custom_weights: Optional[dict]         # Learned weights from WeightResolver
    tender_doc: Optional[dict]             # Full MongoDB document
    tender_structured_data: Optional[dict] # tender_doc["structured_data"]
    tender_pg_embedding: Optional[list]    # 384-dim embedding from Postgres tenders
    extraction_confidence: float           # From ingestion pipeline (0.0–1.0)

    # ── Stage 2: Parsing/Validation (parsing_agent) ───────────────────────────
    tender_parsed: bool                    # True if structured_data is usable
    parse_warnings: Optional[list]         # Non-fatal issues found during parsing

    # ── Stage 3: Hard Filter (filter_agent) ──────────────────────────────────
    filter_result: Optional[dict]          # Output of HardFilterEngine.evaluate()
    is_eligible: bool                      # True if all hard filters passed

    # ── Stage 4: Scoring (scoring_agent) ─────────────────────────────────────
    semantic_score: float                  # Cosine similarity (0.0–1.0)
    score_result: Optional[dict]           # Output of WeightedScoringEngine.calculate_score()
    final_score: float                     # 0–100 final weighted score

    # ── Stage 5: Explanation (explanation_agent) ──────────────────────────────
    explanation_result: Optional[dict]     # ExplanationResult serialized to dict

    # ── Stage 6: Persistence (persist happens inside orchestrate, or graph node)
    match_id: Optional[str]               # Canonical match ID e.g. "MR-V-001-abc12345"
    persisted: bool                        # True once saved to MongoDB match_results

    # ── Stage 7: Notification (notification_agent) ────────────────────────────
    notification_sent: bool                # True if email dispatched
    notification_skipped_reason: Optional[str]

    # ── Final output ──────────────────────────────────────────────────────────
    recommendation: Optional[str]          # HIGH_MATCH | MODERATE_MATCH | LOW_MATCH | NOT_ELIGIBLE
    final_match_result: Optional[dict]     # Complete v3.0.0 result document

    # ── Agentic Engine Fields ─────────────────────────────────────────────────
    execution_plan: Optional[dict]         # From planner_agent
    retrieval_scores: Optional[dict]       # From HybridRetriever (vector_score, bm25, hybrid)
    critic_report: Optional[dict]          # Full findings from CriticAgent
    critic_overridden: bool                # Whether explanation was modified by Critic
    critic_severity: Optional[str]         # Worst severity found: ERROR | WARNING | INFO | CLEAN
    is_rerun: bool                         # Hints for planner
    prior_final_score: Optional[float]
    tender_source_type: Optional[str]
    tender_embeddings_exist: Optional[bool]

    # ── Error tracking ────────────────────────────────────────────────────────
    error: Optional[str]                   # Error message if a node failed
    error_stage: Optional[str]             # Which node raised the error
    current_stage: str                     # Current pipeline stage (for observability)
