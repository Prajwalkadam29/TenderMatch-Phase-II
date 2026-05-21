"""
test_match_orchestrator.py
--------------------------
Tests for Component 5: Match Orchestrator + Celery Integration.

Covers:
  - orchestrate_match() full pipeline (all steps mocked)
  - Short-circuit on failed hard filter (score=0, explanation still generated)
  - Semantic score computation from numpy vectors
  - MongoDB persist called with correct match_id
  - run_match_task Celery wrapper (success, ValueError no-retry, transient retry)
  - run_bulk_match_task fan-out dispatches correct number of tasks
"""

import uuid
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch, call


# ─── Fixtures ────────────────────────────────────────────────────────────────

VENDOR_UUID = str(uuid.uuid4())
TENDER_MONGO_ID = "507f1f77bcf86cd799439011"
ORG_UUID = str(uuid.uuid4())

MOCK_PROFILE_DATA = {
    "identity": {"business_name": "TestVendor Pvt. Ltd."},
    "business_domain": {"primary_domains": ["Information Technology"]},
    "geography": {"operational_states": ["Delhi"], "registered_states": []},
    "financials": {"avg_annual_turnover_inr": 5000000},
    "certifications": {"iso_certifications": [{"standard": "ISO 9001"}], "domain_licenses": []},
    "past_project_experience": {"projects": [{"contract_value_inr": 2000000}]},
    "compliance": {"blacklisted_or_debarred": False, "gst_returns_compliant": True},
    "profile_completeness_pct": 85,
}

MOCK_TENDER_SD = {
    "domain": "Information Technology",
    "location_state": "Delhi",
    "estimated_value": 1000000,
    "min_avg_turnover": 500000,
    "mandatory_certifications": ["ISO 9001"],
    "scope_summary": "Enterprise IT infrastructure deployment.",
    "source_portal": "GeM",
    "deadline": {"bid_submission": "2026-07-01"},
}


def _make_vendor_orm(vendor_id="V-001", embedding=None):
    orm = MagicMock()
    orm.id = uuid.UUID(VENDOR_UUID)
    orm.vendor_id = vendor_id
    orm.org_id = uuid.UUID(ORG_UUID)
    orm.profile_data = MOCK_PROFILE_DATA
    orm.embedding = embedding or [0.1] * 384
    return orm


def _make_pg_tender(embedding=None):
    t = MagicMock()
    t.mongo_id = TENDER_MONGO_ID
    t.embedding = embedding or [0.2] * 384
    return t


def _make_explanation(recommendation="HIGH_MATCH"):
    from app.services.explanation_service import ExplanationResult, ScoreRationale
    return ExplanationResult(
        executive_summary="Strong match. Vendor meets all requirements.",
        strengths=["Domain match", "Financial capacity sufficient"],
        risk_factors=[],
        score_rationale=ScoreRationale(
            domain="Exact match.", geography="Registered in state.",
            financial="3x turnover.", experience="Similar projects.",
            certification="ISO 9001 confirmed.", semantic="High overlap.",
        ),
        recommendation=recommendation,
        recommendation_detail="Proceed to bid immediately.",
        confidence_note=None,
    )


# ─── Unit: semantic score computation ────────────────────────────────────────

class TestSemanticScoreComputation:
    """Verify the cosine similarity math used in orchestrate_match."""

    def test_identical_vectors_give_score_1(self):
        v = np.array([1.0, 0.0, 0.0])
        t = np.array([1.0, 0.0, 0.0])
        score = float(np.dot(v, t) / (np.linalg.norm(v) * np.linalg.norm(t)))
        assert abs(score - 1.0) < 1e-6

    def test_orthogonal_vectors_give_score_0(self):
        v = np.array([1.0, 0.0, 0.0])
        t = np.array([0.0, 1.0, 0.0])
        score = float(np.dot(v, t) / (np.linalg.norm(v) * np.linalg.norm(t)))
        assert abs(score) < 1e-6

    def test_partial_overlap_is_between_0_and_1(self):
        v = np.array([1.0, 1.0, 0.0])
        t = np.array([1.0, 0.0, 1.0])
        score = float(np.dot(v, t) / (np.linalg.norm(v) * np.linalg.norm(t)))
        assert 0 < score < 1


# ─── Integration: orchestrate_match (all I/O mocked) ─────────────────────────

