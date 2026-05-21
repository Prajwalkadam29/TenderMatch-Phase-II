import json
import os
import argparse
from datetime import datetime, timezone

def build_profile(
    name, reg_type, pan, gstin, yr, states, op_states, 
    domains, sub_domains, cap_text, to, to_list, 
    past_projs, isocs, domlics, msme_cat
):
    gstin_entry = {
        "gstin": gstin,
        "state_code": gstin[:2],
        "state_name": states[0],
        "is_primary": True
    }
    iso_entries = [{"standard": c} for c in isocs]
    dom_entries = [{"license_type": c} for c in domlics]
    proj_entries = []
    for p in past_projs:
        proj_entries.append({
            "project_title": p["project_title"],
            "work_type": p["work_type"],
            "contract_value_inr": p["contract_value_inr"],
            "client_name": p["client_name"],
            "client_type": p["client_type"],
            "year_of_completion": p["year_of_completion"]
        })
        
    return {
        "identity": {
            "company_legal_name": name,
            "registration_type": reg_type,
            "year_of_incorporation": yr,
            "pan_number": pan,
            "gstin_list": [gstin_entry],
            "msme_category": msme_cat
        },
        "geography": {
            "registered_states": states,
            "operational_states": op_states
        },
        "business_domain": {
            "primary_domains": domains,
            "sub_domains": sub_domains,
            "capability_description_freetext": cap_text
        },
        "financials": {
            "avg_annual_turnover_inr": to,
            "turnover_by_year": to_list,
            "net_worth_status": "Positive",
            "solvency_certificate_available": True
        },
        "past_project_experience": {
            "projects": proj_entries
        },
        "certifications": {
            "iso_certifications": iso_entries,
            "domain_licenses": dom_entries
        },
        "compliance": {
            "blacklisted_or_debarred": False
        },
        "notification_preferences": {
            "email": "test@example.com",
            "preferred_channels": ["email"],
            "minimum_match_score_threshold": 0.65
        }
    }

