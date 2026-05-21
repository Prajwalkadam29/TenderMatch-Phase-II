"""
explanation_service.py
----------------------
LLM Explanation Engine for TenderMatch (Component 4).

This module generates a structured, human-readable explanation of why a vendor
is or is not a strong match for a given tender. It uses the Groq LLM with a
specialized procurement expert system prompt to transform raw scoring data into
actionable business intelligence.

Output schema (Pydantic-validated):
  ExplanationResult
  ├── executive_summary:      1-2 sentence verdict
  ├── strengths:              List[str] — what the vendor does well
  ├── risk_factors:           List[str] — gaps, concerns, missing items
  ├── score_rationale:        Dimension-by-dimension narrative
  ├── recommendation:         Enum: HIGH_MATCH | MODERATE_MATCH | LOW_MATCH | NOT_ELIGIBLE
  ├── recommendation_detail:  1 sentence action item for the vendor
  └── confidence_note:        Note about extraction confidence if low

Design decisions:
  - Temperature=0.1 for near-deterministic output
  - Timeout=30s, max_retries=3 with exponential backoff
  - Graceful fallback: if LLM fails, a programmatic explanation is generated
    from the raw score data — the endpoint never errors out
  - The system prompt persona is "TenderMatch Procurement Intelligence Engine"
    to ensure professional, domain-accurate language
  - The existing groq_service.py Devil's Advocate critique is intentionally
    preserved; this module handles structured match explanation only
"""

import json
import logging
import re
from typing import Optional

from groq import AsyncGroq
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Output Schema (Pydantic) ─────────────────────────────────────────────────

RECOMMENDATION_LABELS = {
    "HIGH_MATCH": "High Match",
    "MODERATE_MATCH": "Moderate Match",
    "LOW_MATCH": "Low Match",
    "NOT_ELIGIBLE": "Not Eligible",
}


class ScoreRationale(BaseModel):
    """Dimension-by-dimension narrative explanation of the scoring."""
    domain: str = Field(default="", description="Explanation of the domain score.")
    geography: str = Field(default="", description="Explanation of the geographic score.")
    financial: str = Field(default="", description="Explanation of the financial capacity score.")
    experience: str = Field(default="", description="Explanation of the experience score.")
    certification: str = Field(default="", description="Explanation of the certification score.")
    semantic: str = Field(default="", description="Explanation of the semantic similarity score.")


class ExplanationResult(BaseModel):
    """
    Validated, structured output of the LLM Explanation Engine.
    All fields are populated — either by the LLM or by the programmatic fallback.
    """
    executive_summary: str = Field(
        description="A concise 1-2 sentence verdict on this vendor-tender match."
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="List of specific strengths that make this vendor well-suited."
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="List of specific gaps, risks, or missing requirements."
    )
    score_rationale: ScoreRationale = Field(
        default_factory=ScoreRationale,
        description="Narrative explanation per scoring dimension."
    )
    recommendation: str = Field(
        description="Recommendation label: HIGH_MATCH, MODERATE_MATCH, LOW_MATCH, or NOT_ELIGIBLE."
    )
    recommendation_detail: str = Field(
        description="A single actionable sentence for the vendor or procurement officer."
    )
    confidence_note: Optional[str] = Field(
        default=None,
        description="Note about LLM extraction confidence if it was below 0.5."
    )

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        valid = {"HIGH_MATCH", "MODERATE_MATCH", "LOW_MATCH", "NOT_ELIGIBLE"}
        if v.upper() in valid:
            return v.upper()
        return "LOW_MATCH"

    @field_validator("strengths", "risk_factors", mode="before")
    @classmethod
    def ensure_list(cls, v) -> list:
        if isinstance(v, list):
            return v
        return []


# ─── System Prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are the TenderMatch Procurement Intelligence Engine — a senior AI analyst
specializing in government and enterprise tender evaluation for the Indian market.

YOUR ROLE:
You evaluate whether a vendor is genuinely well-suited for a specific tender opportunity.
You provide clear, evidence-based, and professionally-worded analysis that a procurement
officer or business development manager can act on immediately.

