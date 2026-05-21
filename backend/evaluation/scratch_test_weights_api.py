import asyncio
import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres

async def main():
    await init_postgres()
    
    manifest_path = "evaluation/data/ingestion_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    token = manifest.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
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
    
    # We use TestClient as a context manager to run lifespan events
    with TestClient(app) as client:
        r1 = client.get(f"/match/weights/{v1_id}", headers=headers)
        print("\n--- V-EVAL-001 API Response ---")
        print(f"Status: {r1.status_code}")
        try:
            print(json.dumps(r1.json(), indent=2))
        except:
            print(r1.text)
            
        r4 = client.get(f"/match/weights/{v4_id}", headers=headers)
        print("\n--- V-EVAL-004 API Response ---")
        print(f"Status: {r4.status_code}")
        try:
            print(json.dumps(r4.json(), indent=2))
        except:
            print(r4.text)
            
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
