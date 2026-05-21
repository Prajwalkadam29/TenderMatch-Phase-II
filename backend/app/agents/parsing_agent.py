"""
parsing_agent.py
----------------
Node 2 of the TenderMatch LangGraph pipeline.

Responsibilities:
  - Validate the tender_structured_data loaded by ingestion_agent
  - If critical fields are missing (domain, scope_summary) AND extraction_confidence
    is low, call llm_service to re-extract from raw_text
  - Populate: tender_structured_data (enriched), parse_warnings, tender_parsed
"""

import logging
from typing import Optional

from app.agents.state import TenderMatchState

logger = logging.getLogger(__name__)

# Minimum confidence below which we attempt re-extraction
RE_EXTRACT_CONFIDENCE_THRESHOLD = 0.3

# Fields considered critical for matching quality
CRITICAL_FIELDS = ["domain", "scope_summary", "location_state"]


def _count_missing_critical(structured_data: dict) -> list:
    """Returns list of critical fields that are null or empty."""
    missing = []
    for field in CRITICAL_FIELDS:
        val = structured_data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing


async def parsing_agent(state: TenderMatchState) -> dict:
    """
    LangGraph node: validates and optionally enriches tender structured data.

    If extraction confidence < 0.3 AND critical fields are missing,
    attempts a targeted re-extraction using llm_service on the raw_text.
    Otherwise validates what exists and flags warnings.
    """
    logger.info("[Agent:Parsing] START")

    tender_sd = state.get("tender_structured_data") or {}
    extraction_confidence = state.get("extraction_confidence", 0.5)
    tender_doc = state.get("tender_doc") or {}

    warnings = []
    missing_critical = _count_missing_critical(tender_sd)

    if missing_critical:
        warnings.append(f"Missing critical fields: {', '.join(missing_critical)}")

    # Attempt re-extraction only if confidence is very low AND critical fields are missing
    if missing_critical and extraction_confidence < RE_EXTRACT_CONFIDENCE_THRESHOLD:
        logger.info(
            "[Agent:Parsing] Low confidence (%.2f) + missing %s — attempting re-extraction.",
            extraction_confidence, missing_critical,
        )
        raw_text = tender_doc.get("raw_text", "")
        if raw_text and len(raw_text) > 100:
            try:
                from app.services.llm_service import extract_tender_structured_data
                from app.tasks.ingestion_tasks import _chunk_text

                chunks = _chunk_text(raw_text, chunk_size=2000, overlap=200)
                re_extracted = await extract_tender_structured_data(
                    full_text=raw_text, chunks=chunks, max_chunks=3
                )

                # Merge: only fill in fields that were missing in original
                for field in missing_critical:
                    val = re_extracted.get(field)
                    if val is not None and val != "" and val != []:
                        tender_sd[field] = val
                        logger.info("[Agent:Parsing] Re-extracted '%s': %s", field, val)

                if re_extracted.get("extraction_confidence", 0) > extraction_confidence:
                    extraction_confidence = re_extracted["extraction_confidence"]
                    warnings.append("Partial re-extraction was performed.")

            except Exception as exc:
                logger.warning("[Agent:Parsing] Re-extraction failed: %s — using original data.", exc)
                warnings.append(f"Re-extraction attempted but failed: {exc}")
        else:
            warnings.append("No raw_text available for re-extraction.")

    # Final validation
    has_enough_data = len(_count_missing_critical(tender_sd)) < len(CRITICAL_FIELDS)
    if not has_enough_data:
        warnings.append("WARNING: All critical tender fields are missing. Match quality will be low.")

    logger.info(
        "[Agent:Parsing] ✓ Parsed. missing=%s warnings=%d",
        _count_missing_critical(tender_sd), len(warnings),
    )

    return {
        "current_stage": "parsing_complete",
        "tender_structured_data": tender_sd,
        "extraction_confidence": extraction_confidence,
        "tender_parsed": True,
        "parse_warnings": warnings if warnings else [],
    }
