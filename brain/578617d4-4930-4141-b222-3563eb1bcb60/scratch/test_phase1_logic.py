import requests
import time

BASE_URL = "http://localhost:8000"

def setup_test_data(email, password, org_name):
    print(f"\nSetting up data for {email}...")
    # 1. Register
    reg_data = {
        "email": email,
        "password": password,
        "name": "User " + email,
        "role": "ADMIN1",
        "org_name": org_name,
        "org_industry": "Test"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    assert resp.status_code == 201
    auth = resp.json()
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a Vendor Profile
    profile_data = {
        "identity": {
            "legal_name": "Vendor " + org_name,
            "gstin": "27AAAAA0000A1Z5",
            "pan": "ABCDE1234F"
        },
        "geography": {
            "headquarters_city": "Mumbai",
            "headquarters_state": "Maharashtra",
            "operational_states": ["Maharashtra"]
        },
        "business_domain": {
            "primary_domain": "Tech",
            "capability_description_freetext": "Test capabilities"
        }
    }
    resp = requests.post(f"{BASE_URL}/vendor-profiles/", json=profile_data, headers=headers)
    assert resp.status_code == 201
    vendor = resp.json()
    return headers, vendor["vendor_id"]

def test_tenant_isolation():
    print("\n[3] Testing Tenant Isolation...")
    # Create two different orgs
    h1, v1 = setup_test_data(f"user1_{int(time.time())}@a.com", "Pass123!", "Org A")
    h2, v2 = setup_test_data(f"user2_{int(time.time())}@b.com", "Pass123!", "Org B")
    
    # User 1 tries to match against User 2's vendor
    tender = {
        "tender_id": "T-TEST",
        "domain": "Tech",
        "estimated_value": 100000,
        "location_state": "Maharashtra"
    }
    
    print(f"User 1 ({v1}) matching against User 2's vendor ({v2})...")
    payload = {"vendor_id": v2, "tender": tender}
    resp = requests.post(f"{BASE_URL}/match/structured/", json=payload, headers=h1)
    
    print(f"Isolation Result Status: {resp.status_code}")
    # Should be 404 because the vendor is not found within User 1's org
    assert resp.status_code == 404
    print("✅ Tenant Isolation Verified (User 1 cannot see User 2's vendor)")

def test_completeness_boost():
    print("\n[4] Testing Completeness Boost Logic...")
    h, v_id = setup_test_data(f"user_comp_{int(time.time())}@c.com", "Pass123!", "Org C")
    
    tender = {
        "tender_id": "T-COMP",
        "domain": "Tech",
        "estimated_value": 100000,
        "location_state": "Maharashtra"
    }
    
    payload = {"vendor_id": v_id, "tender": tender}
    resp = requests.post(f"{BASE_URL}/match/structured/", json=payload, headers=h)
    assert resp.status_code == 200
    res = resp.json()
    
    final_score = res["match_result"]["weighted_score"]["final_score"]
    print(f"Final Score: {final_score}")
    # The new logic is additive boost. 
    # Previously, 50% completeness would have HALVED the score.
    # Now it should be > 0.5 if the base score is high.
    assert final_score > 0.5 
    print("✅ Completeness Logic Verified (No score collapse)")

if __name__ == "__main__":
    test_tenant_isolation()
    test_completeness_boost()