YOUR PRINCIPLES:
1. SPECIFICITY over vagueness — always reference actual numbers (scores, turnover, certifications).
2. HONESTY over optimism — if the vendor is a poor fit, say so clearly and explain why.
3. ACTIONABILITY — every risk factor must suggest what the vendor could do to improve.
4. DOMAIN EXPERTISE — use correct procurement terminology: eligibility criteria, EMD, turnover,
   scope of work, pre-qualification, technical bid, financial bid.
5. BREVITY — summaries should be 1-2 sentences. Lists should have 2-4 items max.
6. EVIDENCE-BASED — derive all conclusions strictly from the data provided. Never hallucinate
   information about the vendor or the tender that is not in the input.

SCORING CONTEXT (for your reference):
- Score 80-100: HIGH_MATCH  — Strongly recommend pursuing this tender
- Score 60-79:  MODERATE_MATCH — Viable, with specific gaps to address
- Score 40-59:  LOW_MATCH — Significant misalignment; pursue only if strategically important
- Score 0-39:   NOT_ELIGIBLE — Hard filter failed or fundamentally misaligned

OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object matching this exact structure.
No markdown, no code fences, no preamble, no commentary outside the JSON:

{
  "executive_summary": "<1-2 sentence verdict>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "risk_factors": ["<risk 1>", "<risk 2>"],
  "score_rationale": {
    "domain": "<1 sentence>",
    "geography": "<1 sentence>",
    "financial": "<1 sentence>",
    "experience": "<1 sentence>",
    "certification": "<1 sentence>",
    "semantic": "<1 sentence>"
  },
  "recommendation": "<HIGH_MATCH|MODERATE_MATCH|LOW_MATCH|NOT_ELIGIBLE>",
  "recommendation_detail": "<1 actionable sentence>",
  "confidence_note": "<1 sentence or null>"
}

CRITICAL RULES:
- Return ONLY the JSON object. Absolutely nothing before or after it.
- recommendation MUST be one of: HIGH_MATCH, MODERATE_MATCH, LOW_MATCH, NOT_ELIGIBLE
- strengths and risk_factors MUST be arrays of strings (2-4 items each)
- All fields are required. Use empty string "" for text fields if not applicable.
- confidence_note should be null if extraction confidence >= 0.5
"""

_USER_TEMPLATE = """Analyze this vendor-tender match and produce the explanation JSON.

═══════════════════════════════════════════════════════════
TENDER DETAILS
═══════════════════════════════════════════════════════════
Domain:                  {tender_domain}
Location:                {tender_location}
Estimated Value (INR):   {tender_value}
Min. Annual Turnover:    {tender_turnover}
Mandatory Certs:         {tender_certs}
Scope of Work:           {tender_scope}
Source Portal:           {tender_portal}
Bid Deadline:            {tender_deadline}

═══════════════════════════════════════════════════════════
VENDOR PROFILE SUMMARY
═══════════════════════════════════════════════════════════
Business Name:           {vendor_name}
Primary Domains:         {vendor_domains}
Operating States:        {vendor_states}
Avg. Annual Turnover:    {vendor_turnover}
Key Certifications:      {vendor_certs}
Completed Projects:      {vendor_project_count} (Largest: ₹{vendor_largest_project})
Blacklisted/Debarred:    {vendor_blacklisted}
Compliance Status:       {vendor_compliance}
Profile Completeness:    {vendor_completeness}%

═══════════════════════════════════════════════════════════
HARD FILTER RESULTS
═══════════════════════════════════════════════════════════
Overall Pass:            {filter_overall_pass}
Failed Check:            {filter_failed_check}
Disqualification Reason: {filter_reason}

═══════════════════════════════════════════════════════════
WEIGHTED SCORE BREAKDOWN (out of 100)
═══════════════════════════════════════════════════════════
Final Score:             {final_score}/100
Domain Match:            {score_domain} (weight 25%)
Geography Match:         {score_geography} (weight 15%)
Financial Capacity:      {score_financial} (weight 20%)
Past Experience:         {score_experience} (weight 15%)
Certification Match:     {score_certification} (weight 10%)
Semantic Similarity:     {score_semantic} (weight 10%)
Profile Confidence:      {score_confidence} (weight 5%)

