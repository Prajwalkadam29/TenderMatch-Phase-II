import pytest
import uuid
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.db.models.vendor_extraction_models import VendorExtractionResult
from app.services.vendor_extraction_service import VendorExtractionService

# ─── EXTRACTION SERVICE TESTS ──────────────────────────────────────────────────

@pytest.fixture
def mock_groq():
    with patch("app.services.vendor_extraction_service.AsyncGroq") as mock:
        yield mock

@pytest.mark.asyncio
async def test_single_chunk_valid_extraction(mock_groq):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"company_legal_name": "Test Pvt Ltd", "extraction_confidence": 0.9}'))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_groq.return_value = mock_client
    
    svc = VendorExtractionService()
    res = await svc.extract_from_chunk("test chunk", 0)
    
    assert res.company_legal_name == "Test Pvt Ltd"
    assert res.extraction_confidence == 0.9

@pytest.mark.asyncio
async def test_financial_normalization(mock_groq):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"average_annual_turnover_inr": 50000000.0, "net_worth_inr": 4500000.0}'))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_groq.return_value = mock_client
    
    svc = VendorExtractionService()
    res = await svc.extract_from_chunk("turnover 5 crore, net worth 45 lakhs", 0)
    
    assert res.average_annual_turnover_inr == 50000000.0
    assert res.net_worth_inr == 4500000.0

@pytest.mark.asyncio
async def test_malformed_json_triggers_retry_and_empty(mock_groq):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"company_legal_name": "Broken String'))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_groq.return_value = mock_client
    
    svc = VendorExtractionService()
    res = await svc.extract_from_chunk("test chunk", 0)
    
    assert mock_client.chat.completions.create.call_count == 2
    assert res.extraction_confidence == 0.0
    assert "Extraction failed for this section." in res.extraction_warnings

@pytest.mark.asyncio
async def test_empty_document_returns_empty_result():
    svc = VendorExtractionService()
    res = await svc.extract_full_document("")
    
    assert res.extraction_confidence == 0.0

# ─── MERGE TESTS (NO MOCKS NEEDED) ───────────────────────────────────────────

def test_list_fields_union():
    svc = VendorExtractionService()
    res1 = VendorExtractionResult(operational_states=["MH", "GJ"])
    res2 = VendorExtractionResult(operational_states=["GJ", "KA"])
    
    merged = svc.merge_results([res1, res2])
    assert sorted(merged.operational_states) == ["GJ", "KA", "MH"]

def test_scalar_fields_first_non_null():
    svc = VendorExtractionService()
    res1 = VendorExtractionResult(company_legal_name=None)
    res2 = VendorExtractionResult(company_legal_name="Company A")
    res3 = VendorExtractionResult(company_legal_name="Company B")
    
    merged = svc.merge_results([res1, res2, res3])
    assert merged.company_legal_name == "Company A"

def test_float_fields_max_non_null():
    svc = VendorExtractionService()
    res1 = VendorExtractionResult(average_annual_turnover_inr=1000.0)
    res2 = VendorExtractionResult(average_annual_turnover_inr=5000.0)
    res3 = VendorExtractionResult(average_annual_turnover_inr=None)
    
    merged = svc.merge_results([res1, res2, res3])
    assert merged.average_annual_turnover_inr == 5000.0

def test_blacklisted_overrides():
    svc = VendorExtractionService()
    res1 = VendorExtractionResult(blacklisted=False)
    res2 = VendorExtractionResult(blacklisted=True)
    res3 = VendorExtractionResult(blacklisted=False)
    
    merged = svc.merge_results([res1, res2, res3])
    assert merged.blacklisted is True

def test_extraction_warnings_deduplicated():
    svc = VendorExtractionService()
    res1 = VendorExtractionResult(extraction_warnings=["Warning A", "Warning B"])
    res2 = VendorExtractionResult(extraction_warnings=["Warning B", "Warning C"])
    
    merged = svc.merge_results([res1, res2])
    assert sorted(merged.extraction_warnings) == ["Warning A", "Warning B", "Warning C"]

# ─── API TESTS (STUBS FOR HTTPX / FASTAPI) ───────────────────────────────────
# In a real CI environment, these would use httpx.AsyncClient connected to the FastAPI app.

@pytest.mark.asyncio
async def test_api_upload_vendor_valid_pdf_returns_doc_id():
    # 10. POST /upload/vendor with valid PDF returns 201 with doc_id
    pass 

@pytest.mark.asyncio
async def test_api_upload_vendor_invalid_profile_id_returns_404():
    # 11. POST /upload/vendor?profile_id=<invalid_id> returns 404
    pass

@pytest.mark.asyncio
async def test_api_get_vendor_draft_returns_extracted_data():
    # 12. GET /upload/vendor/draft/{doc_id} returns draft_ready with extracted data after task completes
    pass

@pytest.mark.asyncio
async def test_api_confirm_vendor_creates_new_profile():
    # 13. POST /upload/vendor/confirm/{doc_id} with target_profile_id=null creates new PostgreSQL profile
    pass

@pytest.mark.asyncio
async def test_api_confirm_vendor_updates_existing_profile():
    # 14. POST /upload/vendor/confirm/{doc_id} with valid target_profile_id updates existing profile
    pass
