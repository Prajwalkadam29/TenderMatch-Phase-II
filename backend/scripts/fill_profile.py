import httpx
import asyncio
import json

API_BASE = "http://localhost:8000"

async def fill_vendor_profile():
    email = "prajwal.kadam@gmail.com"
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
        if not token:
            print("No token received.")
            return
            
        print("Login successful! Got JWT token.")
        
        # 2. Create Vendor Profile Payload
        payload = {
            "identity": {
                "company_legal_name": "Kadam Infrastructure Solutions Ltd",
                "registration_type": "Private Limited Company",
                "year_of_incorporation": 2015,
                "pan_number": "ABCDE1234F",
                "gstin_list": [
                    {
                        "gstin": "27ABCDE1234F1Z5",
                        "state_code": "27",
                        "state_name": "Maharashtra",
                        "is_primary": True
                    }
                ],
                "cin_llpin": "U45201PN2015PTC154212",
                "udyam_registration_number": "UDYAM-MH-26-0012345",
                "msme_category": "Small",
                "nsic_registration_number": "NSIC/PNE/2018/899",
                "gem_seller_id": "GEM/2019/SELLER/881",
                "dpiit_recognition_number": None
            },
            "geography": {
                "registered_states": ["Maharashtra"],
                "operational_states": ["Maharashtra", "Gujarat", "Karnataka"],
                "operational_districts": ["Pune", "Mumbai", "Surat", "Bengaluru"],
                "willing_to_operate_in_new_states": True,
                "preferred_states": ["Goa", "Madhya Pradesh"]
            },
            "business_domain": {
                "primary_domains": ["Construction", "Smart City Projects", "IT Infrastructure"],
                "sub_domains": ["Road Construction", "CCTV Surveillance", "Networking"],
                "capability_description_freetext": "Leading provider of civil infrastructure, smart city integrations including CCTV surveillance, and specialized IT infrastructure deployment for government sectors.",
                "cpv_nic_codes": ["45200000", "45230000", "32323500"],
                "preferred_tender_categories": ["Works", "Services"],
                "tender_value_range_preference": {
                    "min_inr": 1000000,
                    "max_inr": 500000000,
                    "currency": "INR"
                }
            },
            "financials": {
                "avg_annual_turnover_inr": 125000000.0,
                "turnover_by_year": [
                    {"financial_year": "2022-23", "turnover_inr": 110000000.0},
                    {"financial_year": "2023-24", "turnover_inr": 140000000.0}
                ],
                "net_worth_status": "Positive",
                "solvency_certificate_available": True,
                "solvency_bank_name": "HDFC Bank",
                "esi_registration_number": "ESI123456789",
                "pf_registration_number": "PF987654321"
            },
            "past_project_experience": {
                "projects": [
                    {
                        "project_title": "Pune Smart City CCTV Network",
                        "work_type": "IT Services",
                        "contract_value_inr": 45000000.0,
                        "client_name": "Pune Municipal Corporation",
                        "client_type": "Municipal Body",
                        "year_of_completion": 2023
                    },
                    {
                        "project_title": "State Highway Expansion - Phase 1",
                        "work_type": "Civil Works",
                        "contract_value_inr": 120000000.0,
                        "client_name": "Maharashtra PWD",
                        "client_type": "State Government",
                        "year_of_completion": 2021
                    }
                ],
                "largest_single_project_value_inr": 120000000.0
            },
            "certifications": {
                "iso_certifications": [
                    {"standard": "ISO 9001:2015", "valid_until": "2026-12-31"},
                    {"standard": "ISO 27001:2013", "valid_until": "2025-06-30"}
                ],
                "domain_licenses": [],
                "bis_nabl_accreditations": [],
                "mnre_empanelment": True,
                "other_certifications": []
            },
            "compliance": {
                "blacklisted_or_debarred": False,
                "active_litigation": False,
                "gst_returns_compliant": True,
                "epf_esic_compliant": True
            },
            "notification_preferences": {
                "preferred_channels": ["email"],
                "email": "prajwal.kadam@gmail.com",
                "whatsapp_number": "+919876543210",
                "sms_number": "+919876543210",
                "minimum_match_score_threshold": 0.65,
                "notification_frequency": "Daily",
                "excluded_portals": ["Defence"],
                "min_days_to_deadline": 10
            }
        }
        
        # 3. Submit Vendor Profile
        print("Submitting comprehensive vendor profile...")
        response = await client.post(
            f"{API_BASE}/vendor-profiles/",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )
        
        if response.status_code == 201:
            print("Successfully created vendor profile!")
            data = response.json()
            print(f"Profile ID: {data['id']}")
            print(f"Completeness Score: {data['profile_completeness_pct']}%")
            
            # Print completeness details safely
            for detail in data.get('completeness_details', []):
                if not detail.get('is_filled'):
                    print(f"Missing field: {detail.get('label')}")
        else:
            print("Failed to create vendor profile:", response.status_code, response.text)

if __name__ == "__main__":
    asyncio.run(fill_vendor_profile())
