from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MatchScoreBreakdown(BaseModel):
    domain_fit: float = 0.0
    geography_fit: float = 0.0
    financial_capacity: float = 0.0
    experience_track_record: float = 0.0
    certifications_compliance: float = 0.0
    capability_similarity: float = 0.0
    confidence_score: float = 0.0

class MatchResultInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    vendor_profile_id: str
    tender_id: str
    tender_title: str
    final_score: float
    recommendation: str  # e.g., "Strongly Recommended"
    is_eligible: bool
    disqualification_reasons: List[str] = []
    score_breakdown: MatchScoreBreakdown
    explanation_text: str
    weaknesses: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

def match_helper(match) -> dict:
    return {
        "id": str(match["_id"]),
        "vendor_profile_id": match["vendor_profile_id"],
        "tender_id": match["tender_id"],
        "tender_title": match["tender_title"],
        "final_score": match["final_score"],
        "recommendation": match["recommendation"],
        "is_eligible": match["is_eligible"],
        "disqualification_reasons": match.get("disqualification_reasons", []),
        "score_breakdown": match["score_breakdown"],
        "explanation_text": match["explanation_text"],
        "strengths": match.get("strengths", []),
        "weaknesses": match.get("weaknesses", []),
        "created_at": match["created_at"].isoformat()
    }