def generate_vendors():
    SCRIPT_VERSION = "1.0.0"
    
    vendors = [
        {
            "vendor_id": "V-EVAL-001",
            "business_name": "TechBuild Infrastructure Pvt Ltd",
            "profile_completeness_pct": 95.0,
            "profile_data": build_profile(
                "TechBuild Infrastructure Pvt Ltd", "Pvt Ltd", "ABCDE1234F", "27ABCDE1234F1Z5", 2012,
                ["Maharashtra"], ["Maharashtra", "Gujarat", "Karnataka", "Delhi"],
                ["Civil & Construction"], ["Building Construction", "Civil Works"],
                "Leading infrastructure development company with over a decade of experience.",
                450_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 480000000}],
                [
                    {
                        "project_title": "Navi Mumbai Commercial Complex",
                        "client_name": "CIDCO",
                        "client_type": "Government",
                        "contract_value_inr": 200_000_000,
                        "year_of_completion": 2023,
                        "work_type": "Building Construction"
                    }
                ],
                ["ISO 9001:2015"], ["CPWD empanelment"], None
            )
        },
        {
            "vendor_id": "V-EVAL-002",
            "business_name": "SolarTech Renewables LLP",
            "profile_completeness_pct": 88.0,
            "profile_data": build_profile(
                "SolarTech Renewables LLP", "LLP", "ABCDE5678F", "24ABCDE5678F1Z5", 2016,
                ["Gujarat"], ["Gujarat", "Rajasthan", "Madhya Pradesh"],
                ["Renewable Energy"], ["Solar Power", "Rooftop Solar"],
                "Specialist in solar power installations.",
                180_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 200000000}],
                [
                    {
                        "project_title": "Gandhinagar Solar Rooftop",
                        "client_name": "GUVNL",
                        "client_type": "Government",
                        "contract_value_inr": 80_000_000,
                        "year_of_completion": 2023,
                        "work_type": "Solar Power"
                    }
                ],
                ["ISO 9001:2015"], ["MNRE empanelment", "BIS IS 14286"], "Medium"
            )
        },
        {
            "vendor_id": "V-EVAL-003",
            "business_name": "MediSupply Solutions Pvt Ltd",
            "profile_completeness_pct": 72.0,
            "profile_data": build_profile(
                "MediSupply Solutions Pvt Ltd", "Pvt Ltd", "ABCDE9012F", "07ABCDE9012F1Z5", 2018,
                ["Delhi"], ["Delhi", "Haryana", "UP"],
                ["Healthcare & Medical"], ["Medical Equipment", "Supplies"],
                "Provider of quality medical equipment.",
                80_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 90000000}],
                [],
                ["ISO 13485"], ["CDSCO registration"], "Small"
            )
        },
        {
            "vendor_id": "V-EVAL-004",
            "business_name": "DataCore IT Services Pvt Ltd",
            "profile_completeness_pct": 90.0,
            "profile_data": build_profile(
                "DataCore IT Services Pvt Ltd", "Pvt Ltd", "ABCDE3456F", "29ABCDE3456F1Z5", 2015,
                ["Karnataka"], ["Karnataka", "Delhi", "Maharashtra"],
                ["IT & Software"], ["ERP Implementation", "Cloud Migration"],
                "Specialized in delivering robust e-governance solutions.",
                220_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 250000000}],
                [
                    {
                        "project_title": "Karnataka e-Governance Portal",
                        "client_name": "State Govt of Karnataka",
                        "client_type": "State Government",
                        "contract_value_inr": 120_000_000,
                        "year_of_completion": 2023,
                        "work_type": "Software Development"
                    }
                ],
                ["ISO 27001", "ISO 9001:2015"], ["CMMI Level 3", "GEM registration"], None
            )
        },
        {
            "vendor_id": "V-EVAL-005",
            "business_name": "AquaFlow Engineering Ltd",
            "profile_completeness_pct": 85.0,
            "profile_data": build_profile(
                "AquaFlow Engineering Ltd", "Ltd", "ABCDE7890F", "09ABCDE7890F1Z5", 2010,
                ["Uttar Pradesh"], ["UP", "MP", "Bihar", "Jharkhand"],
                ["Water & Sanitation"], ["Water Treatment", "Sewage Pipeline"],
                "Leading contractor for AMRUT and state water board projects.",
                350_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 380000000}],
                [
                    {
                        "project_title": "Lucknow STP Upgrade",
                        "client_name": "UP Jal Nigam",
                        "client_type": "State Government",
                        "contract_value_inr": 250_000_000,
                        "year_of_completion": 2023,
                        "work_type": "Water Treatment"
                    }
                ],
                ["ISO 9001:2015"], ["BIS"], None
            )
        },
        {
            "vendor_id": "V-EVAL-006",
            "business_name": "PowerGrid Electricals Pvt Ltd",
            "profile_completeness_pct": 45.0,
            "profile_data": build_profile(
                "PowerGrid Electricals Pvt Ltd", "Pvt Ltd", "ABCDE2468F", "33ABCDE2468F1Z5", 2017,
                ["Tamil Nadu"], ["Tamil Nadu"],
                ["Electrical & Instrumentation"], ["Substation", "HT/LT cabling"],
                "Electrical contractor with CEA license.",
                120_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 120000000}],
                [], [], ["CEA license"], "Small"
            )
        },
        {
            "vendor_id": "V-EVAL-007",
            "business_name": "Highway Constructors Ltd",
            "profile_completeness_pct": 92.0,
            "profile_data": build_profile(
                "Highway Constructors Ltd", "Ltd", "ABCDE1357F", "06ABCDE1357F1Z5", 2005,
                ["Haryana"], ["Haryana", "Punjab", "Delhi", "UP", "Rajasthan"],
                ["Roads & Highways"], ["4-lane highway expansion"],
                "Highly specialized in executing large NHAI and state highway projects.",
                850_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 900000000}],
                [
                    {
                        "project_title": "Delhi-Meerut Expressway Package 3",
                        "client_name": "NHAI",
                        "client_type": "Central Government",
                        "contract_value_inr": 1_200_000_000,
                        "year_of_completion": 2022,
                        "work_type": "Expressway paving"
                    }
                ],
                ["ISO 9001:2015"], ["NHAI empanelment", "IRC compliance"], None
            )
        },
        {
            "vendor_id": "V-EVAL-008",
            "business_name": "GreenBuild Multi-Domain Ltd",
            "profile_completeness_pct": 78.0,
            "profile_data": build_profile(
                "GreenBuild Multi-Domain Ltd", "Ltd", "ABCDE3692F", "32ABCDE3692F1Z5", 2014,
                ["Kerala"], ["Kerala", "Tamil Nadu", "Karnataka"],
                ["Civil & Construction", "Renewable Energy"], ["Building Construction", "Solar Power"],
                "Unique multi-domain capabilities.",
                280_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 300000000}],
                [
                    {
                        "project_title": "Kochi Smart City Green Hub",
                        "client_name": "Kochi Smart City",
                        "client_type": "Government",
                        "contract_value_inr": 150_000_000,
                        "year_of_completion": 2023,
                        "work_type": "Building Construction"
                    }
                ],
                ["ISO 9001:2015"], ["CPWD empanelment"], None
            )
        },
        {
            "vendor_id": "V-EVAL-009",
            "business_name": "StartupTech Solutions",
            "profile_completeness_pct": 38.0,
            "profile_data": build_profile(
                "StartupTech Solutions", "Pvt Ltd", "ABCDE1472F", "36ABCDE1472F1Z5", 2022,
                ["Telangana"], ["Telangana"],
                ["IT & Software"], ["Software Development"],
                "New software development startup.",
                12_000_000,
                [{"financial_year": "2023-24", "turnover_inr": 12000000}],
                [], [], [], "Micro"
            )
        },
        {
            "vendor_id": "V-EVAL-010",
            "business_name": "Consultancy Partners LLP",
            "profile_completeness_pct": 65.0,
            "profile_data": build_profile(
                "Consultancy Partners LLP", "LLP", "ABCDE2583F", "07ABCDE2583F1Z5", 2011,
                ["Delhi"], ["Delhi", "Haryana"],
                ["Consultancy & Advisory"], ["Financial Audit", "Project Management"],
                "Boutique advisory firm providing highly specialized financial services.",
                8_500_000,
                [{"financial_year": "2023-24", "turnover_inr": 9000000}],
                [
                    {
                        "project_title": "Delhi Jal Board Process Audit",
                        "client_name": "Delhi Jal Board",
                        "client_type": "Municipal Body",
                        "contract_value_inr": 3_000_000,
                        "year_of_completion": 2022,
                        "work_type": "Financial Audit"
                    }
                ],
                ["ISO 9001:2015"], ["ICAI membership"], "Micro"
            )
        }
    ]
    
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "script_version": SCRIPT_VERSION,
            "total_vendors": len(vendors)
        },
        "vendors": vendors
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 10 synthetic vendors for evaluation.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing dataset")
    args = parser.parse_args()
    
    output_path = os.path.join(os.path.dirname(__file__), "vendors_10.json")
    
    if os.path.exists(output_path) and not args.force:
        print(f"Error: {output_path} already exists. Use --force to overwrite.")
        exit(1)
        
    data = generate_vendors()
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"Successfully generated {len(data['vendors'])} vendors at {output_path}")