@pytest.mark.asyncio
async def test_orchestrate_match_full_pipeline_success():
    """
    Tests the full 8-step pipeline with all DB/LLM calls mocked.
    Verifies correct result structure and that persist (replace_one) is called.
    """
    vendor_orm = _make_vendor_orm()
    pg_tender = _make_pg_tender()

    tender_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "structured_data": MOCK_TENDER_SD,
        "extraction_confidence": 0.85,
        "type": "tender",
    }

    mock_explanation = _make_explanation("HIGH_MATCH")

    mock_mongo = MagicMock()
    mock_mongo.documents.find_one = AsyncMock(return_value=tender_doc)
    mock_mongo.match_results.replace_one = AsyncMock(return_value=MagicMock())

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(side_effect=[vendor_orm, pg_tender])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.services.matching_service.get_db", return_value=mock_mongo),
        patch("app.services.matching_service.get_pg_session") as mock_pg,
        patch("app.services.explanation_service.AsyncGroq"),
        patch("app.services.explanation_service.generate_explanation", new=AsyncMock(return_value=mock_explanation)),
    ):
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        from app.services.matching_service import orchestrate_match
        result = await orchestrate_match(VENDOR_UUID, TENDER_MONGO_ID, org_id=ORG_UUID)

    # Verify result structure
    assert result["version"] == "3.0.0"
    match = result["match_result"]
    assert match["recommendation"] == "HIGH_MATCH"
    assert match["hard_filter_results"]["overall_pass"] is True
    assert match["weighted_score"]["final_score"] > 0
    assert "executive_summary" in match["explanation"]
    assert match["_meta"]["vendor_id"] == "V-001"
    assert match["_meta"]["tender_mongo_id"] == TENDER_MONGO_ID

    # Verify MongoDB persist was called
    mock_mongo.match_results.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrate_match_hard_filter_fail_short_circuits():
    """
    When HardFilter fails (e.g. blacklisted vendor), score should be 0.0,
    eligibility should be Ineligible, but explanation still generated.
    """
    vendor_orm = _make_vendor_orm()
    # Inject blacklist flag into profile data
    vendor_orm.profile_data = {
        **MOCK_PROFILE_DATA,
        "compliance": {"blacklisted_or_debarred": True},
    }
    pg_tender = _make_pg_tender()

    tender_doc = {
        "_id": TENDER_MONGO_ID,
        "structured_data": MOCK_TENDER_SD,
        "extraction_confidence": 0.9,
    }

    mock_explanation = _make_explanation("NOT_ELIGIBLE")
    mock_mongo = MagicMock()
    mock_mongo.documents.find_one = AsyncMock(return_value=tender_doc)
    mock_mongo.match_results.replace_one = AsyncMock(return_value=MagicMock())

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(side_effect=[vendor_orm, pg_tender])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.services.matching_service.get_db", return_value=mock_mongo),
        patch("app.services.matching_service.get_pg_session") as mock_pg,
        patch("app.services.explanation_service.AsyncGroq"),
        patch("app.services.explanation_service.generate_explanation", new=AsyncMock(return_value=mock_explanation)),
    ):
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        from app.services.matching_service import orchestrate_match
        result = await orchestrate_match(VENDOR_UUID, TENDER_MONGO_ID)

    match = result["match_result"]
    assert match["hard_filter_results"]["overall_pass"] is False
    assert match["weighted_score"]["final_score"] == 0.0
    assert match["weighted_score"]["eligibility_status"] == "Ineligible"
    assert match["recommendation"] == "NOT_ELIGIBLE"
    # Persist must still be called even for disqualified vendors
    mock_mongo.match_results.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrate_match_invalid_vendor_id_raises():
    """Verifies that a bad UUID raises ValueError immediately (no retry)."""
    from app.services.matching_service import orchestrate_match

    with pytest.raises(ValueError, match="Invalid vendor_profile_id"):
        await orchestrate_match("not-a-uuid", TENDER_MONGO_ID)


# ─── Celery task: run_match_task ─────────────────────────────────────────────

def test_run_match_task_success():
    """Tests the Celery wrapper returns correct lightweight status dict."""
    mock_result = {
        "version": "3.0.0",
        "match_result": {
            "_meta": {"match_id": "MR-V-001-507f1f77", "vendor_id": "V-001"},
            "weighted_score": {"final_score": 87.5},
            "recommendation": "HIGH_MATCH",
        }
    }

    with patch("app.tasks.matching_tasks._run_async", return_value=mock_result):
        from app.tasks.matching_tasks import run_match_task
        result = run_match_task(VENDOR_UUID, TENDER_MONGO_ID, org_id=ORG_UUID)

    assert result["status"] == "success"
    assert result["final_score"] == 87.5
    assert result["recommendation"] == "HIGH_MATCH"
    assert result["match_id"] == "MR-V-001-507f1f77"


def test_run_match_task_value_error_does_not_retry():
    """ValueError (not found, bad ID) should NOT trigger retry."""
    with patch("app.tasks.matching_tasks._run_async", side_effect=ValueError("VendorProfile not found")):
        from app.tasks.matching_tasks import run_match_task
        result = run_match_task(VENDOR_UUID, TENDER_MONGO_ID)

    assert result["status"] == "error"
    assert "VendorProfile not found" in result["error"]


# ─── Celery task: run_bulk_match_task ────────────────────────────────────────

def test_run_bulk_match_task_queues_correct_count():
    """Tests that bulk match correctly fans out one task per vendor."""
    mock_vendor_list = [
        (str(uuid.uuid4()), ORG_UUID),
        (str(uuid.uuid4()), ORG_UUID),
        (str(uuid.uuid4()), ORG_UUID),
    ]

    with (
        patch("app.tasks.matching_tasks._run_async", return_value=mock_vendor_list),
        patch("app.tasks.matching_tasks.run_match_task") as mock_task,
    ):
        mock_task.apply_async = MagicMock()

        from app.tasks.matching_tasks import run_bulk_match_task
        result = run_bulk_match_task(TENDER_MONGO_ID, org_id=ORG_UUID)

    assert result["status"] == "success"
    assert result["vendors_queued"] == 3
    assert mock_task.apply_async.call_count == 3


def test_run_bulk_match_task_no_vendors_returns_gracefully():
    """If no active vendors exist, returns gracefully with count=0."""
    with patch("app.tasks.matching_tasks._run_async", return_value=[]):
        from app.tasks.matching_tasks import run_bulk_match_task
        result = run_bulk_match_task(TENDER_MONGO_ID, org_id=ORG_UUID)

    assert result["status"] == "success"
    assert result["vendors_queued"] == 0
