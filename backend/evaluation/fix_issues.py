import asyncio
import json
import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres, get_pg_session

async def main():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    with open('evaluation/data/ingestion_manifest.json', 'r') as f:
        manifest = json.load(f)
        
    with open('evaluation/data/vendors_10.json', 'r') as f:
        v_data = json.load(f)
        v_pct_map = {v['vendor_id']: v['profile_completeness_pct'] for v in v_data['vendors']}
        
    print("Fixing Issue 1: Vendor profiles wrong completeness & IDs")
    async with get_pg_session() as session:
        for v in manifest.get('vendor_profiles', []):
            v_eval_id = v['vendor_id']  # V-EVAL-XXX
            pg_uuid = v['profile_id']
            pct = v_pct_map.get(v_eval_id, 0)
            
            await session.execute(text(f"""
                UPDATE vendor_profiles 
                SET vendor_id = '{v_eval_id}', profile_completeness_pct = {pct}
                WHERE id = '{pg_uuid}'
            """))
            
        await session.commit()
        print('Updated Postgres vendors!')
        
    print("Issue 2 was already cleaned in the previous diagnostics run.")
    
    print("Fixing Issue 3: Investigate TM-EVAL-CIVIL-008 dominance")
    t_id_to_find = "TM-EVAL-CIVIL-008"
    mongo_id = None
    for t in manifest.get('tenders', []):
        if t['tender_id'] == t_id_to_find:
            mongo_id = t['mongo_id']
            break
            
    if mongo_id:
        from bson import ObjectId
        tender = await db.documents.find_one({"_id": ObjectId(mongo_id)})
        if tender:
            print("Found TM-EVAL-CIVIL-008!")
            print(json.dumps(tender.get("structured_data", {}), indent=2))
        else:
            print("Tender document not found in mongo by _id.")
    else:
        print("Could not find mongo_id for TM-EVAL-CIVIL-008 in manifest.")
        
    print("Fixing Issue 4: Verify embeddings were generated")
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
        for v in result.fetchall():
            print(f"{v[0]} | {v[1]} | {v[2]} | {v[3]}")
            
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
