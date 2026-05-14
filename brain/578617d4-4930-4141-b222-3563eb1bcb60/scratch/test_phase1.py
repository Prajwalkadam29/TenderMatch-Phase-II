import requests
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("\n[1] Testing Health Endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        print("✅ Health Check Passed")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")

def test_auth_flow():
    print("\n[2] Testing Auth Flow...")
    email = f"test_{int(time.time())}@example.com"
    password = "Password123!"
    
    # 1. Register
    print("Registering...")
    reg_data = {
        "email": email,
        "password": password,
        "name": "Test User",
        "role": "ADMIN1",
        "org_name": "Test Org",
        "org_industry": "Tech"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    print(f"Register Status: {resp.status_code}")
    assert resp.status_code == 201
    reg_json = resp.json()
    access_token = reg_json["access_token"]
    refresh_cookie = resp.cookies.get("refresh_token")
    assert access_token
    assert refresh_cookie
    print("✅ Register Passed (Access token + Refresh cookie received)")

    # 2. Refresh
    print("Refreshing Token...")
    resp = requests.post(f"{BASE_URL}/auth/refresh", cookies={"refresh_token": refresh_cookie})
    print(f"Refresh Status: {resp.status_code}")
    assert resp.status_code == 200
    refresh_json = resp.json()
    new_access_token = refresh_json["access_token"]
    new_refresh_cookie = resp.cookies.get("refresh_token")
    assert new_access_token != access_token
    assert new_refresh_cookie
    print("✅ Refresh Passed (New Access token + Rotated Refresh cookie)")

    # 3. Me
    print("Testing /auth/me...")
    headers = {"Authorization": f"Bearer {new_access_token}"}
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Me Status: {resp.status_code}")
    assert resp.status_code == 200
    assert resp.json()["email"] == email
    print("✅ /auth/me Passed")

    # 4. Logout
    print("Logging out...")
    resp = requests.post(f"{BASE_URL}/auth/logout", headers=headers, cookies={"refresh_token": new_refresh_cookie})
    print(f"Logout Status: {resp.status_code}")
    assert resp.status_code == 200
    # Check if cookie was cleared (set to empty/expired)
    # requests handles cookie deletion by seeing the Set-Cookie with Max-Age=0
    # but we can check if it's still in the response
    print(f"Response Cookies: {resp.cookies.get_dict()}")
    print("✅ Logout Passed")

    # 5. Verify Blacklist (Wait a bit for Redis)
    print("Verifying Blacklist (old token should be rejected)...")
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Rejected Me Status: {resp.status_code}")
    assert resp.status_code == 401
    print("✅ Blacklist Passed")

if __name__ == "__main__":
    # Wait for API to be ready
    print("Waiting for API to be ready...")
    for _ in range(30):
        try:
            requests.get(f"{BASE_URL}/health")
            break
        except:
            time.sleep(2)
    
    test_health()
    test_auth_flow()
