"""
llm_service.py
--------------
Upgraded Groq LLM extraction service for TenderMatch AI Layer (v2.0).

Key improvements over groq_service.py:
  - Strict 13-field tender schema with confidence scoring and evidence fields
  - Processes ALL selected chunks (not just chunk[0]) with intelligent merging
  - Highest-confidence chunk wins for scalar fields; arrays are unioned
  - All calls: timeout=30s, max_retries=3, temperature=0.1
  - Returns null for missing fields — never hallucinate

NOTE: groq_service.py is intentionally preserved for Devil's Advocate critique
      and conversational RAG. This module handles structured tender ingestion only.
"""

import json
import logging
import re
from typing import Optional

from groq import AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Prompts ──────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a specialist AI for government and enterprise procurement document analysis.
Your ONLY job is to extract structured information from tender document text chunks.
You MUST respond with ONLY valid JSON. No preamble, no explanation, no markdown fences, no code blocks.
Handle complex legal and government language carefully.
Use null for any field not clearly present in the text. Never hallucinate or guess values."""

_USER_TEMPLATE = """Analyze this tender document chunk and extract information.
Return ONLY a raw JSON object — no markdown, no code fences, no explanation.

DOCUMENT CHUNK:
{chunk_text}

Return EXACTLY this JSON structure:
{{
  "tender_id": null,
  "source_portal": null,
  "domain": null,
  "scope_summary": null,
  "estimated_value": null,
  "location_state": null,
  "min_avg_turnover": null,
  "mandatory_certifications": [],
  "deadline": {{
    "bid_submission": null,
    "pre_bid_meeting": null
  }},
  "extraction_confidence": 0.0,
  "evidence": {{
    "eligibility": {{"page": null, "section": null}},
    "financial": {{"page": null, "section": null}}
  }}
}}

Field extraction rules:
- tender_id: NIT number / Tender reference / EPROCURE ID found in document, or null
- source_portal: Portal name e.g. "eProcure", "GeM", "CPPP", "SAM.gov", "State PWD", or null
- domain: Primary sector e.g. "Information Technology", "Construction", "Healthcare", "Defence", "Education", or null
- scope_summary: 1-3 sentence plain English description of what work/service this tender requires
- estimated_value: Numeric value in INR as plain integer (no commas, no units, no text), or null
- location_state: Indian state name or "Pan India" or "Global", or null
- min_avg_turnover: Minimum average annual turnover requirement in INR as plain integer, or null
- mandatory_certifications: Array of exact certification strings e.g. ["ISO 9001:2015", "CMMI Level 3"], or []
- deadline.bid_submission: ISO 8601 date YYYY-MM-DD for bid submission, or null
- deadline.pre_bid_meeting: ISO 8601 date YYYY-MM-DD for pre-bid meeting, or null
- extraction_confidence: Float 0.0-1.0 — how confident are you? (1.0 = all key fields found clearly, 0.3 = sparse info)
- evidence.eligibility.page: Page number where eligibility criteria appear, or null
- evidence.eligibility.section: Section name/number for eligibility e.g. "Section 3.2", or null
- evidence.financial.page: Page number where financial requirements appear, or null
- evidence.financial.section: Section name/number for financial requirements, or null

