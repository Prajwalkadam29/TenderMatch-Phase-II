import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_current_user():
    user = MagicMock()
    user.id = "user_123"
    user.org_id = "00000000-0000-0000-0000-000000000001"
    user.is_active = True
    return user

@pytest.fixture
def mock_get_current_user(mock_current_user):
    async def _mock_get_current_user():
        return mock_current_user
    return _mock_get_current_user

@pytest.fixture
def override_deps(mock_get_current_user):
    from app.main import app
    from app.core.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides = {}

# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_match_run(override_deps):
    from app.main import app
    
    with patch("app.tasks.matching_tasks.run_match_task.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "task_123"
        mock_delay.return_value = mock_task
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/match/run",
                json={
                    "vendor_profile_id": "v-123",
                    "tender_mongo_id": "t-123",
                    "use_langgraph": True
                }
            )
            
        assert response.status_code == 202
        assert response.json() == {"task_id": "task_123", "status": "queued"}
        mock_delay.assert_called_once_with(
            vendor_profile_id="v-123",
            tender_mongo_id="t-123",
            org_id="00000000-0000-0000-0000-000000000001",
            use_langgraph=True
        )

@pytest.mark.asyncio
async def test_get_match_status(override_deps):
    from app.main import app
    
    with patch("celery.result.AsyncResult") as mock_result:
        mock_instance = MagicMock()
        mock_instance.state = "SUCCESS"
        mock_instance.result = {"match_result": {"score": 90}}
        mock_result.return_value = mock_instance
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/match/status/task_123")
            
        assert response.status_code == 200
        assert response.json()["status"] == "SUCCESS"
        assert response.json()["result"] == {"match_result": {"score": 90}}

@pytest.mark.asyncio
async def test_post_match_feedback_success(override_deps):
    from app.main import app
    
    mock_db = MagicMock()
    mock_db.match_results.find_one = AsyncMock(return_value={
        "_id": "dummy_id",
        "match_result": {
            "_meta": {
                "match_id": "M-123",
                "vendor_profile_id": "00000000-0000-0000-0000-000000000001"
            }
        }
    })
    mock_db.match_results.update_one = AsyncMock()
    
    mock_session = AsyncMock()
    mock_vp = MagicMock()
    mock_vp.org_id = "00000000-0000-0000-0000-000000000001"
    mock_session.scalar = AsyncMock(return_value=mock_vp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with (
        patch("app.api.match.get_db", return_value=mock_db),
        patch("app.core.postgres.get_pg_session", return_value=mock_session)
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/match/feedback",
                json={
                    "match_id": "M-123",
                    "signal": "interested"
                }
            )
            
        assert response.status_code == 200
        assert response.json() == {"acknowledged": True}
        mock_db.match_results.update_one.assert_called_once()
