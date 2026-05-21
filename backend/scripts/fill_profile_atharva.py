import httpx
import asyncio
import json

API_BASE = "http://localhost:8000"

async def fill_vendor_profile_atharva():
    email = "atharva@gmail.com"
    password = "user@1234"
    
    # 1. Login
    print(f"Logging in as {email}...")
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": password}
        )
        
        if login_response.status_code != 200:
            print("Login failed!", login_response.status_code, login_response.text)
            return
            
        token = login_response.json().get("access_token")
        print("Login successful! Got JWT token.")
        
        # 2. Create Vendor Profile Payload (Medical/Healthcare)
        payload = {
            "identity": {
                "company_legal_name": "Atharva Medical Systems & Services Pvt Ltd",
                "registration_type": "Private Limited Company",
                "year_of_incorporation": 2018,
                "pan_number": "MEDIC8822G",
                "gstin_list": [
                    {
                        "gstin": "07MEDIC8822G1Z1",
                        "state_code": "07",
                        "state_name": "Delhi",
                        "is_primary": True
                    }
                ],
                "cin_llpin": "U85100DL2018PTC334512",
                "udyam_registration_number": "UDYAM-DL-01-0099881",
                "msme_category": "Micro",
                "nsic_registration_number": "NSIC/DEL/2020/442",
                "gem_seller_id": "GEM/2021/SELLER/9921",
                "dpiit_recognition_number": "DPIIT-MED-2022-001"
            },
            "geography": {
                "registered_states": ["Delhi"],
                "operational_states": ["Delhi", "Uttar Pradesh", "Haryana", "Rajasthan"],
                "operational_districts": ["Central Delhi", "Lucknow", "Gurgaon", "Jaipur"],
                "willing_to_operate_in_new_states": True,
                "preferred_states": ["Punjab", "Uttarakhand"]
            },
            "business_domain": {
                "primary_domains": ["Medical Devices", "Hospital Services", "Surgical Equipment Maintenance"],
                "sub_domains": ["MRI & CT Scan Maintenance", "Critical Care Equipment", "Patient Monitoring Systems"],
                "capability_description_freetext": "Premier medical technology provider specializing in the installation, maintenance, and supply of high-end diagnostic imaging systems and critical care life-support equipment for multi-specialty hospitals and government health departments.",
                "cpv_nic_codes": ["33100000", "33111000", "50421000"],
                "preferred_tender_categories": ["Goods", "Services"],
                "tender_value_range_preference": {
                    "min_inr": 500000,
                    "max_inr": 100000000,
                    "currency": "INR"
                }
            },
            "financials": {
                "avg_annual_turnover_inr": 25000000.0,
                "turnover_by_year": [
                    {"financial_year": "2022-23", "turnover_inr": 22000000.0},
                    {"financial_year": "2023-24", "turnover_inr": 28000000.0}
                ],
                "net_worth_status": "Positive",
                "solvency_certificate_available": True,
                "solvency_bank_name": "ICICI Bank",
                "esi_registration_number": "ESI8877665544",
                "pf_registration_number": "PF1122334455"
            },
            "past_project_experience": {
                "projects": [
                    {
                        "project_title": "AIIMS Delhi MRI Maintenance Contract",
                        "work_type": "Medical Services",
                        "contract_value_inr": 8500000.0,
                        "client_name": "AIIMS New Delhi",
                        "client_type": "Statutory Body",
                        "year_of_completion": 2023
                    },
                    {
                        "project_title": "UP Health Dept - ICU Ventilator Supply",
                        "work_type": "Supply of Goods",
                        "contract_value_inr": 15000000.0,
                        "client_name": "UP Medical Supplies Corporation",
                        "client_type": "State Government",
                        "year_of_completion": 2022
                    }
                ],
                "largest_single_project_value_inr": 15000000.0
            },
            "certifications": {
                "iso_certifications": [
                    {"standard": "ISO 13485:2016", "valid_until": "2027-01-20"},
                    {"standard": "ISO 9001:2015", "valid_until": "2026-05-15"}
                ],
                "domain_licenses": [
                    {"license_type": "AERB License for X-Ray/CT", "issuing_authority": "AERB"}
                ],
                "bis_nabl_accreditations": [
                    {"name": "NABL Accredited Calibration Lab", "scope": "Thermal & Optical"}
                ],
                "mnre_empanelment": False,
                "other_certifications": [
                    {"name": "CE Marking Compliance", "id": "CE-9921"}
                ]
            },
            "compliance": {
                "blacklisted_or_debarred": False,
                "active_litigation": False,
                "gst_returns_compliant": True,
                "epf_esic_compliant": True
            },
            "notification_preferences": {
                "preferred_channels": ["email", "whatsapp"],
                "email": "atharva@gmail.com",
                "whatsapp_number": "+918888877777",
                "sms_number": "+918888877777",
                "minimum_match_score_threshold": 0.7,
                "notification_frequency": "Instant",
                "excluded_portals": ["Civil Construction"],
                "min_days_to_deadline": 7
            }
        }
        
        # 3. Submit Vendor Profile
        print("Submitting Atharva's medical vendor profile...")
        response = await client.post(
            f"{API_BASE}/vendor-profiles/",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )
        
        if response.status_code == 201:
            print("Successfully created vendor profile for Atharva!")
            data = response.json()
            print(f"Profile ID: {data['id']}")
            print(f"Completeness Score: {data['profile_completeness_pct']}%")
        else:
            print("Failed to create vendor profile:", response.status_code, response.text)

if __name__ == "__main__":
    asyncio.run(fill_vendor_profile_atharva())
