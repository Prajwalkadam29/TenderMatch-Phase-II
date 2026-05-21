import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres
from app.services.matching_service import orchestrate_match

async def main():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    vendors = manifest.get("vendor_profiles", [])
    tenders = [t for t in manifest.get("tenders", []) if t.get("status") == "completed"]
    
    vendor = vendors[0]
    tender = tenders[0]
    
    print(f"Testing match for vendor {vendor['profile_id']} and tender {tender['mongo_id']}")
    
    try:
        res = await orchestrate_match(
            vendor_profile_id=vendor["profile_id"],
            tender_mongo_id=tender["mongo_id"]
        )
        print("MATCH RESULT RETURNED:")
        print(list(res.keys()))
        
        # Check DB
        in_db = await db.match_results.find_one({"match_result._meta.match_id": res.get("match_result", {}).get("_meta", {}).get("match_id")})
        print("IN DB (nested):", in_db is not None)
        
        in_db2 = await db.match_results.find_one({"tender_id": tender["mongo_id"]})
        print("IN DB (root):", in_db2 is not None)
    except Exception as e:
        print("ERROR:", e)
        
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
