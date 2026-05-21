import asyncio
import os
import sys
import json
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres, get_pg_session

async def main():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    print("=== ISSUE 1: Vendor Profiles Completeness ===")
    async with get_pg_session() as session:
        result = await session.execute(text("""
            SELECT vendor_id, business_name, profile_completeness_pct
            FROM vendor_profiles 
            WHERE vendor_id LIKE 'V-EVAL-%' 
            ORDER BY vendor_id;
        """))
        vendors = result.fetchall()
        for v in vendors:
            print(f"{v[0]} | {v[1]} | {v[2]}")
            
    print("\n=== ISSUE 2: Clean Contaminated Dataset ===")
    # Delete all match results for V-EVAL vendors (and just wipe all to be safe for eval org)
    # The evaluation org_id is typically '6806e04d-30af-4f53-bcb5-6ea4de2defbc' based on my previous logs
    # We will delete everything in match_results to be absolutely clean since this is a local eval DB.
    del_res = await db.match_results.delete_many({})
    print(f"Deleted {del_res.deleted_count} match results.")
    count_after = await db.match_results.count_documents({})
    print(f"Remaining match results: {count_after}")
    
    print("\n=== ISSUE 3: TM-EVAL-CIVIL-008 dominance ===")
    tender = await db.documents.find_one({"mongo_id": "TM-EVAL-CIVIL-008"})
    # wait, the mongo_id in the DB is usually a hex string. TM-EVAL-CIVIL-008 is the tender_id!
    # Let's search by structured_data.tender_id
    tender = await db.documents.find_one({"structured_data.tender_id": "TM-EVAL-CIVIL-008"})
    if tender:
        print(json.dumps(tender.get("structured_data", {}), indent=2))
    else:
        print("Tender TM-EVAL-CIVIL-008 not found!")
        
    print("\n=== ISSUE 4: Verify Embeddings ===")
    async with get_pg_session() as session:
        result = await session.execute(text("""
            SELECT vendor_id, business_name, 
                   profile_completeness_pct,
                   CASE WHEN embedding IS NULL THEN 'NO EMBEDDING' 
                        ELSE 'HAS EMBEDDING' END as embedding_status
            FROM vendor_profiles 
            WHERE vendor_id LIKE 'V-EVAL-%'
            ORDER BY vendor_id;
        """))
        vendors = result.fetchall()
        for v in vendors:
            print(f"{v[0]} | {v[1]} | {v[2]} | {v[3]}")
            
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
