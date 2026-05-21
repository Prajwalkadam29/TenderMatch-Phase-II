"""
test_ingestion_pipeline.py
--------------------------
Integration tests for Component 1: PDF + LLM Ingestion Pipeline.

Tests cover:
  - Text chunking logic
  - LLM extraction schema validation
  - Multi-chunk merge intelligence
  - Search text builder
  - MongoDB document update (mocked)
  - PostgreSQL upsert (mocked)
  - Full Celery task (unit-level with mocks)

Run with: python -m pytest tests/test_ingestion_pipeline.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# ─── Unit tests: chunk_text ───────────────────────────────────────────────────

# chunk_text is now in the shared utility — import from there (Q6 fix)
from app.utils.text_chunker import chunk_text as _chunk_text


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        text = "A" * 500
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_exact_size_returns_single_chunk(self):
        text = "B" * 2000
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) == 1

    def test_large_text_splits_correctly(self):
        text = "C" * 5000
        chunks = _chunk_text(text, chunk_size=2000, overlap=200)
        # Each chunk: 2000 chars; stride: 1800 → chunks cover 0, 1800, 3600
        assert len(chunks) == 3
        assert len(chunks[0]) == 2000
        # Overlap: end of chunk[0] and start of chunk[1] share 200 chars
        assert chunks[0][-200:] == chunks[1][:200]

    def test_empty_text_returns_empty_list(self):
        # Shared utility returns [] for empty string (guards against empty-chunk bugs)
        chunks = _chunk_text("", chunk_size=2000, overlap=200)
        assert chunks == []

    def test_overlap_cannot_exceed_chunk_size(self):
        text = "D" * 10_000
        chunks = _chunk_text(text, chunk_size=500, overlap=100)
        assert all(len(c) <= 500 for c in chunks)


# ─── Unit tests: _merge_extractions ──────────────────────────────────────────

from app.services.llm_service import _merge_extractions, _empty_extraction


class TestMergeExtractions:
    def test_empty_list_returns_empty(self):
        result = _merge_extractions([])
        assert result == _empty_extraction()

    def test_single_extraction_returned_as_is(self):
        ext = _empty_extraction()
        ext["domain"] = "Information Technology"
        ext["extraction_confidence"] = 0.8
        assert _merge_extractions([ext]) == ext

    def test_highest_confidence_wins_for_scalar(self):
        ext1 = _empty_extraction()
        ext1["domain"] = "Construction"
        ext1["extraction_confidence"] = 0.4

        ext2 = _empty_extraction()
        ext2["domain"] = "Information Technology"
        ext2["extraction_confidence"] = 0.9

        result = _merge_extractions([ext1, ext2])
        assert result["domain"] == "Information Technology"

    def test_certifications_are_unioned(self):
        ext1 = _empty_extraction()
        ext1["mandatory_certifications"] = ["ISO 9001:2015", "CMMI Level 3"]
        ext1["extraction_confidence"] = 0.7

        ext2 = _empty_extraction()
        ext2["mandatory_certifications"] = ["ISO 27001", "ISO 9001:2015"]  # duplicate
        ext2["extraction_confidence"] = 0.6

        result = _merge_extractions([ext1, ext2])
        certs = result["mandatory_certifications"]
        assert len(certs) == 3  # deduped
        assert "ISO 9001:2015" in certs
        assert "CMMI Level 3" in certs
        assert "ISO 27001" in certs

    def test_null_scalar_falls_back_to_next_chunk(self):
        ext1 = _empty_extraction()
        ext1["location_state"] = None
        ext1["extraction_confidence"] = 0.9

        ext2 = _empty_extraction()
        ext2["location_state"] = "Maharashtra"
        ext2["extraction_confidence"] = 0.5

        result = _merge_extractions([ext1, ext2])
        assert result["location_state"] == "Maharashtra"

    def test_confidence_is_averaged(self):
        exts = []
        for conf in [0.6, 0.8, 1.0]:
            e = _empty_extraction()
            e["extraction_confidence"] = conf
            exts.append(e)

        result = _merge_extractions(exts)
        assert abs(result["extraction_confidence"] - round((0.6 + 0.8 + 1.0) / 3, 3)) < 0.001

    def test_deadline_merged_field_by_field(self):
        ext1 = _empty_extraction()
        ext1["deadline"]["bid_submission"] = "2026-06-15"
        ext1["extraction_confidence"] = 0.8

        ext2 = _empty_extraction()
        ext2["deadline"]["pre_bid_meeting"] = "2026-05-30"
        ext2["extraction_confidence"] = 0.6

        result = _merge_extractions([ext1, ext2])
        assert result["deadline"]["bid_submission"] == "2026-06-15"
        assert result["deadline"]["pre_bid_meeting"] == "2026-05-30"


# ─── Unit tests: build_tender_search_text ────────────────────────────────────

from app.services.llm_service import build_tender_search_text


class TestBuildTenderSearchText:
    def test_full_extraction_builds_rich_text(self):
        extracted = {
            "domain": "Information Technology",
            "scope_summary": "Supply of enterprise servers and networking equipment.",
            "mandatory_certifications": ["ISO 9001:2015", "ISO 27001"],
            "location_state": "Karnataka",
            "source_portal": "GeM",
        }
        text = build_tender_search_text(extracted)
        assert "Information Technology" in text
        assert "enterprise servers" in text
        assert "ISO 9001:2015" in text
        assert "Karnataka" in text
        assert "GeM" in text

    def test_empty_extraction_returns_fallback(self):
        text = build_tender_search_text(_empty_extraction())
        assert text == "Government procurement tender"

    def test_partial_extraction_skips_null_fields(self):
        extracted = _empty_extraction()
        extracted["domain"] = "Healthcare"
        text = build_tender_search_text(extracted)
        assert "Healthcare" in text
        assert "None" not in text
        assert "null" not in text.lower()


# ─── Unit tests: _sanitize_extraction ────────────────────────────────────────

from app.services.llm_service import _sanitize_extraction


class TestSanitizeExtraction:
    def test_string_estimated_value_converted_to_int(self):
        raw = _empty_extraction()
        raw["estimated_value"] = "5,00,00,000"
        result = _sanitize_extraction(raw)
        assert result["estimated_value"] == 50000000

    def test_string_certifications_wrapped_in_list(self):
        raw = _empty_extraction()
        raw["mandatory_certifications"] = "ISO 9001"  # string, not list
        result = _sanitize_extraction(raw)
        assert isinstance(result["mandatory_certifications"], list)
        assert result["mandatory_certifications"] == ["ISO 9001"]

    def test_confidence_clamped_to_0_1(self):
        raw = _empty_extraction()
        raw["extraction_confidence"] = 1.5  # out of range
        result = _sanitize_extraction(raw)
        assert result["extraction_confidence"] == 1.0

    def test_negative_confidence_clamped_to_0(self):
        raw = _empty_extraction()
        raw["extraction_confidence"] = -0.5
        result = _sanitize_extraction(raw)
        assert result["extraction_confidence"] == 0.0


# ─── Integration test: LLM extraction (mocked Groq) ─────────────────────────

@pytest.mark.asyncio
async def test_extract_tender_structured_data_with_mock():
    """
    Tests the full multi-chunk extraction with a mocked Groq API.
    Verifies that chunks are processed and results are merged correctly.
    """
    mock_response_payload = {
        "tender_id": "NIT/2026/IT/001",
        "source_portal": "eProcure",
        "domain": "Information Technology",
        "scope_summary": "Supply, installation and commissioning of enterprise IT infrastructure.",
        "estimated_value": 50000000,
        "location_state": "Delhi",
        "min_avg_turnover": 15000000,
        "mandatory_certifications": ["ISO 9001:2015", "CMMI Level 3"],
        "deadline": {"bid_submission": "2026-07-01", "pre_bid_meeting": "2026-06-15"},
        "extraction_confidence": 0.85,
        "evidence": {
            "eligibility": {"page": 5, "section": "Section 3"},
            "financial": {"page": 8, "section": "Section 5.2"},
        },
    }

    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_response_payload)

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("app.services.llm_service.AsyncGroq") as MockGroq:
        instance = AsyncMock()
        instance.chat.completions.create = AsyncMock(return_value=mock_completion)
        MockGroq.return_value = instance

        from app.services.llm_service import extract_tender_structured_data

        chunks = ["Chunk 1 content about IT tender", "Chunk 2 with financial details"]
        result = await extract_tender_structured_data(
            full_text="Full text here",
            chunks=chunks,
            max_chunks=2,
        )

    assert result["domain"] == "Information Technology"
    assert result["tender_id"] == "NIT/2026/IT/001"
    assert result["estimated_value"] == 50000000
    assert "ISO 9001:2015" in result["mandatory_certifications"]
    assert result["deadline"]["bid_submission"] == "2026-07-01"
    assert result["extraction_confidence"] == 0.85


# ─── Integration test: Celery task (mocked I/O) ──────────────────────────────

def test_ingest_tender_document_task_success():
    """
    Tests the full Celery task with all external I/O mocked.
    Verifies correct stage transitions and return payload.
    """
    mock_extracted = {
        "tender_id": "TEST-001",
        "source_portal": "GeM",
        "domain": "Construction",
        "scope_summary": "Construction of government office building.",
        "estimated_value": 100000000,
        "location_state": "Maharashtra",
        "min_avg_turnover": 30000000,
        "mandatory_certifications": ["ISO 9001:2015"],
        "deadline": {"bid_submission": "2026-08-01", "pre_bid_meeting": None},
        "extraction_confidence": 0.78,
        "evidence": {
            "eligibility": {"page": 3, "section": "Clause 4"},
            "financial": {"page": 6, "section": "Clause 7"},
        },
    }

    with (
        patch("app.tasks.ingestion_tasks.os.path.exists", return_value=True),
        patch("builtins.open", MagicMock(return_value=MagicMock(
            __enter__=lambda s: s,
            __exit__=MagicMock(return_value=False),
            read=lambda: b"%PDF-1.4 fake pdf bytes",
        ))),
        patch("app.tasks.ingestion_tasks.extract_text_from_bytes", return_value="Sample tender text " * 200),
        patch("app.tasks.ingestion_tasks._run_async", return_value=mock_extracted),
        patch("app.tasks.ingestion_tasks.extract_tender_structured_data", MagicMock()),
        patch("app.tasks.ingestion_tasks._upsert_tender_postgres", MagicMock()),
        patch("app.tasks.ingestion_tasks.build_tender_search_text", return_value="IT tender Maharashtra ISO 9001"),
        patch("app.tasks.ingestion_tasks.get_embedding_service") as mock_emb,
        patch("app.tasks.ingestion_tasks.get_celery_db") as mock_db,
        patch("app.tasks.notification_tasks.run_match_and_notify_task", MagicMock()),
    ):
        # Mock embedding service
        mock_emb_instance = MagicMock()
        mock_emb_instance.encode_text_sync.return_value = [0.1] * 384
        mock_emb.return_value = mock_emb_instance

        # Mock MongoDB
        mock_db_instance = MagicMock()
        mock_db_instance.documents.update_one = MagicMock()
        mock_db.return_value = mock_db_instance

        from app.tasks.ingestion_tasks import ingest_tender_document

        # Call synchronously (bypass Celery worker)
        result = ingest_tender_document(
            "507f1f77bcf86cd799439011",
            "/uploads/tender/sample.pdf",
            org_id="550e8400-e29b-41d4-a716-446655440000",
            uploaded_by="550e8400-e29b-41d4-a716-446655440001",
        )

    assert result["status"] == "success"
    assert result["domain"] == "Construction"
    assert result["extraction_confidence"] == 0.78
    assert result["certifications_found"] == 1


def test_ingest_tender_document_file_not_found():
    """Verifies task fails fast (no retry) on FileNotFoundError."""
    with (
        patch("app.tasks.ingestion_tasks.os.path.exists", return_value=False),
        patch("app.tasks.ingestion_tasks.get_celery_db") as mock_db,
    ):
        mock_db_instance = MagicMock()
        mock_db_instance.documents.update_one = MagicMock()
        mock_db.return_value = mock_db_instance

        from app.tasks.ingestion_tasks import ingest_tender_document

        with pytest.raises(FileNotFoundError):
            ingest_tender_document(
                "507f1f77bcf86cd799439011",
                "/nonexistent/file.pdf",
            )

        # Verify MongoDB was updated to "failed"
        call_args = mock_db_instance.documents.update_one.call_args
        assert call_args[0][1]["$set"]["status"] == "failed"
