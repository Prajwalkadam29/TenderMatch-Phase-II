"""
critic_service.py
-----------------
Standalone deterministic logic for the TenderMatch Critic Agent.

This service implements the 6 consistency rules required to validate that
the LLM-generated explanation aligns with the raw numerical scores and
hard filter results. It does NOT use an LLM.

It returns a `CriticReport` which aggregates `CriticFinding` objects.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional

from app.db.models.critic_models import (
    CriticFinding,
    CriticReport,
    WorstSeverity,
    SCORE_TO_RECOMMENDATION,
    score_to_recommendation,
)

logger = logging.getLogger(__name__)


class CriticService:
    """
    Evaluates an LLM-generated explanation against the raw score data.
    """

    def __init__(self):
        # Keywords used to map strength/risk text to scoring dimensions
        self.dimension_keywords = {
            "domain": ["domain", "sector", "industry", "scope", "technical"],
            "financial": ["financial", "turnover", "capacity", "revenue"],
            "geography": ["geography", "location", "state", "region", "presence"],
            "experience": ["experience", "past project", "track record", "completed"],
            "certification": ["certification", "iso", "license", "compliance"],
            "semantic": ["semantic", "contextual", "similarity"],
        }

    def evaluate(
        self,
        explanation_dict: dict,
        score_result: dict,
        filter_result: dict,
        vendor_completeness: float,
    ) -> CriticReport:
        """
        Run all consistency checks on the explanation output.
        
        Args:
            explanation_dict: The dict output of generate_explanation (matches ExplanationResult schema).
            score_result: The raw numerical scoring output from WeightedScoringEngine.
            filter_result: The raw hard filter output from HardFilterEngine.
            vendor_completeness: Profile completeness percentage (0-100).
            
        Returns:
            CriticReport containing findings and potential override instructions.
        """
        findings: List[CriticFinding] = []
        final_score = score_result.get("final_score", 0.0)
        breakdown = score_result.get("breakdown", {})
        overall_pass = filter_result.get("overall_pass", False)
        
        # Rule 1: Recommendation-Score Alignment (ERROR)
        findings.append(self._check_recommendation_alignment(explanation_dict, final_score, overall_pass))

        # Rule 4: Hard Filter Consistency (ERROR) - checked alongside Rule 1, but explicitly separated here
        findings.append(self._check_hard_filter_consistency(explanation_dict, overall_pass))

        # Rule 2: Strengths Must Reference High-Scoring Dimensions (WARNING)
        findings.extend(self._check_strengths(explanation_dict, breakdown))

        # Rule 3: Risk Factors Must Reference Low-Scoring or Failed Dimensions (WARNING)
        findings.extend(self._check_risk_factors(explanation_dict, breakdown))

        # Rule 5: Score Rationale Coverage (INFO)
        findings.append(self._check_score_rationale(explanation_dict))

        # Rule 6: Confidence Sanity (WARNING)
        findings.append(self._check_confidence_sanity(explanation_dict, vendor_completeness))
        
        # Determine worst severity
        worst_severity: WorstSeverity = "CLEAN"
        failed_severities = [f.severity for f in findings if not f.passed]
        
        if "ERROR" in failed_severities:
            worst_severity = "ERROR"
        elif "WARNING" in failed_severities:
            worst_severity = "WARNING"
        elif "INFO" in failed_severities:
            worst_severity = "INFO"

        # Determine override
        overridden = False
        override_reason = None
        
        # We override if there are any ERROR-level findings
        error_findings = [f for f in findings if not f.passed and f.severity == "ERROR"]
        if error_findings:
            overridden = True
            override_reason = " | ".join(f.detail for f in error_findings)

        return CriticReport(
            total_checks=len(findings),
            passed_checks=sum(1 for f in findings if f.passed),
            failed_checks=len(failed_severities),
            worst_severity=worst_severity,
            findings=findings,
            overridden=overridden,
            override_reason=override_reason,
            evaluated_at=datetime.now(timezone.utc),
        )

    def _check_recommendation_alignment(self, explanation_dict: dict, final_score: float, overall_pass: bool) -> CriticFinding:
        actual_rec = explanation_dict.get("recommendation", "UNKNOWN")
        expected_rec = score_to_recommendation(final_score, overall_pass)
        
        passed = actual_rec == expected_rec
        
        return CriticFinding(
            check_name="recommendation_score_alignment",
            severity="ERROR",
            passed=passed,
            expected=f"Recommendation must be {expected_rec} for score {final_score:.1f}",
            actual=f"LLM returned recommendation: {actual_rec}",
            detail=f"Recommendation mismatch. Score {final_score:.1f} warrants {expected_rec}, but explanation provided {actual_rec}." if not passed else "Recommendation aligns with score."
        )

    def _check_hard_filter_consistency(self, explanation_dict: dict, overall_pass: bool) -> CriticFinding:
        actual_rec = explanation_dict.get("recommendation", "UNKNOWN")
        
        if not overall_pass:
            passed = actual_rec in ["NOT_ELIGIBLE", "LOW_MATCH"]
            expected = "NOT_ELIGIBLE or LOW_MATCH (Hard filter failed)"
        else:
            passed = True
            expected = "Any eligible recommendation (Hard filter passed)"
            
        return CriticFinding(
            check_name="hard_filter_consistency",
            severity="ERROR",
            passed=passed,
            expected=expected,
            actual=f"LLM returned recommendation: {actual_rec}",
            detail="Vendor failed hard filters, but LLM recommended them." if not passed else "Hard filter consistency maintained."
        )

    def _check_strengths(self, explanation_dict: dict, breakdown: dict) -> List[CriticFinding]:
        findings = []
        strengths = explanation_dict.get("strengths", [])
        
        for idx, strength in enumerate(strengths):
            strength_lower = strength.lower()
            for dim, keywords in self.dimension_keywords.items():
                if any(kw in strength_lower for kw in keywords):
                    # Found a referenced dimension. Check its raw score.
                    dim_data = breakdown.get(dim, {})
                    raw_score = dim_data.get("raw_score", 0.0)
                    
                    if raw_score < 0.6:
                        findings.append(CriticFinding(
                            check_name=f"hallucinated_strength_{idx}",
                            severity="WARNING",
                            passed=False,
                            expected=f"Dimension '{dim}' score >= 0.6 to be listed as strength",
                            actual=f"Dimension '{dim}' score is {raw_score:.2f}",
                            detail=f"Strength mentions '{dim}' but the actual raw score is low ({raw_score:.2f}). Potential hallucination."
                        ))
                    else:
                        findings.append(CriticFinding(
                            check_name=f"valid_strength_{idx}_{dim}",
                            severity="INFO",
                            passed=True,
                            expected=f"Dimension '{dim}' score >= 0.6",
                            actual=f"Dimension '{dim}' score is {raw_score:.2f}",
                            detail=f"Strength referencing '{dim}' correctly aligns with high score."
                        ))
        
        # If no findings were generated (e.g. no strengths or no keywords matched), add a pass
        if not findings:
            findings.append(CriticFinding(
                check_name="hallucinated_strength_check",
                severity="INFO",
                passed=True,
                expected="No hallucinated strengths",
                actual="No hallucinated strengths detected",
                detail="All strengths align with high-scoring dimensions or no specific dimensions mentioned."
            ))
            
        return findings

    def _check_risk_factors(self, explanation_dict: dict, breakdown: dict) -> List[CriticFinding]:
        findings = []
        risk_factors = explanation_dict.get("risk_factors", [])
        
        # Check if risk factors are empty but there are low scores
        low_dims = [dim for dim, data in breakdown.items() if data.get("raw_score", 1.0) < 0.5]
        if not risk_factors and low_dims:
            findings.append(CriticFinding(
                check_name="missing_risk_factors",
                severity="WARNING",
                passed=False,
                expected="Risk factors should be present for dimensions scoring < 0.5",
                actual="Risk factors are empty",
                detail=f"Dimensions {low_dims} scored < 0.5, but no risk factors were listed."
            ))
            return findings

        for idx, risk in enumerate(risk_factors):
            risk_lower = risk.lower()
            for dim, keywords in self.dimension_keywords.items():
                if any(kw in risk_lower for kw in keywords):
                    # Found a referenced dimension. Check its raw score.
                    dim_data = breakdown.get(dim, {})
                    raw_score = dim_data.get("raw_score", 0.0)
                    
                    if raw_score > 0.8:
                        findings.append(CriticFinding(
                            check_name=f"hallucinated_risk_{idx}",
                            severity="WARNING",
                            passed=False,
                            expected=f"Dimension '{dim}' score < 0.8 to be listed as a risk",
                            actual=f"Dimension '{dim}' score is {raw_score:.2f}",
                            detail=f"Risk factor mentions '{dim}' but the actual raw score is very high ({raw_score:.2f}). Potential hallucination."
                        ))
                    else:
                        findings.append(CriticFinding(
                            check_name=f"valid_risk_{idx}_{dim}",
                            severity="INFO",
                            passed=True,
                            expected=f"Dimension '{dim}' score <= 0.8",
                            actual=f"Dimension '{dim}' score is {raw_score:.2f}",
                            detail=f"Risk referencing '{dim}' correctly aligns with score."
                        ))
        
        if not findings:
             findings.append(CriticFinding(
                check_name="hallucinated_risk_check",
                severity="INFO",
                passed=True,
                expected="No hallucinated risks",
                actual="No hallucinated risks detected",
                detail="All risk factors align with low-scoring dimensions or no specific dimensions mentioned."
            ))
             
        return findings

    def _check_score_rationale(self, explanation_dict: dict) -> CriticFinding:
        # Default weights mapped conceptually
        # Weights >= 0.15: domain, financial, geography, experience
        major_dimensions = ["domain", "financial", "geography", "experience"]
        score_rationale = explanation_dict.get("score_rationale", {})
        
        missing_dims = [dim for dim in major_dimensions if not score_rationale.get(dim)]
        
        passed = len(missing_dims) == 0
        
        return CriticFinding(
            check_name="score_rationale_coverage",
            severity="INFO",
            passed=passed,
            expected="Score rationale should cover domain, financial, geography, experience",
            actual=f"Missing dimensions: {missing_dims}" if missing_dims else "All major dimensions covered",
            detail=f"Score rationale is missing entries for: {missing_dims}" if not passed else "Score rationale coverage is complete."
        )

    def _check_confidence_sanity(self, explanation_dict: dict, vendor_completeness: float) -> CriticFinding:
        actual_rec = explanation_dict.get("recommendation", "")
        
        if vendor_completeness < 40 and actual_rec in ["HIGH_MATCH", "MODERATE_MATCH"]:
            # Check if explanation mentions data limitations
            confidence_note = explanation_dict.get("confidence_note")
            summary = explanation_dict.get("executive_summary", "").lower()
            
            mentions_limitations = (
                confidence_note is not None 
                or "inferred" in summary 
                or "missing data" in summary 
                or "limited profile" in summary
                or "low confidence" in summary
            )
            
            passed = mentions_limitations
            
            return CriticFinding(
                check_name="confidence_sanity",
                severity="WARNING",
                passed=passed,
                expected="Explanation should mention data limitations when profile completeness < 40 and match is positive",
                actual="No data limitations mentioned" if not passed else "Limitations mentioned",
                detail="Profile completeness is < 40% but LLM gave a positive match without acknowledging data limitations." if not passed else "Data limitations acknowledged."
            )
            
        return CriticFinding(
            check_name="confidence_sanity",
            severity="INFO",
            passed=True,
            expected="N/A",
            actual="N/A",
            detail="Confidence sanity check passed or not applicable."
        )

# Singleton instance
critic_service = CriticService()
