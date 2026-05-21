"""
vendor_extraction_service.py
----------------------------
Multi-chunk LLM extraction service for vendor capability documents.

Design decisions:
  - Per-request instantiation (one VendorExtractionService per Celery task call)
    matches the pattern of groq_service.py — no shared state between tasks.
  - chunk_text imported from app.utils.text_chunker (shared with ingestion pipeline).
  - asyncio.Semaphore(10) caps concurrent Groq calls — prevents rate-limit hits on
    large PDFs that produce many chunks (EC7).
  - normalize_financial_value() applied after Pydantic parsing — handles LLM quirks
    like "₹ 5 Crore", "2.5 cr", "INR 45 Lakhs" (EC8).
  - Partial chunk failure is tracked explicitly: if some chunks succeed, the merge
    proceeds with a descriptive warning instead of treating the whole doc as failed (EC3).
  - If ALL chunks fail (Groq completely down), returns an empty VendorExtractionResult
    with extraction_confidence=0.0. The Celery task then writes status=draft_ready
    (not failed) so users can still do manual profile entry (EC2).
"""

import json
import re
import logging
import asyncio
from typing import Any, List, Optional

from groq import AsyncGroq
from pydantic import ValidationError

from app.core.config import settings
from app.db.models.vendor_extraction_models import VendorExtractionResult
from app.utils.text_chunker import chunk_text  # shared utility — no inline copy

logger = logging.getLogger(__name__)

# Maximum concurrent Groq calls — prevents rate-limit storms on large docs (EC7).
_GROQ_SEMAPHORE = asyncio.Semaphore(10)

# Multipliers for Indian financial shorthand normalization (EC8).
_CRORE_MULTIPLIER = 10_000_000   # 1 crore = 10 million INR
_LAKH_MULTIPLIER  = 100_000      # 1 lakh  = 100 thousand INR


# ─── Financial Normalization (EC8) ───────────────────────────────────────────

def normalize_financial_value(raw: Any) -> Optional[float]:
    """
    Normalize a raw financial value from the LLM into an absolute INR float.

    Handles:
      - Plain numbers (int/float): returned as-is
      - Strings with Indian shorthand: "crore/cr/Cr/CRORE", "lakh/lac/L/LAKH"
      - Currency prefixes: "₹", "INR", "Rs.", "Rs "
      - Comma-separated numbers: "1,50,000"
      - Mixed: "INR 2.5 Cr", "approx ₹ 5 Crore", "Rs. 45 lakhs"
      - Already-normalized floats like 50000000.0

    Returns None if the value cannot be parsed (caller adds it to warnings).
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None

    text = raw.strip()

    # Strip approximate/currency prefixes
    text = re.sub(r"(?i)\b(approximately|approx\.?|around|about)\b\s*", "", text)
    text = re.sub(r"(?i)(inr|rs\.?|₹)\s*", "", text)
    text = text.replace(",", "").strip()

    # Detect and remove multiplier suffix
    multiplier = 1.0
    crore_pattern = re.compile(r"(?i)\s*(crores?|cr|crs)\s*$")
    lakh_pattern  = re.compile(r"(?i)\s*(lakhs?|lac|l)\s*$")

    if crore_pattern.search(text):
        text = crore_pattern.sub("", text).strip()
        multiplier = _CRORE_MULTIPLIER
    elif lakh_pattern.search(text):
        text = lakh_pattern.sub("", text).strip()
        multiplier = _LAKH_MULTIPLIER

    try:
        numeric = float(text)
        return numeric * multiplier
    except (ValueError, TypeError):
        return None


def _normalize_fields_in_result(result: VendorExtractionResult) -> tuple[VendorExtractionResult, list[str]]:
    """
    Apply normalize_financial_value to every financial field in a parsed result.
    Returns the mutated result and a list of normalization warnings.
    """
    warnings: list[str] = []
    data = result.model_dump()

    def _fix(field_path: str, raw_val: Any) -> Optional[float]:
        normed = normalize_financial_value(raw_val)
        if raw_val is not None and normed is None:
            warnings.append(
                f"Could not normalize financial value '{raw_val}' for field '{field_path}'. "
                "Value set to null."
            )
        return normed

    data["average_annual_turnover_inr"] = _fix(
        "average_annual_turnover_inr", data.get("average_annual_turnover_inr")
    )
    data["net_worth_inr"] = _fix("net_worth_inr", data.get("net_worth_inr"))

    for i, year_entry in enumerate(data.get("turnover_by_year") or []):
        if isinstance(year_entry, dict):
            year_entry["turnover_inr"] = _fix(
                f"turnover_by_year[{i}].turnover_inr", year_entry.get("turnover_inr")
            )

    for i, proj in enumerate(data.get("past_projects") or []):
        if isinstance(proj, dict):
            proj["contract_value_inr"] = _fix(
                f"past_projects[{i}].contract_value_inr", proj.get("contract_value_inr")
            )

    return VendorExtractionResult.model_validate(data), warnings


# ─── VendorExtractionService ─────────────────────────────────────────────────

class VendorExtractionService:
    """
    Stateless multi-chunk extraction service.
    Instantiated once per Celery task call (no shared async state between tasks).
    """

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    def _strip_fences(self, text: str) -> str:
        text = text.strip()
        pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
        match = re.match(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return text

    def _get_prompt(self, chunk: str) -> str:
        return f"""You are a specialized procurement data analyst.
