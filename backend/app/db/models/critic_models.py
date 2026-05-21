"""
critic_models.py
----------------
Pydantic models for the TenderMatch Critic Agent.

The Critic Agent is a deterministic (no-LLM) validation layer that sits
between the explanation_agent and notification_agent. It checks whether the
LLM-generated explanation is internally consistent with the raw numerical
scores and hard-filter results.

Schema hierarchy:
  CriticFinding   — result of a single consistency rule check
  CriticReport    — aggregated report across all six rules

Recommendation enum alignment (matches explanation_service.py):
  HIGH_MATCH       → final_score >= 80  (and filter pass)
  MODERATE_MATCH   → 60 <= score < 80   (and filter pass)
  LOW_MATCH        → 40 <= score < 60   (and filter pass)
  NOT_ELIGIBLE     → score < 40  OR  filter fail
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# ─── Severity levels ──────────────────────────────────────────────────────────

SeverityLevel = Literal["ERROR", "WARNING", "INFO"]
WorstSeverity = Literal["ERROR", "WARNING", "INFO", "CLEAN"]

# ─── Recommendation label constants ──────────────────────────────────────────
# Must stay in sync with explanation_service._determine_recommendation()

RECOMMENDATION_HIGH = "HIGH_MATCH"
RECOMMENDATION_MODERATE = "MODERATE_MATCH"
RECOMMENDATION_LOW = "LOW_MATCH"
RECOMMENDATION_NOT_ELIGIBLE = "NOT_ELIGIBLE"

VALID_RECOMMENDATIONS = {
    RECOMMENDATION_HIGH,
    RECOMMENDATION_MODERATE,
    RECOMMENDATION_LOW,
    RECOMMENDATION_NOT_ELIGIBLE,
}

# Threshold mapping used by the Critic to derive safe corrected recommendations
# When the Critic overrides an explanation it uses this — NOT the LLM.
SCORE_TO_RECOMMENDATION = [
    (80.0, RECOMMENDATION_HIGH),       # score >= 80
    (60.0, RECOMMENDATION_MODERATE),   # 60 <= score < 80
    (40.0, RECOMMENDATION_LOW),        # 40 <= score < 60
    (0.0,  RECOMMENDATION_NOT_ELIGIBLE),  # score < 40
]


def score_to_recommendation(final_score: float, filter_passed: bool) -> str:
    """
    Deterministic recommendation derived purely from numerical score and filter.
    This is the single source of truth used by the Critic when overriding.

    Args:
        final_score:    Weighted final score (0–100 scale).
        filter_passed:  Whether the vendor passed all hard filters.

    Returns:
        One of HIGH_MATCH | MODERATE_MATCH | LOW_MATCH | NOT_ELIGIBLE
    """
    if not filter_passed:
        return RECOMMENDATION_NOT_ELIGIBLE
    for threshold, label in SCORE_TO_RECOMMENDATION:
        if final_score >= threshold:
            return label
    return RECOMMENDATION_NOT_ELIGIBLE


# ─── CriticFinding ────────────────────────────────────────────────────────────

class CriticFinding(BaseModel):
    """
    Result of a single consistency rule check performed by the Critic Agent.

    Fields:
        check_name  — Unique identifier for the rule, e.g. "recommendation_score_alignment"
        severity    — ERROR (pipeline-critical), WARNING (advisory), INFO (observational)
        passed      — True if the check passed, False if a problem was detected
        expected    — Human-readable description of what was expected
        actual      — Human-readable description of what was actually found
        detail      — Full explanation of the finding, including dimension names and values
    """

    check_name: str = Field(
        description="Unique identifier for the consistency rule being checked."
    )
    severity: SeverityLevel = Field(
        description="Severity level: ERROR overrides output, WARNING appends, INFO logs only."
    )
    passed: bool = Field(
        description="True if this specific check passed without issues."
    )
    expected: str = Field(
        description="What the Critic expected to find given the numerical data."
    )
    actual: str = Field(
        description="What was actually found in the LLM-generated explanation."
    )
    detail: str = Field(
        description="Full human-readable explanation of the finding."
    )

    # Allow arbitrary types for forward-compat with future extensions
    model_config = ConfigDict(extra="forbid")


# ─── CriticReport ─────────────────────────────────────────────────────────────

class CriticReport(BaseModel):
    """
    Aggregated report from all Critic Agent consistency checks for a single
    vendor-tender explanation.

    This document is:
      1. Stored in TenderMatchState as `critic_report`
      2. Persisted to MongoDB match_results under the `critic_report` key
      3. Exposed via GET /match/{match_id} in the frontend-facing payload

    Fields:
        total_checks    — Total number of rules evaluated
        passed_checks   — Number of rules that passed
        failed_checks   — Number of rules that detected an issue (passed=False)
        worst_severity  — The most critical severity found across all findings;
                          CLEAN if all passed
        findings        — Full list of CriticFinding objects for all checks
        overridden      — True if the Critic replaced the recommendation
        override_reason — Reason for override (populated only when overridden=True)
        evaluated_at    — UTC timestamp of when the Critic ran
    """

    total_checks: int = Field(
        description="Total number of consistency rules evaluated."
    )
    passed_checks: int = Field(
        description="Number of rules that passed without issues."
    )
    failed_checks: int = Field(
        description="Number of rules that detected an inconsistency (passed=False)."
    )
    worst_severity: WorstSeverity = Field(
        description="Most critical severity across all findings. CLEAN if all passed."
    )
    findings: List[CriticFinding] = Field(
        default_factory=list,
        description="Full ordered list of CriticFinding results for each rule."
    )
    overridden: bool = Field(
        default=False,
        description="True if the Critic overrode the LLM recommendation due to ERROR findings."
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Explanation of why the Critic overrode the output (ERROR cases only)."
    )
    evaluated_at: datetime = Field(
        description="UTC timestamp of when the Critic Agent evaluation ran."
    )

    model_config = ConfigDict(extra="forbid")

    # ── Convenience helpers ────────────────────────────────────────────────────

    def errors(self) -> List[CriticFinding]:
        """Return all ERROR-level findings."""
        return [f for f in self.findings if f.severity == "ERROR" and not f.passed]

    def warnings(self) -> List[CriticFinding]:
        """Return all WARNING-level findings."""
        return [f for f in self.findings if f.severity == "WARNING" and not f.passed]

    def info_findings(self) -> List[CriticFinding]:
        """Return all INFO-level findings."""
        return [f for f in self.findings if f.severity == "INFO" and not f.passed]

    def has_errors(self) -> bool:
        """True if any ERROR-severity findings exist."""
        return any(f.severity == "ERROR" and not f.passed for f in self.findings)

    def has_warnings(self) -> bool:
        """True if any WARNING-severity findings exist."""
        return any(f.severity == "WARNING" and not f.passed for f in self.findings)

    def to_mongo_dict(self) -> dict:
        """
        Serialize the report to a MongoDB-compatible dict.
        Converts datetime to ISO string for BSON compatibility.
        """
        data = self.model_dump()
        data["evaluated_at"] = self.evaluated_at.isoformat()
        return data
