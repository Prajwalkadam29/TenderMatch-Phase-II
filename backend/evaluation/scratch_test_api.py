import json
import httpx
import asyncio

async def main():
    manifest_path = "evaluation/data/ingestion_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    profiles = manifest.get("vendor_profiles", [])
    v1_id = None
    v4_id = None
    
    for p in profiles:
        if p["vendor_id"] == "V-EVAL-001":
            v1_id = p["profile_id"]
        elif p["vendor_id"] == "V-EVAL-004":
            v4_id = p["profile_id"]
            
    print(f"V-EVAL-001 profile_id: {v1_id}")
    print(f"V-EVAL-004 profile_id: {v4_id}")
    
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        login_data = {"email": "eval3@tendermatch-research.internal", "password": "EvalSecure2026!"}
        login_resp = await client.post("/auth/login", json=login_data)
        if login_resp.status_code != 200:
            print("Login failed:", login_resp.text)
            return
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        r1 = await client.get(f"/match/weights/{v1_id}", headers=headers)
        print("\n--- V-EVAL-001 API Response ---")
        print(f"Status: {r1.status_code}")
        try:
            print(json.dumps(r1.json(), indent=2))
        except:
            print(r1.text)
            
        r4 = await client.get(f"/match/weights/{v4_id}", headers=headers)
        print("\n--- V-EVAL-004 API Response ---")
        print(f"Status: {r4.status_code}")
        try:
            print(json.dumps(r4.json(), indent=2))
        except:
            print(r4.text)

if __name__ == "__main__":
    asyncio.run(main())