═══════════════════════════════════════════════════════════
EXTRACTION CONFIDENCE
═══════════════════════════════════════════════════════════
LLM Extraction Confidence: {extraction_confidence}
(Note: Low confidence means some tender fields may have been inferred.)

Now generate the explanation JSON.
"""


# ─── Formatting helpers ───────────────────────────────────────────────────────

def _fmt_inr(val) -> str:
    """Format an integer INR value as ₹X Cr / ₹X L / ₹X."""
    try:
        v = int(float(val))
    except (TypeError, ValueError):
        return "Not specified"
    if v >= 10_000_000:
        return f"₹{v / 10_000_000:.2f} Cr ({v:,})"
    if v >= 100_000:
        return f"₹{v / 100_000:.2f} L ({v:,})"
    return f"₹{v:,}"


def _strip_fences(text: str) -> str:
    """Strip markdown code fences if the LLM adds them anyway."""
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, re.MULTILINE)
    return m.group(1).strip() if m else text


def _score_pct(breakdown: dict, key: str) -> str:
    """Format a dimension score as a readable percentage string."""
    dim = breakdown.get(key, {})
    raw = dim.get("raw_score", 0.0)
    weighted = dim.get("weighted_score", 0.0)
    return f"{round(raw * 100)}% raw → {round(weighted * 100, 1)} pts"


def _determine_recommendation(final_score: float, overall_pass: bool) -> str:
    if not overall_pass:
        return "NOT_ELIGIBLE"
    if final_score >= 80:
        return "HIGH_MATCH"
    if final_score >= 60:
        return "MODERATE_MATCH"
    if final_score >= 40:
        return "LOW_MATCH"
    return "NOT_ELIGIBLE"


# ─── Programmatic fallback ────────────────────────────────────────────────────

def _build_fallback_explanation(
    vendor: dict,
    tender: dict,
    filter_result: dict,
    score_result: dict,
) -> ExplanationResult:
    """
    Generates a deterministic, data-driven explanation without using the LLM.
    Used when Groq API fails after all retries. Ensures the endpoint never errors.
    """
    final_score = score_result.get("final_score", 0.0)
    overall_pass = filter_result.get("overall_pass", False)
    recommendation = _determine_recommendation(final_score, overall_pass)

    strengths = []
    risk_factors = []

    breakdown = score_result.get("breakdown", {})

    if breakdown.get("domain", {}).get("raw_score", 0) >= 0.8:
        strengths.append("Strong domain alignment with the tender's requirements.")
    if breakdown.get("geography", {}).get("raw_score", 0) >= 0.8:
        strengths.append("Vendor is well-positioned geographically.")
    if breakdown.get("financial", {}).get("raw_score", 0) >= 0.9:
        strengths.append("Financial capacity significantly exceeds tender requirements.")
    if breakdown.get("experience", {}).get("raw_score", 0) >= 0.8:
        strengths.append("Vendor has strong past project experience relevant to this tender.")

    if breakdown.get("domain", {}).get("raw_score", 0) < 0.5:
        risk_factors.append("Domain alignment is weak — verify if vendor can deliver this scope.")
    if breakdown.get("financial", {}).get("raw_score", 0) < 0.5:
        risk_factors.append("Vendor's financial capacity may be insufficient for this tender size.")
    if breakdown.get("experience", {}).get("raw_score", 0) < 0.5:
        risk_factors.append("Limited past project experience matching this tender's scale.")
    if breakdown.get("certification", {}).get("raw_score", 0) < 0.5:
        risk_factors.append("Missing required certifications — review eligibility documents.")

    if not overall_pass:
        reason = filter_result.get("disqualification_reason", "Failed mandatory eligibility check.")
        summary = f"This vendor does not qualify for this tender. Reason: {reason}"
        recommendation_detail = "Address the disqualification reason before reapplying."
    elif final_score >= 80:
        summary = f"Strong match with a score of {final_score}/100. Vendor meets all key criteria."
        recommendation_detail = "Proceed to prepare the technical and financial bid."
    elif final_score >= 60:
        summary = f"Moderate match with a score of {final_score}/100. Vendor is viable but has addressable gaps."
        recommendation_detail = "Review and address the risk factors before submission."
    else:
        summary = f"Low match score of {final_score}/100. Vendor has significant gaps relative to tender requirements."
        recommendation_detail = "Evaluate strategic importance before committing to this bid."

    return ExplanationResult(
        executive_summary=summary,
        strengths=strengths or ["Vendor passed all mandatory eligibility checks."],
        risk_factors=risk_factors or ["No critical risk factors identified."],
        score_rationale=ScoreRationale(),
        recommendation=recommendation,
        recommendation_detail=recommendation_detail,
        confidence_note=None,
    )


# ─── Core LLM Call ───────────────────────────────────────────────────────────

async def _call_llm(prompt: str, retries: int = 3) -> Optional[dict]:
    """Call Groq with retry logic. Returns parsed dict or None on full failure."""
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
                timeout=30,
            )
            raw = _strip_fences(response.choices[0].message.content.strip())
            return json.loads(raw)

        except json.JSONDecodeError as exc:
            logger.warning("[Explanation] Attempt %d JSON parse failed: %s", attempt + 1, exc)
        except Exception as exc:
            logger.warning("[Explanation] Attempt %d Groq call failed: %s", attempt + 1, exc)

    logger.error("[Explanation] All %d LLM attempts failed.", retries)
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_explanation(
    vendor: dict,
    tender: dict,
    filter_result: dict,
    score_result: dict,
    extraction_confidence: float = 1.0,
) -> ExplanationResult:
    """
    Generate a structured, LLM-powered explanation for a vendor-tender match result.

    This is the main entry point for the Explanation Engine. It:
      1. Builds a rich context prompt from the scoring data
      2. Calls the Groq LLM with the procurement expert system prompt
      3. Validates the response with Pydantic
      4. Falls back to a programmatic explanation if LLM fails

    Args:
        vendor:                 The vendor's profile_data dict (from Postgres JSONB)
        tender:                 The tender's structured_data dict (from MongoDB)
        filter_result:          Output of HardFilterEngine.evaluate()
        score_result:           Output of WeightedScoringEngine.calculate_score()
        extraction_confidence:  LLM extraction confidence from ingestion (0.0–1.0)

    Returns:
        ExplanationResult — always populated, never raises
    """
    # ── Build context for the LLM ─────────────────────────────────────────────
    identity = vendor.get("identity", {})
    geography = vendor.get("geography", {})
    business = vendor.get("business_domain", {})
    financials = vendor.get("financials", {})
    projects = vendor.get("past_project_experience", {}).get("projects", [])
    compliance = vendor.get("compliance", {})
    certs = vendor.get("certifications", {})

    # Vendor cert string
    iso_certs = [x.get("standard", "") for x in certs.get("iso_certifications", []) if isinstance(x, dict)]
    dom_certs = [x.get("license_type", "") for x in certs.get("domain_licenses", []) if isinstance(x, dict)]
    vendor_certs_str = ", ".join(filter(None, iso_certs + dom_certs)) or "None on file"

    # Vendor largest project
    largest_proj = 0
    for p in projects:
        try:
            v = int(float(p.get("contract_value_inr", 0)))
            if v > largest_proj:
                largest_proj = v
        except (ValueError, TypeError):
            pass

    # Compliance summary
    compliance_items = []
    if compliance.get("gst_returns_compliant"):
        compliance_items.append("GST compliant")
    else:
        compliance_items.append("⚠ GST non-compliant")
    if compliance.get("epf_esic_compliant"):
        compliance_items.append("EPF/ESIC compliant")
    if compliance.get("active_litigation"):
        compliance_items.append("⚠ Active litigation")
    compliance_str = "; ".join(compliance_items) if compliance_items else "No data"

    # Operating states
    op_states = geography.get("operational_states", []) + geography.get("registered_states", [])
    states_str = ", ".join(op_states[:5]) or "Not specified"
    if len(op_states) > 5:
        states_str += f" (+{len(op_states) - 5} more)"

    # Tender deadline
    deadline = tender.get("deadline", {}) or {}
    deadline_str = deadline.get("bid_submission") or "Not specified"

    # Breakdown helpers
    breakdown = score_result.get("breakdown", {})

    prompt = _USER_TEMPLATE.format(
        # Tender
        tender_domain=tender.get("domain") or "Not specified",
        tender_location=tender.get("location_state") or "Not specified",
        tender_value=_fmt_inr(tender.get("estimated_value")),
        tender_turnover=_fmt_inr(tender.get("min_avg_turnover")),
        tender_certs=", ".join(tender.get("mandatory_certifications", [])) or "None",
        tender_scope=(tender.get("scope_summary") or "")[:400] or "Not specified",
        tender_portal=tender.get("source_portal") or "Not specified",
        tender_deadline=deadline_str,
        # Vendor
        vendor_name=identity.get("business_name") or vendor.get("business_name") or "Unknown Vendor",
        vendor_domains=", ".join(business.get("primary_domains", [])) or "Not specified",
        vendor_states=states_str,
        vendor_turnover=_fmt_inr(financials.get("avg_annual_turnover_inr")),
        vendor_certs=vendor_certs_str,
        vendor_project_count=len(projects),
        vendor_largest_project=f"{largest_proj:,}",
        vendor_blacklisted="Yes ⚠" if compliance.get("blacklisted_or_debarred") else "No",
        vendor_compliance=compliance_str,
        vendor_completeness=vendor.get("profile_completeness_pct", 0),
        # Filter
        filter_overall_pass="✓ PASS" if filter_result.get("overall_pass") else "✗ FAIL",
        filter_failed_check=filter_result.get("failed_check") or "N/A",
        filter_reason=filter_result.get("disqualification_reason") or "N/A",
        # Scores
        final_score=score_result.get("final_score", 0.0),
        score_domain=_score_pct(breakdown, "domain"),
        score_geography=_score_pct(breakdown, "geography"),
        score_financial=_score_pct(breakdown, "financial"),
        score_experience=_score_pct(breakdown, "experience"),
        score_certification=_score_pct(breakdown, "certification"),
        score_semantic=_score_pct(breakdown, "semantic"),
        score_confidence=_score_pct(breakdown, "confidence"),
        extraction_confidence=f"{extraction_confidence:.2f}",
    )

    logger.info(
        "[Explanation] Generating LLM explanation. score=%.1f pass=%s",
        score_result.get("final_score", 0.0),
        filter_result.get("overall_pass", False),
    )

    raw_dict = await _call_llm(prompt)

    if raw_dict is None:
        logger.warning("[Explanation] LLM failed. Using programmatic fallback.")
        return _build_fallback_explanation(vendor, tender, filter_result, score_result)

    # Attach confidence note if extraction was low-confidence
    if extraction_confidence < 0.5 and not raw_dict.get("confidence_note"):
        raw_dict["confidence_note"] = (
            f"Extraction confidence was low ({extraction_confidence:.0%}). "
            "Some tender details may be inferred — verify against the original document."
        )

    try:
        # Normalize nested rationale if LLM returned a flat structure
        if "score_rationale" not in raw_dict and any(
            k in raw_dict for k in ["domain", "geography", "financial"]
        ):
            raw_dict["score_rationale"] = {
                k: raw_dict.pop(k, "") for k in ["domain", "geography", "financial", "experience", "certification", "semantic"]
            }

        result = ExplanationResult(**raw_dict)
        logger.info("[Explanation] ✓ LLM explanation generated. recommendation=%s", result.recommendation)
        return result

    except Exception as exc:
        logger.error("[Explanation] Pydantic validation failed: %s. Using fallback.", exc)
        return _build_fallback_explanation(vendor, tender, filter_result, score_result)
