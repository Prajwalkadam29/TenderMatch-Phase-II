import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.planner_service import PlannerService
from app.db.models.planner_models import PlannerInput

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock

@pytest.fixture
def planner(mock_redis):
    return PlannerService(mock_redis)

@pytest.mark.asyncio
async def test_planner_high_completeness(planner, mock_redis):
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        profile_completeness_pct=85.0
    )
    plan = await planner.get_or_create_plan(input_data)
    
    assert plan.retrieval_strategy == "vector_only"
    assert plan.explanation_depth == "full"
    assert mock_redis.setex.called

@pytest.mark.asyncio
async def test_planner_low_completeness(planner):
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        profile_completeness_pct=30.0
    )
    plan = await planner.get_or_create_plan(input_data)
    
    assert plan.retrieval_strategy == "bm25_fallback"
    assert plan.explanation_depth == "summary"

@pytest.mark.asyncio
async def test_planner_skip_reingestion(planner):
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        profile_completeness_pct=85.0,
        embeddings_exist=True
    )
    plan = await planner.get_or_create_plan(input_data)
    assert plan.skip_reingestion is True

@pytest.mark.asyncio
async def test_planner_redis_cache_hit(planner, mock_redis):
    cached_entry = {
        "plan": {
            "skip_reingestion": False,
            "retrieval_strategy": "hybrid",
            "require_ocr": False,
            "filter_strictness": "strict",
            "explanation_depth": "full",
            "invoke_critic": True,
            "rerank_results": False,
            "plan_reasoning": "cached"
        },
        "cached_at": "2023-01-01T00:00:00+00:00",
        "cache_hit_count": 0,
        "planner_used_llm": False
    }
    mock_redis.get.return_value = json.dumps(cached_entry)
    
    input_data = PlannerInput(tender_id="123", vendor_profile_id="456")
    plan = await planner.get_or_create_plan(input_data)
    
    assert plan.plan_reasoning == "cached"
    assert mock_redis.get.called

@pytest.mark.asyncio
async def test_planner_redis_cache_miss(planner, mock_redis):
    mock_redis.get.return_value = None
    input_data = PlannerInput(tender_id="123", vendor_profile_id="456", profile_completeness_pct=80.0)
    plan = await planner.get_or_create_plan(input_data)
    
    assert plan.retrieval_strategy == "vector_only"
    assert mock_redis.get.called
    assert mock_redis.setex.called

@pytest.mark.asyncio
async def test_planner_invoke_critic_rerun(planner):
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        is_rerun=True,
        prior_final_score=65.0
    )
    plan = await planner.get_or_create_plan(input_data)
    assert plan.invoke_critic is True
    assert plan.rerank_results is True

@pytest.mark.asyncio
async def test_planner_invoke_critic_rerun_high_score(planner):
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        is_rerun=True,
        prior_final_score=95.0
    )
    plan = await planner.get_or_create_plan(input_data)
    assert plan.invoke_critic is False
    assert plan.rerank_results is False

@pytest.mark.asyncio
@patch("app.services.planner_service.PlannerService._call_llm_planner")
async def test_planner_ambiguous_llm_fallback(mock_llm, planner):
    mock_llm.side_effect = Exception("API error")
    
    input_data = PlannerInput(
        tender_id="123",
        vendor_profile_id="456",
        profile_completeness_pct=50.0  # ambiguous zone
    )
    plan = await planner.get_or_create_plan(input_data)
    
    # Should fallback to safe default
    assert plan.retrieval_strategy == "hybrid"
    assert plan.invoke_critic is True
    assert plan.rerank_results is True
