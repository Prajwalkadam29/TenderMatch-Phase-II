import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from app.services.weight_resolver import WeightResolver

async def main():
    await init_postgres()
    
    manifest_path = "evaluation/data/ingestion_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    profiles = manifest.get("vendor_profiles", [])
    org_id = "6806e04d-30af-4f53-bcb5-6ea4de2defbc" # The eval org
    v1_id = None
    v4_id = None
    
    for p in profiles:
        if p["vendor_id"] == "V-EVAL-001":
            v1_id = p["profile_id"]
        elif p["vendor_id"] == "V-EVAL-004":
            v4_id = p["profile_id"]
            
    print(f"V-EVAL-001 profile_id: {v1_id}")
    print(f"V-EVAL-004 profile_id: {v4_id}")
    
    async with get_pg_session() as session:
        w1 = await WeightResolver.get_weights(session, v1_id, org_id)
        print("\n--- V-EVAL-001 Resolved Weights ---")
        print(json.dumps(w1, indent=2))
        
        w4 = await WeightResolver.get_weights(session, v4_id, org_id)
        print("\n--- V-EVAL-004 Resolved Weights ---")
        print(json.dumps(w4, indent=2))
            
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