Critical rules:
- Return ONLY the JSON object. Nothing else before or after.
- estimated_value and min_avg_turnover MUST be integers or null — never strings
- mandatory_certifications MUST be an array — never a string
- Do NOT invent data not found in the text chunk
"""


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _empty_extraction() -> dict:
    """Return a zero-confidence empty extraction matching the 13-field schema."""
    return {
        "tender_id": None,
        "source_portal": None,
        "domain": None,
        "scope_summary": None,
        "estimated_value": None,
        "location_state": None,
        "min_avg_turnover": None,
        "mandatory_certifications": [],
        "deadline": {"bid_submission": None, "pre_bid_meeting": None},
        "extraction_confidence": 0.0,
        "evidence": {
            "eligibility": {"page": None, "section": None},
            "financial": {"page": None, "section": None},
        },
    }


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if the model adds them anyway."""
    text = text.strip()
    pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(pattern, text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return text


def _coerce_int(value) -> Optional[int]:
    """Safely coerce a value to int, stripping commas and whitespace."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace(" ", "").split(".")[0]
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def _sanitize_extraction(raw: dict) -> dict:
    """Validate and sanitize a single chunk extraction result."""
    result = _empty_extraction()

    # Copy known fields
    for field in ["tender_id", "source_portal", "domain", "scope_summary", "location_state"]:
        val = raw.get(field)
        if val and isinstance(val, str) and val.strip():
            result[field] = val.strip()

    result["estimated_value"] = _coerce_int(raw.get("estimated_value"))
    result["min_avg_turnover"] = _coerce_int(raw.get("min_avg_turnover"))

    # Certifications: must be a list of strings
    certs = raw.get("mandatory_certifications")
    if isinstance(certs, list):
        result["mandatory_certifications"] = [str(c).strip() for c in certs if c]
    elif isinstance(certs, str) and certs.strip():
        result["mandatory_certifications"] = [certs.strip()]

    # Deadlines
    deadline = raw.get("deadline") or {}
    if isinstance(deadline, dict):
        result["deadline"]["bid_submission"] = deadline.get("bid_submission")
        result["deadline"]["pre_bid_meeting"] = deadline.get("pre_bid_meeting")

    # Evidence
    evidence = raw.get("evidence") or {}
    if isinstance(evidence, dict):
        for ev_type in ["eligibility", "financial"]:
            ev_block = evidence.get(ev_type) or {}
            if isinstance(ev_block, dict):
                result["evidence"][ev_type]["page"] = ev_block.get("page")
                result["evidence"][ev_type]["section"] = ev_block.get("section")

    # Confidence: clamp to [0.0, 1.0]
    try:
        conf = float(raw.get("extraction_confidence") or 0.0)
        result["extraction_confidence"] = round(max(0.0, min(1.0, conf)), 3)
    except (TypeError, ValueError):
        result["extraction_confidence"] = 0.0

    return result


# ─── Multi-chunk merge ────────────────────────────────────────────────────────

def _merge_extractions(extractions: list[dict]) -> dict:
    """
    Merge multiple per-chunk extractions into a single high-quality result.

    Strategy:
      - Scalar fields: value from the highest-confidence chunk that has it non-null
      - Arrays (certifications): union all, deduplicate (case-insensitive)
      - Nested dicts (deadline, evidence): field-by-field same scalar rule
      - Final confidence: average of all chunk confidences
    """
    if not extractions:
        return _empty_extraction()
    if len(extractions) == 1:
        return extractions[0]

    # Sort descending by confidence — highest confidence chunk wins for scalars
    by_conf = sorted(extractions, key=lambda x: x.get("extraction_confidence", 0.0), reverse=True)

    merged = _empty_extraction()

    # Scalar fields
    for field in ["tender_id", "source_portal", "domain", "scope_summary",
                  "estimated_value", "location_state", "min_avg_turnover"]:
        for ext in by_conf:
            val = ext.get(field)
            if val is not None and val != "" and val != []:
                merged[field] = val
                break

    # Certifications: union with deduplication
    seen = set()
    all_certs = []
    for ext in extractions:
        for cert in (ext.get("mandatory_certifications") or []):
            cert_str = str(cert).strip()
            if cert_str and cert_str.lower() not in seen:
                all_certs.append(cert_str)
                seen.add(cert_str.lower())
    merged["mandatory_certifications"] = all_certs

    # Deadline: field-by-field
    for dk in ["bid_submission", "pre_bid_meeting"]:
        for ext in by_conf:
            val = (ext.get("deadline") or {}).get(dk)
            if val:
                merged["deadline"][dk] = val
                break

    # Evidence: field-by-field
    for ev_type in ["eligibility", "financial"]:
        for ev_field in ["page", "section"]:
            for ext in by_conf:
                val = ((ext.get("evidence") or {}).get(ev_type) or {}).get(ev_field)
                if val is not None:
                    merged["evidence"][ev_type][ev_field] = val
                    break

    # Confidence: average across all chunks
    confidences = [ext.get("extraction_confidence", 0.0) for ext in extractions]
    merged["extraction_confidence"] = round(sum(confidences) / len(confidences), 3)

    return merged


# ─── Single-chunk extraction ──────────────────────────────────────────────────

async def _extract_single_chunk(
    client: AsyncGroq,
    chunk: str,
    chunk_index: int,
    retries: int = 3,
) -> dict:
    """
    Extract structured data from a single text chunk with retry logic.
    Returns empty extraction on all failures.
    """
    for attempt in range(retries):
        try:
            user_msg = _USER_TEMPLATE.format(chunk_text=chunk[:12_000])

            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=1024,
                timeout=30,
            )

            raw_text = _strip_fences(response.choices[0].message.content.strip())
            parsed = json.loads(raw_text)
            result = _sanitize_extraction(parsed)

            logger.info(
                "[LLM] Chunk %d/%d extracted. confidence=%.2f domain=%s",
                chunk_index + 1, retries, result["extraction_confidence"], result.get("domain"),
            )
            return result

        except json.JSONDecodeError as exc:
            logger.warning("[LLM] Chunk %d attempt %d JSON parse failed: %s", chunk_index, attempt + 1, exc)
        except Exception as exc:
            logger.warning("[LLM] Chunk %d attempt %d error: %s", chunk_index, attempt + 1, exc)

    logger.error("[LLM] Chunk %d failed after %d retries. Returning empty.", chunk_index, retries)
    return _empty_extraction()


# ─── Public API ───────────────────────────────────────────────────────────────

async def extract_tender_structured_data(
    full_text: str,
    chunks: list[str],
    max_chunks: int = 5,
) -> dict:
    """
    Main extraction entry point for the ingestion pipeline.

    Selects the most information-dense chunks (front-heavy, since tender
    metadata is usually in the first pages), runs LLM extraction on each,
    then merges all results into a single high-confidence structured dict.

    Args:
        full_text:  Complete document text (for context/reference)
        chunks:     Pre-chunked text segments (2000-char, 200-char overlap)
        max_chunks: Max number of chunks to send to LLM (cost/coverage tradeoff)

    Returns:
        Merged dict matching the 13-field schema.
    """
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # Chunk selection strategy: first 3 + middle + last (front-heavy)
    if len(chunks) <= max_chunks:
        selected_indices = list(range(len(chunks)))
    else:
        mid = len(chunks) // 2
        candidate_indices = list(dict.fromkeys([0, 1, 2, mid, len(chunks) - 1]))
        selected_indices = sorted(candidate_indices)[:max_chunks]

    selected_chunks = [chunks[i] for i in selected_indices]
    logger.info(
        "[LLM] Processing %d/%d chunks. Indices: %s",
        len(selected_chunks), len(chunks), selected_indices,
    )

    extractions = []
    for i, chunk in enumerate(selected_chunks):
        ext = await _extract_single_chunk(client, chunk, chunk_index=i)
        # Include extraction if it has any meaningful data
        has_data = any([
            ext.get("domain"),
            ext.get("scope_summary"),
            ext.get("location_state"),
            ext.get("tender_id"),
            ext.get("mandatory_certifications"),
            ext.get("extraction_confidence", 0.0) > 0.1,
        ])
        if has_data:
            extractions.append(ext)

    if not extractions:
        logger.warning("[LLM] All chunks returned empty extractions.")
        return _empty_extraction()

    merged = _merge_extractions(extractions)
    logger.info(
        "[LLM] Merge complete. final_confidence=%.2f chunks_used=%d domain=%s",
        merged["extraction_confidence"], len(extractions), merged.get("domain"),
    )
    return merged


def build_tender_search_text(extracted: dict) -> str:
    """
    Build a synthesized search text string from extracted tender fields.
    This string is embedded using all-MiniLM-L6-v2 to produce the 384-dim
    pgvector embedding for semantic similarity search.

    Combines: domain + scope_summary + mandatory_certifications + location_state
    """
    parts = []

    if extracted.get("domain"):
        parts.append(f"Domain: {extracted['domain']}")

    if extracted.get("scope_summary"):
        parts.append(extracted["scope_summary"])

    if extracted.get("mandatory_certifications"):
        certs_str = ", ".join(extracted["mandatory_certifications"])
        parts.append(f"Required certifications: {certs_str}")

    if extracted.get("location_state"):
        parts.append(f"Location: {extracted['location_state']}")

    if extracted.get("source_portal"):
        parts.append(f"Portal: {extracted['source_portal']}")

    return " | ".join(parts) if parts else "Government procurement tender"