Extract structured company information from the following capability statement / vendor document chunk.

DOCUMENT CHUNK:
{chunk}

Extract the data mapping directly to the following JSON schema.
Return ONLY a single valid JSON object. NO preamble, NO markdown formatting, NO backticks.

Rules:
1. All financial values (turnover, net worth, contract values) MUST be normalized to absolute INR (floats).
   - "INR 5 Crore" -> 50000000.0
   - "₹ 45 Lakhs" -> 4500000.0
   - "2.5 cr" -> 25000000.0
2. If a field is not found or is unclear, return `null` (or empty array `[]` for lists). Do NOT invent data.
3. If you are uncertain about a field, add a descriptive warning string to the `extraction_warnings` array.
4. `blacklisted` defaults to `false` unless the document explicitly states debarment, blacklisting, or suspension.
5. Provide a realistic `extraction_confidence` score between 0.0 and 1.0 (float) for this chunk based on how much clear vendor data it contains.

SCHEMA TO MATCH:
{{
  "company_legal_name": string | null,
  "registration_type": string | null,
  "pan_number": string | null,
  "gstin": string | null,
  "year_of_incorporation": int | null,
  "cin_number": string | null,
  "registered_state": string | null,
  "registered_city": string | null,
  "operational_states": [string],
  "primary_domains": [string],
  "sub_domains": [string],
  "cpv_nic_codes": [string],
  "capabilities_freetext": string | null,
  "average_annual_turnover_inr": float | null,
  "net_worth_inr": float | null,
  "turnover_by_year": [
    {{
      "financial_year": string | null,
      "turnover_inr": float | null,
      "source_text": string | null
    }}
  ],
  "solvency_certificate_available": bool | null,
  "total_projects_completed": int | null,
  "past_projects": [
    {{
      "project_title": string | null,
      "client_name": string | null,
      "client_type": string | null,
      "contract_value_inr": float | null,
      "year_of_completion": int | null,
      "location_state": string | null,
      "work_type": string | null,
      "description": string | null
    }}
  ],
  "years_in_business": int | null,
  "iso_certifications": [
    {{
      "certification_name": string | null,
      "issuing_body": string | null,
      "valid_until": string | null,
      "certificate_number": string | null
    }}
  ],
  "bis_nabl_accreditations": [
    {{
      "certification_name": string | null,
      "issuing_body": string | null,
      "valid_until": string | null,
      "certificate_number": string | null
    }}
  ],
  "domain_licenses": [
    {{
      "certification_name": string | null,
      "issuing_body": string | null,
      "valid_until": string | null,
      "certificate_number": string | null
    }}
  ],
  "blacklisted": bool | null,
  "msme_registered": bool | null,
  "msme_category": string | null,
  "extraction_confidence": float,
  "extraction_warnings": [string],
  "source_pages_referenced": [int]
}}
"""

    async def extract_from_chunk(self, chunk: str, chunk_index: int) -> VendorExtractionResult:
        """
        Extract structured data from a single text chunk.

        Retries once with a stricter system prompt on JSON/Pydantic failure.
        On all failures, returns an empty VendorExtractionResult(confidence=0.0)
        so the caller can distinguish failed chunks from successful ones (EC3).
        """
        sys_prompt = (
            "You are a procurement data analyst extracting structured company data. "
            "Always respond with raw valid JSON."
        )

        for attempt in range(2):
            try:
                async with _GROQ_SEMAPHORE:   # EC7: cap concurrent calls
                    response = await self.client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": self._get_prompt(chunk[:12_000])},
                        ],
                        temperature=0.1,
                        max_tokens=2048,
                        timeout=60,
                    )

                raw_text = self._strip_fences(response.choices[0].message.content.strip())
                parsed = json.loads(raw_text)

                result = VendorExtractionResult.model_validate(parsed)

                # EC8: Normalize financial fields after Pydantic validation
                result, norm_warnings = _normalize_fields_in_result(result)
                if norm_warnings:
                    result.extraction_warnings = (result.extraction_warnings or []) + norm_warnings

                return result

            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    "[VendorExtraction] Attempt %d failed for chunk %d (JSON/Schema): %s",
                    attempt + 1, chunk_index, e,
                )
                sys_prompt += " VERY IMPORTANT: ONLY RETURN VALID JSON. NO TEXT. STRICT SCHEMA."

            except Exception as e:
                logger.error(
                    "[VendorExtraction] LLM error for chunk %d (attempt %d): %s",
                    chunk_index, attempt + 1, e,
                )

        # All attempts exhausted — return empty sentinel so EC3 tracking works
        return VendorExtractionResult(
            extraction_confidence=0.0,
            extraction_warnings=["Extraction failed for this section."],
        )

    async def extract_full_document(self, text: str) -> VendorExtractionResult:
        """
        Orchestrate multi-chunk extraction for an entire document.

        Chunk selection strategy (unchanged from original):
          - If ≤5 chunks: process all
          - If >5 chunks: select first 2, middle, and last to maximize coverage

        Semaphore-limited concurrency (EC7): asyncio.gather is capped to
        _GROQ_SEMAPHORE (10 concurrent) — see extract_from_chunk.

        Returns a merged VendorExtractionResult.
        EC2 (all chunks fail) → confidence=0.0, all fields null. Caller sets draft_ready.
        EC3 (partial failure) → merge on successful chunks + warning about failed count.
        """
        if not text or len(text.strip()) == 0:
            return VendorExtractionResult(extraction_confidence=0.0)

        chunks = chunk_text(text, chunk_size=2000, overlap=200)

        # Select representative chunks for large documents
        if len(chunks) > 5:
            mid = len(chunks) // 2
            selected_indices = list(dict.fromkeys([0, 1, 2, mid, len(chunks) - 1]))[:5]
            selected_chunks = [chunks[i] for i in selected_indices]
        else:
            selected_chunks = chunks

        total = len(selected_chunks)
        tasks = [
            self.extract_from_chunk(chunk, i)
            for i, chunk in enumerate(selected_chunks)
        ]
        # gather respects the per-call semaphore — rate-safe for large docs (EC7)
        chunk_results: list[VendorExtractionResult] = await asyncio.gather(*tasks)

        # EC3: count failures (confidence=0.0 AND warning text = "Extraction failed for this section.")
        failed_count = sum(
            1 for r in chunk_results
            if r.extraction_confidence == 0.0
            and any("Extraction failed for this section" in w for w in (r.extraction_warnings or []))
        )

        merged = self.merge_results(chunk_results, total_chunks=total, failed_chunks=failed_count)
        return merged

    def merge_results(
        self,
        results: List[VendorExtractionResult],
        total_chunks: int = 0,
        failed_chunks: int = 0,
    ) -> VendorExtractionResult:
        """
        Merge multiple chunk results into a single VendorExtractionResult.

        Merge strategy per field type:
          - Lists   → union (deduplicated)
          - Floats  → max (financial fields) — extraction_confidence averaged
          - Bools   → any True wins (blacklisted: any True wins)
          - Scalars → first non-null wins

        EC3: Injects chunk-failure warning when some (not all) chunks failed.
        """
        merged = VendorExtractionResult(extraction_confidence=0.0).model_dump()

        confidences: list[float] = []
        all_warnings: set[str] = set()

        for res in results:
            data = res.model_dump(exclude_none=True)

            if "extraction_confidence" in data and data["extraction_confidence"] > 0:
                confidences.append(data["extraction_confidence"])

            if "extraction_warnings" in data:
                all_warnings.update(data["extraction_warnings"])

            for key, val in data.items():
                if key in ("extraction_confidence", "extraction_warnings"):
                    continue

                existing = merged.get(key)

                if isinstance(val, list):
                    if existing is None:
                        merged[key] = val
                    else:
                        for item in val:
                            if item not in existing:
                                existing.append(item)

                elif isinstance(val, float):
                    if existing is None or val > existing:
                        merged[key] = val

                elif isinstance(val, bool):
                    if key == "blacklisted":
                        if val is True:
                            merged[key] = True
                    else:
                        if existing is None or val is True:
                            merged[key] = val

                else:   # str, int — first non-null wins
                    if not existing:
                        merged[key] = val

        # EC3: Emit partial-failure warning with exact counts
        if 0 < failed_chunks < total_chunks:
            all_warnings.add(
                f"{failed_chunks} of {total_chunks} chunks failed LLM extraction. "
                "Results may be incomplete."
            )

        merged["extraction_warnings"] = list(all_warnings)
        if confidences:
            merged["extraction_confidence"] = round(sum(confidences) / len(confidences), 3)

        return VendorExtractionResult.model_validate(merged)
