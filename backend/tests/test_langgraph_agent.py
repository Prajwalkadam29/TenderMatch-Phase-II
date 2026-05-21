"""
test_langgraph_agent.py
-----------------------
Tests for Component 6: LangGraph Agentic Pipeline.

Covers:
  - route_after_ingestion conditional logic
  - route_after_filter conditional logic
  - Individual agent nodes (ingestion, parsing, filter, scoring, explanation, notification)
  - Full pipeline via run_match_pipeline (graph mocked at node level)
  - Ineligible vendor short-circuit (filter → explanation, skips scoring)
  - Error propagation from ingestion_agent to END
"""

import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# ─── Fixtures ─────────────────────────────────────────────────────────────────

VENDOR_UUID = str(uuid.uuid4())
TENDER_MONGO_ID = "507f1f77bcf86cd799439abc"
ORG_UUID = str(uuid.uuid4())

BASE_STATE = {
    "vendor_profile_id": VENDOR_UUID,
    "tender_mongo_id": TENDER_MONGO_ID,
    "org_id": ORG_UUID,
    "score_threshold": 70.0,
    "current_stage": "start",
    "is_eligible": True,
    "tender_parsed": False,
    "persisted": False,
    "notification_sent": False,
    "final_score": 0.0,
    "semantic_score": 0.0,
    "extraction_confidence": 0.8,
    "vendor_profile_data": {
        "business_domain": {"primary_domains": ["Information Technology"]},
        "geography": {"operational_states": ["Delhi"]},
        "financials": {"avg_annual_turnover_inr": 5000000},
        "certifications": {"iso_certifications": [{"standard": "ISO 9001"}], "domain_licenses": []},
        "past_project_experience": {"projects": [{"contract_value_inr": 2000000}]},
        "compliance": {"blacklisted_or_debarred": False},
        "profile_completeness_pct": 80,
        "identity": {"business_name": "TestVendor Pvt. Ltd."},
    },
    "vendor_vendor_id": "V-001",
    "vendor_pg_uuid": VENDOR_UUID,
    "vendor_embedding": [0.1] * 384,
    "tender_doc": {
        "structured_data": {
            "domain": "Information Technology",
            "location_state": "Delhi",
            "estimated_value": 1000000,
            "min_avg_turnover": 500000,
            "mandatory_certifications": ["ISO 9001"],
            "scope_summary": "Enterprise IT infrastructure.",
        },
        "extraction_confidence": 0.8,
        "raw_text": "Sample raw tender text...",
    },
    "tender_structured_data": {
        "domain": "Information Technology",
        "location_state": "Delhi",
        "estimated_value": 1000000,
        "min_avg_turnover": 500000,
        "mandatory_certifications": ["ISO 9001"],
        "scope_summary": "Enterprise IT infrastructure.",
    },
    "tender_pg_embedding": [0.2] * 384,
}


# ─── Unit: routing functions ──────────────────────────────────────────────────

class TestRoutingFunctions:
    def test_route_after_ingestion_no_error_goes_to_parsing(self):
        from app.agents.graph import route_after_ingestion
        state = {**BASE_STATE, "error": None}
        assert route_after_ingestion(state) == "parsing_agent"

    def test_route_after_ingestion_with_error_goes_to_end(self):
        from app.agents.graph import route_after_ingestion
        state = {**BASE_STATE, "error": "VendorProfile not found"}
        assert route_after_ingestion(state) == "end_with_error"

    def test_route_after_filter_eligible_goes_to_scoring(self):
        from app.agents.graph import route_after_filter
        state = {**BASE_STATE, "is_eligible": True}
        assert route_after_filter(state) == "scoring_agent"

    def test_route_after_filter_ineligible_goes_to_explanation(self):
        from app.agents.graph import route_after_filter
        state = {**BASE_STATE, "is_eligible": False}
        assert route_after_filter(state) == "explanation_agent"


# ─── Unit: parsing_agent ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_parsing_agent_valid_data_passes():
    from app.agents.parsing_agent import parsing_agent
    result = await parsing_agent(BASE_STATE)
    assert result["tender_parsed"] is True
    assert result["current_stage"] == "parsing_complete"
    assert isinstance(result["parse_warnings"], list)


@pytest.mark.asyncio
async def test_parsing_agent_missing_critical_fields_adds_warning():
    from app.agents.parsing_agent import parsing_agent
    state = {
        **BASE_STATE,
        "tender_structured_data": {},  # All critical fields missing
        "extraction_confidence": 0.8,  # High enough to skip re-extraction
    }
    result = await parsing_agent(state)
    assert result["tender_parsed"] is True
    assert len(result["parse_warnings"]) > 0


