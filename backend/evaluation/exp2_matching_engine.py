import asyncio
import os
import sys
import json
from datetime import datetime

# Add the backend directory to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres
from app.services.matching_service import orchestrate_match

async def run_all_matches():
    await init_postgres()
    await connect_to_mongo()
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    tenders = [t for t in manifest.get("tenders", []) if t.get("status") == "completed"]
    vendors = manifest.get("vendor_profiles", [])
    
    print(f"Generating matches for {len(vendors)} vendors against {len(tenders)} tenders...")
    print(f"Total pairs: {len(vendors) * len(tenders)}")
    
    total = len(vendors) * len(tenders)
    count = 0
    
    for vendor in vendors:
        vendor_id = vendor["profile_id"]  # the Postgres UUID
        for tender in tenders:
            tender_mongo_id = tender["mongo_id"]  # the mongo ObjectId string
            
            try:
                await orchestrate_match(
                    vendor_profile_id=vendor_id,
                    tender_mongo_id=tender_mongo_id
                )
            except Exception as e:
                print(f"Failed to match {vendor_id} against {tender_mongo_id}: {e}")
            
            count += 1
            if count % 10 == 0:
                print(f"Completed {count}/{total} matches...")
                
    await close_postgres()
    await close_mongo_connection()
    print("All matches generated and saved to MongoDB 'match_results' collection.")

if __name__ == "__main__":
    asyncio.run(run_all_matches())
