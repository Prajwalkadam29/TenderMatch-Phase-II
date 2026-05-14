import requests

BASE_URL = "http://localhost:8000"
EMAIL = "prajwal.kadam@gmail.com"
PASSWORD = "user123"

def check_profiles():
    # 1. Login
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Profiles
    res = requests.get(f"{BASE_URL}/vendor-profiles/", headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Body: {res.json()}")

if __name__ == "__main__":
    check_profiles()
