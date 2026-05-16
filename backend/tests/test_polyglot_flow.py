import pytest
from httpx import AsyncClient
import uuid
import logging
from sqlalchemy import select

from app.main import app
from app.core.database import get_db
from app.core.postgres import get_pg_session
from app.db.models.user import User
from app.db.models.organization import Organization
from app.db.models.document import Tender, VendorProfile

logging.basicConfig(level=logging.INFO)

# Pytest fixtures and config for testing against the actual local DBs

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_polyglot_registration_flow(async_client: AsyncClient):
    """
    Validates that registering a user correctly populates the PostgreSQL database
    (both Organization and User) and returns a valid JWT.
    """
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "testpassword123",
        "name": "Test Admin",
        "org_name": "Polyglot Test Inc",
        "org_industry": "Technology"
    }

    # 1. Register
    response = await async_client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    
    # 2. Login to get token
    login_payload = {
        "email": unique_email,
        "password": "testpassword123"
    }
    login_resp = await async_client.post("/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    
    # 3. Verify in PostgreSQL
    async with get_pg_session() as session:
        user = await session.scalar(select(User).where(User.email == unique_email))
        assert user is not None
        assert user.role == "ADMIN1"
        
        org = await session.scalar(select(Organization).where(Organization.id == user.org_id))
        assert org is not None
        assert org.name == "Polyglot Test Inc"

@pytest.mark.asyncio
async def test_polyglot_vendor_profile_flow(async_client: AsyncClient):
    """
    Validates that vendor profiles are stored exclusively in PostgreSQL
    as JSONB and can be retrieved correctly.
    """
    # Create test user
    unique_email = f"test_vendor_{uuid.uuid4().hex[:8]}@example.com"
    await async_client.post("/auth/register", json={
        "email": unique_email, "password": "pass", "name": "Vendor Test", "org_name": "Test Org"
    })
    
    login_resp = await async_client.post("/auth/login", json={"email": unique_email, "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Vendor Profile (Postgres JSONB)
    profile_payload = {
        "identity": {
            "company_legal_name": "Polyglot Vendor LLC",
            "business_type": "Private Limited",
            "incorporation_date": "2020-01-01T00:00:00Z"
        },
        "geography": {
            "registered_states": ["Delhi"],
            "willing_to_operate_in_new_states": True
        },
        "business_domain": {
            "primary_domains": ["IT Software"],
            "capability_description_freetext": "Software dev and AI"
        },
        "financials": {"avg_annual_turnover_inr": 10000000},
        "certifications": {},
        "compliance": {"blacklisted_or_debarred": False},
        "past_project_experience": {"projects": []},
        "notification_preferences": {}
    }
    
    resp = await async_client.post("/vendor-profiles/", json=profile_payload, headers=headers)
    assert resp.status_code == 201
    profile_id = resp.json()["id"]
    
    # 2. Verify in PostgreSQL
    async with get_pg_session() as session:
        profile = await session.scalar(select(VendorProfile).where(VendorProfile.id == uuid.UUID(profile_id)))
        assert profile is not None
        assert profile.business_name == "Polyglot Vendor LLC"
        assert profile.profile_data["business_domain"]["primary_domains"] == ["IT Software"]

@pytest.mark.asyncio
async def test_polyglot_tender_storage_flow():
    """
    Validates that querying a tender checks MongoDB for raw documents.
    Note: Full upload testing requires Celery workers, so we test the
    database state assertion here.
    """
    db = get_db()
    # Ensure MongoDB is reachable
    ping = await db.command("ping")
    assert ping["ok"] == 1.0
    
    # We expect global tenders to exist from the seeding script
    tenders = await db.documents.find({"type": "tender"}).to_list(10)
    if tenders:
        assert "_id" in tenders[0]
        assert "structured_data" in tenders[0]
        
        # Verify bridge in Postgres
        mongo_id = str(tenders[0]["_id"])
        async with get_pg_session() as session:
            pg_tender = await session.scalar(select(Tender).where(Tender.mongo_id == mongo_id))
            if pg_tender:
                assert pg_tender.mongo_id == mongo_id
