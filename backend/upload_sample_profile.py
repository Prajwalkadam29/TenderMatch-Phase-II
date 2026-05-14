import requests
import json

# --- Configuration ---
BASE_URL = "http://localhost:8000"
EMAIL = "prajwal.kadam@gmail.com"
PASSWORD = "user123"

def upload_sample():
    # 1. Login to get the Token
    print(f"Logging in as {EMAIL}...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    
    if login_res.status_code != 200:
        print("Login failed! Check credentials.")
        return
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Define Sample Vendor Profile Data
    sample_profile = {
        "identity": {
            "company_legal_name": "Nexus Global Solutions",
            "registration_type": "Pvt Ltd",
            "year_of_incorporation": 2015,
            "pan_number": "PQRTS9876X",
            "gstin_list": [
                {"gstin": "27PQRTS9876X1Z2", "state_code": "27", "state_name": "Maharashtra", "is_primary": True}
            ],
            "cin_llpin": "U72200MH2015PTC999999",
            "msme_category": "Small"
        },
        "geography": {
            "registered_office_address": {
                "street": "MG Road",
                "city": "Pune",
                "district": "Pune",
                "state": "Maharashtra",
                "state_code": "27",
                "pincode": "411001"
            },
            "registered_states": ["Maharashtra"],
            "operational_states": ["Maharashtra", "Karnataka", "Telangana"],
            "willing_to_operate_in_new_states": True
        },
        "business_domain": {
            "primary_domains": ["IT Consulting", "Software Development"],
            "sub_domains": ["Cloud Infrastructure", "Cyber Security"],
            "capability_description_freetext": "High-tech software firm specializing in government digital transformation.",
            "tender_value_range_preference": {"min_inr": 500000, "max_inr": 20000000, "currency": "INR"}
        },
        "financials": {
            "avg_annual_turnover_inr": 50000000,
            "net_worth_status": "Positive",
            "solvency_certificate_available": True
        },
        "past_project_experience": {
            "projects": [
                {
                    "project_id": "PRJ-999",
                    "project_title": "Smart City Portal",
                    "work_type": "Software Services",
                    "contract_value_inr": 15000000,
                    "client_name": "Pune Municipal Corp",
                    "client_type": "State Government",
                    "location_state": "Maharashtra",
                    "year_of_completion": 2023,
                    "completion_certificate_available": True
                }
            ],
            "largest_single_project_value_inr": 15000000
        },
        "certifications": {
            "iso_certifications": [
                {"standard": "ISO 27001", "category": "Security", "certifying_body": "TUV", "valid_until": "2026-12-31"}
            ]
        },
        "compliance": {
            "blacklisted_or_debarred": False,
            "gst_returns_compliant": True,
            "epf_esic_compliant": True
        },
        "notification_preferences": {
            "preferred_channels": ["email"],
            "email": EMAIL,
            "minimum_match_score_threshold": 0.80,
            "notification_frequency": "daily"
        }
    }

    # 3. Upload the Profile
    print("Uploading vendor profile...")
    profile_res = requests.post(
        f"{BASE_URL}/vendor-profiles/", 
        headers=headers, 
        json=sample_profile
    )

    if profile_res.status_code in [200, 201]:
        print("Profile uploaded successfully!")
        print(f"Profile ID: {profile_res.json()['id']}")
    else:
        print(f"Failed to upload: {profile_res.status_code}")
        print(profile_res.text)

if __name__ == "__main__":
    upload_sample()
