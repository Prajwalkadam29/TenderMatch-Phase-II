import pytest
from app.services.critic_service import critic_service
from app.db.models.critic_models import CriticReport, CriticFinding

# Common mock structures
def build_explanation(recommendation="HIGH_MATCH", strengths=None, risk_factors=None, summary=""):
    return {
        "executive_summary": summary or f"Test summary for {recommendation}",
        "strengths": strengths or ["Good domain alignment"],
        "risk_factors": risk_factors or [],
        "score_rationale": {
            "domain": "Good",
            "financial": "Good",
            "geography": "Good",
            "experience": "Good"
        },
        "recommendation": recommendation,
        "recommendation_detail": "Proceed",
        "confidence_note": None
    }

def build_score(final_score=85.0, domain=0.9, financial=0.8, geography=0.8, experience=0.8):
    return {
        "final_score": final_score,
        "breakdown": {
            "domain": {"raw_score": domain},
            "financial": {"raw_score": financial},
            "geography": {"raw_score": geography},
            "experience": {"raw_score": experience}
        }
    }

def build_filter(passed=True):
    return {
        "overall_pass": passed,
        "failed_check": None if passed else "turnover",
        "disqualification_reason": None if passed else "Turnover too low"
    }

# ─── Tests ──────────────────────────────────────────────────────────────────

def test_critic_clean_pass_high_match():
    exp = build_explanation(recommendation="HIGH_MATCH")
    score = build_score(final_score=85.0)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.overridden is False
    assert report.worst_severity == "CLEAN" or report.worst_severity == "INFO"
    assert not report.has_errors()
    assert not report.has_warnings()

def test_critic_clean_pass_moderate_match():
    exp = build_explanation(recommendation="MODERATE_MATCH")
    score = build_score(final_score=70.0)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.overridden is False
    assert not report.has_errors()

def test_critic_clean_pass_low_match():
    exp = build_explanation(recommendation="LOW_MATCH")
    score = build_score(final_score=50.0)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.overridden is False
    assert not report.has_errors()

def test_critic_clean_pass_not_eligible():
    exp = build_explanation(recommendation="NOT_ELIGIBLE")
    score = build_score(final_score=30.0)
    report = critic_service.evaluate(exp, score, build_filter(passed=False), 80.0)
    
    assert report.overridden is False
    assert not report.has_errors()

def test_critic_error_recommendation_mismatch():
    # LLM says MODERATE, but score is 85
    exp = build_explanation(recommendation="MODERATE_MATCH")
    score = build_score(final_score=85.0)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.overridden is True
    assert report.has_errors()
    assert report.worst_severity == "ERROR"
    errors = report.errors()
    assert any(e.check_name == "recommendation_score_alignment" for e in errors)
    assert report.override_reason is not None

def test_critic_error_hard_filter_fail():
    # LLM says HIGH_MATCH, but vendor failed hard filters
    exp = build_explanation(recommendation="HIGH_MATCH")
    score = build_score(final_score=85.0)
    report = critic_service.evaluate(exp, score, build_filter(passed=False), 80.0)
    
    assert report.overridden is True
    assert report.has_errors()
    errors = report.errors()
    assert any(e.check_name == "hard_filter_consistency" for e in errors)
    assert any(e.check_name == "recommendation_score_alignment" for e in errors)

def test_critic_warning_hallucinated_strength():
    # Strength references "financial" but financial score is 0.4
    exp = build_explanation(recommendation="MODERATE_MATCH", strengths=["Strong financial capacity"])
    score = build_score(final_score=65.0, financial=0.4)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.overridden is False  # Warnings don't trigger override
    assert report.has_warnings()
    assert report.worst_severity == "WARNING"
    warnings = report.warnings()
    assert any("hallucinated_strength" in w.check_name for w in warnings)

def test_critic_warning_hallucinated_risk():
    # Risk references "domain" but domain score is 0.9
    exp = build_explanation(risk_factors=["Weak domain alignment"])
    score = build_score(final_score=80.0, domain=0.9)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    assert report.has_warnings()
    warnings = report.warnings()
    assert any("hallucinated_risk" in w.check_name for w in warnings)

def test_critic_warning_confidence_sanity():
    # Vendor completeness is 30%, recommendation HIGH_MATCH, but no limitation mentioned
    exp = build_explanation(recommendation="HIGH_MATCH", summary="Vendor is a perfect match.")
    score = build_score(final_score=85.0)
    report = critic_service.evaluate(exp, score, build_filter(), 30.0)  # low completeness
    
    assert report.has_warnings()
    warnings = report.warnings()
    assert any(w.check_name == "confidence_sanity" for w in warnings)

def test_critic_serialization():
    # Test report.to_mongo_dict()
    exp = build_explanation(recommendation="HIGH_MATCH")
    score = build_score(final_score=85.0)
    report = critic_service.evaluate(exp, score, build_filter(), 80.0)
    
    mongo_dict = report.to_mongo_dict()
    assert isinstance(mongo_dict, dict)
    assert "evaluated_at" in mongo_dict
    assert isinstance(mongo_dict["evaluated_at"], str)
    assert "findings" in mongo_dict
    assert isinstance(mongo_dict["findings"], list)
    assert mongo_dict["total_checks"] >= 6
