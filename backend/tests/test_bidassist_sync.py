"""
test_bidassist_sync.py
----------------------
Integration tests for Phase 5: Bidassist Auto-Ingestion & Scheduled Scraping.

Covers:
  - BidassistService normalization and deduplication
  - ScrapingService portal config loading and deduplication
  - Scheduled task idempotency
  - Admin API tenancy enforcement
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_mongo_db():
    """Creates a mock MongoDB database with async methods."""
    db = MagicMock()
    db.documents.find_one = AsyncMock(return_value=None)
    db.documents.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id_001"))
    db.documents.update_one = AsyncMock()
    db.documents.count_documents = AsyncMock(return_value=42)
    db.sync_logs.find_one = AsyncMock(return_value=None)
    db.sync_logs.insert_one = MagicMock()  # Sync in Celery context

    # For async iteration on sync_logs.find()
    async def _async_log_iter():
        for item in []:
            yield item

    mock_cursor = MagicMock()
    mock_cursor.sort = MagicMock(return_value=mock_cursor)
    mock_cursor.limit = MagicMock(return_value=mock_cursor)
    mock_cursor.__aiter__ = lambda self: _async_log_iter().__aiter__()
    db.sync_logs.find = MagicMock(return_value=mock_cursor)

    return db


@pytest.fixture
def mock_super_admin_user():
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000099"
    user.org_id = "00000000-0000-0000-0000-000000000001"
    user.email = "super@tendermatch.com"
    user.role = "SUPER"
    user.is_active = True
    return user


@pytest.fixture
def mock_regular_user():
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000050"
    user.org_id = "00000000-0000-0000-0000-000000000002"
    user.email = "user@acme.com"
    user.role = "USER"
    user.is_active = True
    return user


@pytest.fixture
def override_super_admin(mock_super_admin_user):
    from app.main import app
    from app.core.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_super_admin_user
    yield
    app.dependency_overrides = {}


@pytest.fixture
def override_regular_user(mock_regular_user):
    from app.main import app
    from app.core.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_regular_user
    yield
    app.dependency_overrides = {}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BIDASSIST SERVICE — NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBidassistNormalization:
    """Tests that the BidassistService correctly normalizes API responses."""

    @pytest.mark.asyncio
    async def test_normalize_tender_with_pdf(self, mock_mongo_db):
        """Tender with a pdf_url should be queued via ingest_tender_document."""
        from app.services.bidassist_service import BidassistService

        service = BidassistService()

        with (
            patch("app.services.bidassist_service.db", mock_mongo_db),
            patch("app.services.bidassist_service.ingest_tender_document") as mock_ingest,
            patch.object(service, "_download_pdf", new_callable=AsyncMock, return_value="/tmp/BA-1001.pdf"),
            patch.object(service, "fetch_tenders", new_callable=AsyncMock, return_value=[
                {
                    "tender_id": "BA-1001",
                    "title": "IT Equipment Supply",
                    "domain": "IT",
                    "scope_summary": "Supply of laptops",
                    "estimated_value": 25000000,
                    "location_state": "Maharashtra",
                    "min_avg_turnover": 50000000,
                    "mandatory_certifications": ["ISO 9001"],
                    "deadline": "2026-12-31T00:00:00Z",
                    "extraction_confidence": 1.0,
                    "pdf_url": "https://example.com/tender.pdf"
                }
            ]),
        ):
            stats = await service.sync_tenders()

        assert stats["new_tenders"] == 1
        assert stats["duplicates_skipped"] == 0
        assert stats["errors"] == 0
        assert "BA-1001" in stats["tender_ids"]
        mock_ingest.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalize_tender_without_pdf(self, mock_mongo_db):
        """Tender without a pdf_url should be persisted directly (no LLM extraction)."""
        from app.services.bidassist_service import BidassistService

        service = BidassistService()

        mock_pg_session = AsyncMock()
        mock_pg_session.__aenter__ = AsyncMock(return_value=mock_pg_session)
        mock_pg_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_pg_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.bidassist_service.db", mock_mongo_db),
            patch("app.services.bidassist_service._save_tender_vector", new_callable=AsyncMock),
            patch("app.services.bidassist_service.get_embedding_service") as mock_emb,
            patch("app.services.bidassist_service.get_pg_session", return_value=mock_pg_session),
            patch("app.tasks.matching_tasks.run_bulk_match_task") as mock_match,
            patch.object(service, "fetch_tenders", new_callable=AsyncMock, return_value=[
                {
                    "tender_id": "BA-NO-PDF",
                    "title": "Road Work",
                    "domain": "Construction",
                    "scope_summary": "10km road",
                    "estimated_value": 150000000,
                    "location_state": "Karnataka",
                    "min_avg_turnover": 300000000,
                    "mandatory_certifications": [],
                    "deadline": "2026-11-15T00:00:00Z",
                    "extraction_confidence": 1.0,
                    "pdf_url": None
                }
            ]),
        ):
            mock_emb_instance = MagicMock()
            mock_emb_instance.encode_text_sync = MagicMock(return_value=[0.1] * 384)
            mock_emb.return_value = mock_emb_instance

            stats = await service.sync_tenders()

        assert stats["new_tenders"] == 1
        assert "BA-NO-PDF" in stats["tender_ids"]
        mock_mongo_db.documents.insert_one.assert_called()
        mock_match.delay.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DEDUPLICATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeduplication:
    """Tests that duplicate tenders are correctly detected and skipped."""

    @pytest.mark.asyncio
    async def test_duplicate_by_tender_id_skipped(self, mock_mongo_db):
        """A tender already in Mongo (by reference_no) should be skipped."""
        from app.services.bidassist_service import BidassistService

        # Simulate existing document found
        mock_mongo_db.documents.find_one = AsyncMock(return_value={"_id": "existing_doc"})

        service = BidassistService()

        with (
            patch("app.services.bidassist_service.db", mock_mongo_db),
            patch.object(service, "fetch_tenders", new_callable=AsyncMock, return_value=[
                {
                    "tender_id": "BA-DUPE",
                    "title": "Duplicate Tender",
                    "domain": "IT",
                    "scope_summary": "Already exists",
                    "estimated_value": 1000,
                    "location_state": "Delhi",
                    "min_avg_turnover": 5000,
                    "mandatory_certifications": [],
                    "deadline": "2026-12-01T00:00:00Z",
                    "extraction_confidence": 1.0,
                    "pdf_url": None
                }
            ]),
        ):
            stats = await service.sync_tenders()

        assert stats["new_tenders"] == 0
        assert stats["duplicates_skipped"] == 1
        mock_mongo_db.documents.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent_double_run(self, mock_mongo_db):
        """Running sync twice should not produce duplicates on the second run."""
        from app.services.bidassist_service import BidassistService

        service = BidassistService()
        call_count = 0

        async def _find_one_side_effect(query):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return None  # First run: not found
            return {"_id": "now_exists"}  # Second run: found

        mock_mongo_db.documents.find_one = AsyncMock(side_effect=_find_one_side_effect)

        tender_data = [{
            "tender_id": "BA-IDEM",
            "title": "Idempotency Test",
            "domain": "IT",
            "scope_summary": "Test",
            "estimated_value": 1000,
            "location_state": "Delhi",
            "min_avg_turnover": 5000,
            "mandatory_certifications": [],
            "deadline": "2026-12-01T00:00:00Z",
            "extraction_confidence": 1.0,
            "pdf_url": None
        }]

        mock_pg_session = AsyncMock()
        mock_pg_session.__aenter__ = AsyncMock(return_value=mock_pg_session)
        mock_pg_session.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_pg_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("app.services.bidassist_service.db", mock_mongo_db),
            patch("app.services.bidassist_service._save_tender_vector", new_callable=AsyncMock),
            patch("app.services.bidassist_service.get_embedding_service") as mock_emb,
            patch("app.services.bidassist_service.get_pg_session", return_value=mock_pg_session),
            patch("app.tasks.matching_tasks.run_bulk_match_task"),
            patch.object(service, "fetch_tenders", new_callable=AsyncMock, return_value=tender_data),
        ):
            mock_emb_instance = MagicMock()
            mock_emb_instance.encode_text_sync = MagicMock(return_value=[0.1] * 384)
            mock_emb.return_value = mock_emb_instance

            # First run
            stats1 = await service.sync_tenders()

        with (
            patch("app.services.bidassist_service.db", mock_mongo_db),
            patch.object(service, "fetch_tenders", new_callable=AsyncMock, return_value=tender_data),
        ):
            # Second run — should be a duplicate
            stats2 = await service.sync_tenders()

        assert stats1["new_tenders"] == 1
        assert stats2["new_tenders"] == 0
        assert stats2["duplicates_skipped"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SCRAPING SERVICE — CONFIG LOADING & DEDUP
# ═══════════════════════════════════════════════════════════════════════════════

class TestScrapingService:

    def test_load_portal_configs(self):
        """Portal configs should be loaded and only enabled portals returned."""
        from app.services.scraping_service import ScrapingService

        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value={
                "portals": [
                    {"name": "portal_a", "enabled": True, "scrape_url": "https://a.com", "rate_limit_seconds": 2},
                    {"name": "portal_b", "enabled": False, "scrape_url": "https://b.com", "rate_limit_seconds": 2},
                    {"name": "portal_c", "enabled": True, "scrape_url": "https://c.com", "rate_limit_seconds": 2},
                ]
            }):
                service = ScrapingService()

        assert len(service.portals) == 2
        assert service.portals[0]["name"] == "portal_a"
        assert service.portals[1]["name"] == "portal_c"

    @pytest.mark.asyncio
    async def test_scraper_dedup_skips_existing(self, mock_mongo_db):
        """Scraper should skip tenders that already exist in MongoDB."""
        from app.services.scraping_service import ScrapingService

        mock_mongo_db.documents.find_one = AsyncMock(return_value={"_id": "exists"})

        with (
            patch("builtins.open", MagicMock()),
            patch("json.load", return_value={"portals": []}),
        ):
            service = ScrapingService()

        config = {
            "name": "test_portal",
            "scrape_url": "https://test.com",
            "requires_login": False,
            "rate_limit_seconds": 0,
            "tender_link_selector": "a"
        }

        # Inject a fake tender extraction result
        with (
            patch("app.services.scraping_service.db", mock_mongo_db),
            patch.object(service, "_scrape_with_firecrawl", new_callable=AsyncMock, return_value="<html></html>"),
            patch.object(service, "_extract_tenders_from_html", return_value=[
                {"title": "Existing", "reference_no": "REF-001", "deadline": "2026-12-01", "pdf_url": None}
            ]),
        ):
            stats = await service.scrape_portal(config)

        assert stats["duplicates_skipped"] == 1
        assert stats["new_tenders"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SCHEDULED TASK IDEMPOTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestScheduledTaskIdempotency:

    def test_nightly_bidassist_sync_logs_to_mongo(self):
        """The nightly task should always write a sync_log entry, even on success."""
        from app.tasks.scheduled_tasks import nightly_bidassist_sync

        mock_sync_db = MagicMock()
        mock_sync_db.sync_logs.insert_one = MagicMock()

        mock_service_instance = MagicMock()

        async def _mock_sync(*a, **kw):
            return {"new_tenders": 2, "duplicates_skipped": 1, "errors": 0, "tender_ids": ["A", "B"]}

        mock_service_instance.sync_tenders = _mock_sync

        with (
            patch("app.tasks.scheduled_tasks.get_celery_db", return_value=mock_sync_db),
            patch("app.tasks.scheduled_tasks.BidassistService", return_value=mock_service_instance),
            patch("app.tasks.scheduled_tasks._send_super_admin_notification", new_callable=AsyncMock),
        ):
            result = nightly_bidassist_sync()

        assert "success" in result
        mock_sync_db.sync_logs.insert_one.assert_called_once()
        log_entry = mock_sync_db.sync_logs.insert_one.call_args[0][0]
        assert log_entry["sync_type"] == "bidassist"
        assert log_entry["new_tenders"] == 2
        assert log_entry["status"] == "success"

    def test_nightly_bidassist_sync_logs_failure(self):
        """On failure, the task should still write a log entry with status=failed."""
        from app.tasks.scheduled_tasks import nightly_bidassist_sync

        mock_sync_db = MagicMock()
        mock_sync_db.sync_logs.insert_one = MagicMock()

        mock_service_instance = MagicMock()

        async def _mock_sync_fail(*a, **kw):
            raise ConnectionError("Bidassist API unreachable")

        mock_service_instance.sync_tenders = _mock_sync_fail

        with (
            patch("app.tasks.scheduled_tasks.get_celery_db", return_value=mock_sync_db),
            patch("app.tasks.scheduled_tasks.BidassistService", return_value=mock_service_instance),
            patch("app.tasks.scheduled_tasks._send_super_admin_notification", new_callable=AsyncMock),
        ):
            result = nightly_bidassist_sync()

        assert "failed" in result
        mock_sync_db.sync_logs.insert_one.assert_called_once()
        log_entry = mock_sync_db.sync_logs.insert_one.call_args[0][0]
        assert log_entry["status"] == "failed"
        assert "Bidassist API unreachable" in log_entry["error_detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ADMIN API — TENANCY ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAPITenancy:

    @pytest.mark.asyncio
    async def test_trigger_sync_as_super_admin(self, override_super_admin):
        """SUPER_ADMIN should be able to trigger a manual sync."""
        from app.main import app

        with patch("app.api.admin.nightly_bidassist_sync") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "celery-task-xyz"
            mock_task.delay.return_value = mock_result

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/admin/sync/trigger")

        assert response.status_code == 202
        assert response.json()["task_id"] == "celery-task-xyz"
        assert response.json()["status"] == "queued"
        mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_sync_as_regular_user_forbidden(self, override_regular_user):
        """A regular USER should receive 403 Forbidden."""
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/admin/sync/trigger")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_sync_logs_as_super_admin(self, override_super_admin, mock_mongo_db):
        """SUPER_ADMIN should be able to retrieve sync logs."""
        from app.main import app

        with patch("app.api.admin.get_db", return_value=mock_mongo_db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/admin/sync/logs")

        assert response.status_code == 200
        assert "logs" in response.json()

    @pytest.mark.asyncio
    async def test_get_sync_logs_as_regular_user_forbidden(self, override_regular_user):
        """A regular USER should receive 403 Forbidden on sync logs."""
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/admin/sync/logs")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_sync_status_as_super_admin(self, override_super_admin, mock_mongo_db):
        """SUPER_ADMIN should be able to see sync status."""
        from app.main import app

        with patch("app.api.admin.get_db", return_value=mock_mongo_db):
            with patch("app.api.admin.BidassistService"):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.get("/admin/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert "total_tenders_in_db" in data
        assert "bidassist_connected" in data
        assert data["total_tenders_in_db"] == 42

    @pytest.mark.asyncio
    async def test_get_sync_status_as_regular_user_forbidden(self, override_regular_user):
        """A regular USER should receive 403 Forbidden on sync status."""
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/admin/sync/status")

        assert response.status_code == 403
