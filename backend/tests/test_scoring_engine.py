"""
test_scoring_engine.py
----------------------
Unit tests for Component 3: Weighted Scoring Engine.
"""

import pytest
from app.services.matching_service import WeightedScoringEngine

class TestWeightedScoringEngine:
    
    def test_score_domain(self):
        tender = {"domain": "Information Technology"}
        
        # Exact Match
        vendor_exact = {"business_domain": {"primary_domains": ["Information Technology"]}}
        assert WeightedScoringEngine.score_domain(vendor_exact, tender) == 1.0
        
        # Synonym Match
        vendor_synonym = {"business_domain": {"primary_domains": ["IT & Software"]}}
        assert WeightedScoringEngine.score_domain(vendor_synonym, tender) == 0.8
        
        # Partial Match
        vendor_partial = {"business_domain": {"primary_domains": ["Technology"]}}
        assert WeightedScoringEngine.score_domain(vendor_partial, tender) == 0.5
        
        # No Match
        vendor_no_match = {"business_domain": {"primary_domains": ["Construction"]}}
        assert WeightedScoringEngine.score_domain(vendor_no_match, tender) == 0.0

    def test_score_geography(self):
        tender = {"location_state": "Delhi"}
        
        # Registered
        vendor_reg = {"geography": {"registered_states": ["Delhi"]}}
        assert WeightedScoringEngine.score_geography(vendor_reg, tender) == 1.0
        
        # Operational
        vendor_op = {"geography": {"operational_states": ["Delhi"]}}
        assert WeightedScoringEngine.score_geography(vendor_op, tender) == 0.8
        
        # Willing
        vendor_willing = {"geography": {"willing_to_operate_in_new_states": True}}
        assert WeightedScoringEngine.score_geography(vendor_willing, tender) == 0.5
        
        # None
        vendor_none = {"geography": {"operational_states": ["Goa"], "willing_to_operate_in_new_states": False}}
        assert WeightedScoringEngine.score_geography(vendor_none, tender) == 0.0

    def test_score_financial(self):
        tender = {"estimated_value": 1000000}
        
        vendor_high = {"financials": {"avg_annual_turnover_inr": 3500000}} # ratio 3.5
        assert WeightedScoringEngine.score_financial(vendor_high, tender) == 1.0
        
        vendor_med = {"financials": {"avg_annual_turnover_inr": 2500000}} # ratio 2.5
        assert WeightedScoringEngine.score_financial(vendor_med, tender) == 0.9
        
        vendor_low = {"financials": {"avg_annual_turnover_inr": 1000000}} # ratio 1.0
        assert WeightedScoringEngine.score_financial(vendor_low, tender) == 0.8
        
        vendor_very_low = {"financials": {"avg_annual_turnover_inr": 600000}} # ratio 0.6
        assert WeightedScoringEngine.score_financial(vendor_very_low, tender) == 0.5

    def test_score_experience(self):
        tender = {"estimated_value": 5000000}
        
        vendor_exceeds = {"past_project_experience": {"projects": [{"contract_value_inr": 6000000}]}}
        assert WeightedScoringEngine.score_experience(vendor_exceeds, tender) == 1.0
        
        vendor_half = {"past_project_experience": {"projects": [{"contract_value_inr": 3000000}]}}
        assert WeightedScoringEngine.score_experience(vendor_half, tender) == 0.7
        
        vendor_small = {"past_project_experience": {"projects": [{"contract_value_inr": 1000000}]}}
        assert WeightedScoringEngine.score_experience(vendor_small, tender) == 0.4

    def test_score_certification(self):
        tender = {"mandatory_certifications": ["ISO 9001", "CMMI Level 3"], "optional_certifications": ["ISO 27001"]}
        # Total target certs = 3
        
        vendor = {
            "certifications": {
                "iso_certifications": [{"standard": "ISO 9001"}, {"standard": "ISO 27001"}],
                "domain_licenses": []
            }
        }
        # Vendor has 2 out of 3 = 0.666...
        score = WeightedScoringEngine.score_certification(vendor, tender)
        assert abs(score - 0.666) < 0.01
        
    def test_calculate_score(self):
        vendor = {
            "business_domain": {"primary_domains": ["Information Technology"]},  # Domain: 1.0 * 0.25 = 0.25
            "geography": {"registered_states": ["Delhi"]},                       # Geo: 1.0 * 0.15 = 0.15
            "financials": {"avg_annual_turnover_inr": 3000000},                  # Fin (ratio 3.0): 1.0 * 0.20 = 0.20
            "past_project_experience": {"projects": [{"contract_value_inr": 1500000}]}, # Exp (>val): 1.0 * 0.15 = 0.15
            "certifications": {"iso_certifications": [{"standard": "ISO 9001"}]}, # Certs (1/1): 1.0 * 0.10 = 0.10
            "profile_completeness_pct": 100                                       # Conf: 1.0 * 0.05 = 0.05
        }
        tender = {
            "domain": "Information Technology",
            "location_state": "Delhi",
            "estimated_value": 1000000,
            "mandatory_certifications": ["ISO 9001"]
        }
        
        semantic_score = 1.0 # Sem: 1.0 * 0.10 = 0.10
        
        res = WeightedScoringEngine.calculate_score(vendor, tender, semantic_score)
        
        # Total expected: 0.25 + 0.15 + 0.20 + 0.15 + 0.10 + 0.10 + 0.05 = 1.00 (100.0)
        assert res["final_score"] == 100.0
        assert "domain" in res["breakdown"]
        assert "semantic" in res["breakdown"]
