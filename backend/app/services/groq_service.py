"""
groq_service.py
---------------
Sends extracted document text to Groq LLM and returns:
  - structured_data  (scope, eligibility, technical_specs, certifications, location)
  - keywords         (domain-specific multi-word phrases)

Uses the official `groq` Python SDK (async client).
"""

import json
import re
import logging
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Prompt template ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a document analysis AI specialized in government and enterprise procurement documents.
Your job is to extract structured information from tender and vendor documents.
Always respond with ONLY valid JSON. No explanation, no markdown, no code fences."""

_USER_PROMPT_TEMPLATE = """Analyze the following document and extract key information.

Document TEXT:
{document_text}

Extract and return ONLY this JSON structure (no markdown, no fences, raw JSON only):

{{
  "structured_data": {{
    "scope": "Brief description of the scope of work or services",
    "eligibility": "Eligibility criteria or vendor qualifications required",
    "technical_specs": "Key technical specifications or requirements",
    "certifications": ["List", "of", "required", "certifications"],
    "location": "Geographic location or region mentioned"
  }},
  "keywords": [
    "domain-specific multi-word phrase 1",
    "domain-specific multi-word phrase 2",
    "domain-specific multi-word phrase 3"
  ]
}}

Rules:
- Keywords MUST be multi-word domain-specific phrases (e.g. "road construction", "ISO 9001 certification", "solar panel installation")
- Avoid single generic words like "work", "project", "document"
- Keep certification names exact as they appear in the document
- If a field has no data, use null for strings or [] for arrays
- Return at least 5 and at most 15 keywords
"""


# ─── Main extraction function ─────────────────────────────────────────────────

async def extract_with_groq(document_text: str) -> dict:
    """
    Call Groq LLM and parse the returned JSON.
    Raises ValueError if the model output is not parseable JSON.
    """
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # Truncate to avoid exceeding context limits (Groq supports large windows
    # but we keep it reasonable for speed and cost)
    max_chars = 12_000
    if len(document_text) > max_chars:
        logger.warning(
            "Document text truncated from %d to %d chars for LLM processing.",
            len(document_text), max_chars
        )
        document_text = document_text[:max_chars] + "\n\n[... document truncated ...]"

    user_message = _USER_PROMPT_TEMPLATE.format(document_text=document_text)

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # fast, large-context Groq model
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,       # low temp → more deterministic extraction
        max_tokens=1024,
    )

    raw_content: str = response.choices[0].message.content.strip()

    # Defensive: strip markdown fences if model adds them anyway
    raw_content = _strip_markdown_fences(raw_content)

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("Groq returned non-JSON output:\n%s", raw_content)
        raise ValueError(
            f"LLM did not return valid JSON. Raw output snippet: {raw_content[:300]}"
        ) from exc

    # Normalise structure — ensure both top-level keys exist
    structured_data = parsed.get("structured_data") or {}
    keywords: list = parsed.get("keywords") or []

    # Ensure certifications is always a list
    certs = structured_data.get("certifications")
    if isinstance(certs, str):
        structured_data["certifications"] = [certs]
    elif not isinstance(certs, list):
        structured_data["certifications"] = []

    # Ensure keywords is a flat list of strings
    keywords = [str(k) for k in keywords if k and str(k).strip()]

    return {
        "structured_data": structured_data,
        "keywords": keywords,
    }


# ─── helpers ─────────────────────────────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if present."""
    pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(pattern, text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return text