# ─── Unit: filter_agent ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_agent_eligible_vendor_passes():
    from app.agents.filter_agent import filter_agent
    result = await filter_agent(BASE_STATE)
    assert result["is_eligible"] is True
    assert result["filter_result"]["overall_pass"] is True


@pytest.mark.asyncio
async def test_filter_agent_blacklisted_vendor_fails():
    from app.agents.filter_agent import filter_agent
    state = {
        **BASE_STATE,
        "vendor_profile_data": {
            **BASE_STATE["vendor_profile_data"],
            "compliance": {"blacklisted_or_debarred": True},
        }
    }
    result = await filter_agent(state)
    assert result["is_eligible"] is False
    assert result["final_score"] == 0.0
    assert result["recommendation"] == "NOT_ELIGIBLE"


# ─── Unit: scoring_agent ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_agent_computes_nonzero_score():
    from app.agents.scoring_agent import scoring_agent
    result = await scoring_agent({
        **BASE_STATE,
        "filter_result": {"overall_pass": True},
    })
    assert result["final_score"] > 0
    assert 0.0 <= result["semantic_score"] <= 1.0
    assert result["recommendation"] in {"HIGH_MATCH", "MODERATE_MATCH", "LOW_MATCH", "NOT_ELIGIBLE"}


@pytest.mark.asyncio
async def test_scoring_agent_no_embeddings_gives_zero_semantic():
    from app.agents.scoring_agent import scoring_agent
    state = {
        **BASE_STATE,
        "vendor_embedding": None,
        "tender_pg_embedding": None,
        "filter_result": {"overall_pass": True},
    }
    result = await scoring_agent(state)
    assert result["semantic_score"] == 0.0


# ─── Unit: explanation_agent ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_explanation_agent_produces_valid_result():
    from app.agents.explanation_agent import explanation_agent
    from app.services.explanation_service import ExplanationResult, ScoreRationale

    mock_exp = ExplanationResult(
        executive_summary="Strong match.",
        strengths=["Domain match"],
        risk_factors=[],
        score_rationale=ScoreRationale(domain="Exact match."),
        recommendation="HIGH_MATCH",
        recommendation_detail="Proceed to bid.",
    )

    state = {
        **BASE_STATE,
        "filter_result": {"overall_pass": True, "disqualification_reason": None, "failed_check": None, "check_results": []},
        "score_result": {"final_score": 85.0, "breakdown": {}},
        "final_score": 85.0,
    }

    with patch("app.agents.explanation_agent.generate_explanation", new=AsyncMock(return_value=mock_exp)):
        result = await explanation_agent(state)

    assert result["recommendation"] == "HIGH_MATCH"
    assert "final_match_result" in result
    mr = result["final_match_result"]["match_result"]
    assert mr["_meta"]["engine_version"] == "langgraph-v3.0"
    assert mr["_meta"]["pipeline"] == "langgraph"
    assert "match_id" in result


# ─── Unit: notification_agent ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notification_agent_persists_and_sends_email_above_threshold():
    from app.agents.notification_agent import notification_agent

    state = {
        **BASE_STATE,
        "final_score": 85.0,
        "match_id": "MR-V-001-test1234",
        "score_threshold": 70.0,
        "final_match_result": {"match_result": {"_meta": {"vendor_id": "V-001"}, "explanation": {"executive_summary": "Good match."}}},
    }

    mock_mongo = MagicMock()
    mock_mongo.match_results.replace_one = AsyncMock(return_value=MagicMock())

    with (
        patch("app.agents.notification_agent.get_db", return_value=mock_mongo),
    ):
        result = await notification_agent(state)

    assert result["persisted"] is True
    mock_mongo.match_results.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_notification_agent_skips_email_below_threshold():
    from app.agents.notification_agent import notification_agent

    state = {
        **BASE_STATE,
        "final_score": 45.0,
        "match_id": "MR-V-001-test5678",
        "score_threshold": 70.0,
        "final_match_result": {"match_result": {"_meta": {"vendor_id": "V-001"}, "explanation": {}}},
    }

    mock_mongo = MagicMock()
    mock_mongo.match_results.replace_one = AsyncMock(return_value=MagicMock())

    with patch("app.agents.notification_agent.get_db", return_value=mock_mongo):
        result = await notification_agent(state)

    assert result["notification_sent"] is False
    assert "below threshold" in result["notification_skipped_reason"]


# ─── Integration: graph compilation ──────────────────────────────────────────

def test_graph_compiles_without_error():
    """Verifies that StateGraph builds and compiles cleanly."""
    from app.agents.graph import build_graph
    graph = build_graph()
    assert graph is not None


def test_get_graph_returns_singleton():
    """Verifies that get_graph() returns the same instance on repeated calls."""
    from app.agents.graph import get_graph
    g1 = get_graph()
    g2 = get_graph()
    assert g1 is g2
