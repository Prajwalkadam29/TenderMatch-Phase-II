"""
test_explanation_engine.py
--------------------------
Tests for Component 4: LLM Explanation Engine.

Covers:
  - ExplanationResult Pydantic schema validation
  - Fallback explanation under every score band
  - _fmt_inr formatting
  - _determine_recommendation logic
  - Full async generate_explanation with mocked Groq
  - Graceful degradation when LLM fails (fallback triggers correctly)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from app.services.explanation_service import (
    ExplanationResult,
    ScoreRationale,
    _fmt_inr,
    _determine_recommendation,
    _build_fallback_explanation,
    generate_explanation,
)


# ─── Unit: _fmt_inr ──────────────────────────────────────────────────────────

class TestFmtInr:
    def test_crores(self):
        assert "Cr" in _fmt_inr(50_000_000)

    def test_lakhs(self):
        assert "L" in _fmt_inr(500_000)

    def test_small(self):
        assert "₹50,000" in _fmt_inr(50000)

    def test_none(self):
        assert _fmt_inr(None) == "Not specified"

    def test_string_input(self):
        # Should coerce "50000000" string to int
        result = _fmt_inr("50000000")
        assert "Cr" in result


# ─── Unit: _determine_recommendation ─────────────────────────────────────────

class TestDetermineRecommendation:
    def test_not_eligible_when_filter_fails(self):
        assert _determine_recommendation(95.0, False) == "NOT_ELIGIBLE"

    def test_high_match(self):
        assert _determine_recommendation(85.0, True) == "HIGH_MATCH"

    def test_moderate_match(self):
        assert _determine_recommendation(70.0, True) == "MODERATE_MATCH"

    def test_low_match(self):
        assert _determine_recommendation(50.0, True) == "LOW_MATCH"

    def test_not_eligible_low_score(self):
        assert _determine_recommendation(30.0, True) == "NOT_ELIGIBLE"


# ─── Unit: ExplanationResult Pydantic schema ─────────────────────────────────

class TestExplanationResultSchema:
    def test_valid_construction(self):
        result = ExplanationResult(
            executive_summary="Strong match.",
            strengths=["Domain match", "Good financials"],
            risk_factors=["Missing ISO 27001"],
            score_rationale=ScoreRationale(domain="Exact match.", geography="Operational in state."),
            recommendation="HIGH_MATCH",
            recommendation_detail="Proceed with bid preparation.",
        )
        assert result.recommendation == "HIGH_MATCH"
        assert len(result.strengths) == 2

    def test_recommendation_normalized_to_uppercase(self):
        result = ExplanationResult(
            executive_summary="X", strengths=[], risk_factors=[],
            recommendation="high_match",
            recommendation_detail="Go for it.",
        )
        assert result.recommendation == "HIGH_MATCH"

    def test_invalid_recommendation_fallback(self):
        result = ExplanationResult(
            executive_summary="X", strengths=[], risk_factors=[],
            recommendation="UNKNOWN_VALUE",
            recommendation_detail="Test.",
        )
        assert result.recommendation == "LOW_MATCH"

    def test_strengths_defaults_to_empty_list(self):
        result = ExplanationResult(
            executive_summary="X",
            recommendation="LOW_MATCH",
            recommendation_detail="Review carefully.",
        )
        assert result.strengths == []


# ─── Unit: Fallback explanation ───────────────────────────────────────────────

def _make_score_result(final_score: float, domain=1.0, financial=1.0, experience=1.0, certification=1.0) -> dict:
    return {
        "final_score": final_score,
        "breakdown": {
            "domain": {"raw_score": domain, "weighted_score": domain * 0.25},
            "geography": {"raw_score": 1.0, "weighted_score": 0.15},
            "financial": {"raw_score": financial, "weighted_score": financial * 0.20},
            "experience": {"raw_score": experience, "weighted_score": experience * 0.15},
            "certification": {"raw_score": certification, "weighted_score": certification * 0.10},
            "semantic": {"raw_score": 1.0, "weighted_score": 0.10},
            "confidence": {"raw_score": 1.0, "weighted_score": 0.05},
        }
    }


class TestFallbackExplanation:
    VENDOR = {
        "business_name": "TestCorp",
        "business_domain": {"primary_domains": ["IT"]},
        "geography": {"operational_states": ["Delhi"]},
        "financials": {"avg_annual_turnover_inr": 5000000},
        "certifications": {"iso_certifications": [{"standard": "ISO 9001"}]},
        "past_project_experience": {"projects": []},
        "compliance": {"blacklisted_or_debarred": False},
        "profile_completeness_pct": 80,
    }
    TENDER = {
        "domain": "IT",
        "location_state": "Delhi",
        "estimated_value": 1000000,
        "mandatory_certifications": [],
        "scope_summary": "IT infra setup",
    }

    def test_high_match_fallback(self):
        filter_ok = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
        result = _build_fallback_explanation(self.VENDOR, self.TENDER, filter_ok, _make_score_result(85.0))
        assert result.recommendation == "HIGH_MATCH"
        assert result.executive_summary != ""

    def test_moderate_match_fallback(self):
        filter_ok = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
        result = _build_fallback_explanation(self.VENDOR, self.TENDER, filter_ok, _make_score_result(65.0))
        assert result.recommendation == "MODERATE_MATCH"

    def test_not_eligible_fallback(self):
        filter_fail = {"overall_pass": False, "disqualification_reason": "Blacklisted.", "failed_check": "blacklist"}
        result = _build_fallback_explanation(self.VENDOR, self.TENDER, filter_fail, _make_score_result(0.0))
        assert result.recommendation == "NOT_ELIGIBLE"
        assert "Blacklisted" in result.executive_summary

    def test_strengths_populated_for_high_score(self):
        filter_ok = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
        result = _build_fallback_explanation(self.VENDOR, self.TENDER, filter_ok, _make_score_result(85.0))
        assert len(result.strengths) >= 1

    def test_risk_factors_populated_for_low_score(self):
        filter_ok = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
        score = _make_score_result(30.0, domain=0.1, financial=0.1, experience=0.1, certification=0.1)
        result = _build_fallback_explanation(self.VENDOR, self.TENDER, filter_ok, score)
        assert len(result.risk_factors) >= 1


# ─── Integration: generate_explanation with mocked LLM ───────────────────────

@pytest.mark.asyncio
async def test_generate_explanation_success():
    """Tests the full async path with a mocked Groq response."""
    mock_llm_response = {
        "executive_summary": "Strong match with 87/100 score.",
        "strengths": ["Domain alignment", "Exceeds financial threshold"],
        "risk_factors": ["ISO 27001 not confirmed"],
        "score_rationale": {
            "domain": "Exact domain match.",
            "geography": "Vendor registered in tender state.",
            "financial": "Turnover 3x the tender value.",
            "experience": "Completed similar projects.",
            "certification": "Holds ISO 9001.",
            "semantic": "High scope overlap."
        },
        "recommendation": "HIGH_MATCH",
        "recommendation_detail": "Proceed to bid preparation immediately.",
        "confidence_note": None
    }

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_llm_response)
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    vendor = {
        "identity": {"business_name": "TechVentures Pvt. Ltd."},
        "business_domain": {"primary_domains": ["Information Technology"]},
        "geography": {"operational_states": ["Delhi"], "registered_states": []},
        "financials": {"avg_annual_turnover_inr": 3000000},
        "certifications": {"iso_certifications": [{"standard": "ISO 9001"}], "domain_licenses": []},
        "past_project_experience": {"projects": [{"contract_value_inr": 1200000}]},
        "compliance": {"blacklisted_or_debarred": False, "gst_returns_compliant": True, "epf_esic_compliant": True},
        "profile_completeness_pct": 85,
    }
    tender = {
        "domain": "Information Technology",
        "location_state": "Delhi",
        "estimated_value": 1000000,
        "min_avg_turnover": 500000,
        "mandatory_certifications": ["ISO 9001"],
        "scope_summary": "Enterprise IT infrastructure setup.",
        "source_portal": "GeM",
        "deadline": {"bid_submission": "2026-07-01"},
    }
    filter_result = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
    score_result = _make_score_result(87.0)

    with patch("app.services.explanation_service.AsyncGroq") as MockGroq:
        instance = AsyncMock()
        instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        MockGroq.return_value = instance

        result = await generate_explanation(vendor, tender, filter_result, score_result, extraction_confidence=0.85)

    assert result.recommendation == "HIGH_MATCH"
    assert "87" in result.executive_summary
    assert len(result.strengths) == 2
    assert result.confidence_note is None


@pytest.mark.asyncio
async def test_generate_explanation_llm_failure_uses_fallback():
    """Verifies that LLM failures trigger the programmatic fallback gracefully."""
    vendor = {
        "identity": {"business_name": "FallbackCorp"},
        "business_domain": {"primary_domains": ["Construction"]},
        "geography": {"operational_states": ["Mumbai"]},
        "financials": {"avg_annual_turnover_inr": 10000000},
        "certifications": {},
        "past_project_experience": {"projects": [{"contract_value_inr": 5000000}]},
        "compliance": {"blacklisted_or_debarred": False},
        "profile_completeness_pct": 70,
    }
    tender = {"domain": "Construction", "location_state": "Mumbai", "estimated_value": 5000000}
    filter_result = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
    score_result = _make_score_result(72.0)

    with patch("app.services.explanation_service.AsyncGroq") as MockGroq:
        instance = AsyncMock()
        instance.chat.completions.create = AsyncMock(side_effect=Exception("Groq API unreachable"))
        MockGroq.return_value = instance

        result = await generate_explanation(vendor, tender, filter_result, score_result)

    assert result.recommendation in {"MODERATE_MATCH", "HIGH_MATCH", "LOW_MATCH", "NOT_ELIGIBLE"}
    assert result.executive_summary != ""
    assert isinstance(result.strengths, list)


@pytest.mark.asyncio
async def test_generate_explanation_low_confidence_adds_note():
    """Verifies that low extraction confidence triggers a confidence note."""
    mock_llm_response = {
        "executive_summary": "Moderate match.",
        "strengths": ["Domain match"],
        "risk_factors": ["Low extraction confidence"],
        "score_rationale": {"domain": "Matched.", "geography": "OK.", "financial": "OK.", "experience": "Limited.", "certification": "None.", "semantic": "Partial."},
        "recommendation": "MODERATE_MATCH",
        "recommendation_detail": "Verify tender document manually.",
        "confidence_note": None
    }

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_llm_response)
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    vendor = {
        "identity": {}, "business_domain": {}, "geography": {},
        "financials": {}, "certifications": {}, "past_project_experience": {},
        "compliance": {}, "profile_completeness_pct": 50,
    }
    tender = {}
    filter_result = {"overall_pass": True, "disqualification_reason": None, "failed_check": None}
    score_result = _make_score_result(63.0)

    with patch("app.services.explanation_service.AsyncGroq") as MockGroq:
        instance = AsyncMock()
        instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        MockGroq.return_value = instance

        result = await generate_explanation(
            vendor, tender, filter_result, score_result,
            extraction_confidence=0.3  # Low confidence
        )

    assert result.confidence_note is not None
    assert "30%" in result.confidence_note
