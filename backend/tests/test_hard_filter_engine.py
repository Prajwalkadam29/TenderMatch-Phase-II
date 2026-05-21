"""
test_hard_filter_engine.py
--------------------------
Unit tests for Component 2: Hard Filter Engine.
"""

import pytest
from app.services.matching_service import HardFilterEngine

class TestHardFilterEngine:
    
    def test_check_blacklist(self):
        # Vendor blacklisted
        vendor = {"compliance": {"blacklisted_or_debarred": True}}
        res = HardFilterEngine.check_blacklist(vendor, {})
        assert not res["passed"]
        
        # Vendor clean
        vendor = {"compliance": {"blacklisted_or_debarred": False}}
        res = HardFilterEngine.check_blacklist(vendor, {})
        assert res["passed"]

    def test_check_domain_match(self):
        tender = {"domain": "Information Technology"}
        
        # Exact Match
        vendor_exact = {"business_domain": {"primary_domains": ["Information Technology"]}}
        assert HardFilterEngine.check_domain_match(vendor_exact, tender)["passed"]
        
        # Synonym Match
        vendor_synonym = {"business_domain": {"primary_domains": ["IT & Software"]}}
        assert HardFilterEngine.check_domain_match(vendor_synonym, tender)["passed"]
        
        # No Match
        vendor_no_match = {"business_domain": {"primary_domains": ["Construction"]}}
        assert not HardFilterEngine.check_domain_match(vendor_no_match, tender)["passed"]
        
        # Partial Match
        tender_partial = {"domain": "Civil Construction"}
        vendor_partial = {"business_domain": {"primary_domains": ["Construction"]}}
        assert HardFilterEngine.check_domain_match(vendor_partial, tender_partial)["passed"]

    def test_check_geographic_eligibility(self):
        tender = {"location_state": "Maharashtra"}
        
        # Exact State Match
        vendor_exact = {"geography": {"operational_states": ["Maharashtra", "Goa"]}}
        assert HardFilterEngine.check_geographic_eligibility(vendor_exact, tender)["passed"]
        
        # Pan India Vendor
        vendor_pan = {"geography": {"registered_states": ["Pan India"]}}
        assert HardFilterEngine.check_geographic_eligibility(vendor_pan, tender)["passed"]
        
        # Willing to operate
        vendor_willing = {"geography": {"operational_states": ["Delhi"], "willing_to_operate_in_new_states": True}}
        assert HardFilterEngine.check_geographic_eligibility(vendor_willing, tender)["passed"]
        
        # Fails
        vendor_fails = {"geography": {"operational_states": ["Delhi"], "willing_to_operate_in_new_states": False}}
        assert not HardFilterEngine.check_geographic_eligibility(vendor_fails, tender)["passed"]

    def test_check_financial_threshold(self):
        tender = {"min_avg_turnover": 5000000}
        
        # Exceeds
        vendor_exceeds = {"financials": {"avg_annual_turnover_inr": 6000000}}
        assert HardFilterEngine.check_financial_threshold(vendor_exceeds, tender)["passed"]
        
        # Exact
        vendor_exact = {"financials": {"avg_annual_turnover_inr": 5000000}}
        assert HardFilterEngine.check_financial_threshold(vendor_exact, tender)["passed"]
        
        # Fails
        vendor_fails = {"financials": {"avg_annual_turnover_inr": 4000000}}
        assert not HardFilterEngine.check_financial_threshold(vendor_fails, tender)["passed"]

    def test_check_mandatory_certifications(self):
        tender = {"mandatory_certifications": ["ISO 9001", "CMMI Level 3"]}
        
        # Vendor has all
        vendor_has_all = {
            "certifications": {
                "iso_certifications": [{"standard": "ISO 9001"}],
                "domain_licenses": [{"license_type": "CMMI Level 3"}]
            }
        }
        assert HardFilterEngine.check_mandatory_certifications(vendor_has_all, tender)["passed"]
        
        # Vendor missing one
        vendor_missing = {
            "certifications": {
                "iso_certifications": [{"standard": "ISO 9001"}]
            }
        }
        assert not HardFilterEngine.check_mandatory_certifications(vendor_missing, tender)["passed"]
        
        # Flat list vendor (fallback structure)
        vendor_flat = {"certifications": ["ISO 9001", "CMMI Level 3"]}
        assert HardFilterEngine.check_mandatory_certifications(vendor_flat, tender)["passed"]
        
    def test_evaluate_all(self):
        vendor = {
            "compliance": {"blacklisted_or_debarred": False},
            "business_domain": {"primary_domains": ["IT"]},
            "geography": {"operational_states": ["Pan India"]},
            "financials": {"avg_annual_turnover_inr": 10000000},
            "certifications": {"iso_certifications": [{"standard": "ISO 27001"}]}
        }
        tender = {
            "domain": "Information Technology",
            "location_state": "Delhi",
            "min_avg_turnover": 5000000,
            "mandatory_certifications": ["ISO 27001"]
        }
        
        res = HardFilterEngine.evaluate(vendor, tender)
        assert res["overall_pass"]
        assert res["disqualification_reason"] is None
        assert len(res["check_results"]) == 5
