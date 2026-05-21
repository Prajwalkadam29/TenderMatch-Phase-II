import asyncio
import json
import httpx
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from sqlalchemy import text

async def main():
    await connect_to_mongo()
    await init_postgres()
    db = get_db()
    
    # 1. Get Top Match for V-EVAL-001
    cursor = db.match_results.find(
        {"match_result._meta.vendor_id": "V-EVAL-001"}
    ).sort("match_result.weighted_score.final_score", -1).limit(1)
    
    match_docs = await cursor.to_list(1)
    if not match_docs:
        print("No match found for V-EVAL-001")
        return
        
    top_match = match_docs[0]
    match_id = top_match["match_result"]["_meta"]["match_id"]
    print(f"Found Top Match ID: {match_id} (Score: {top_match['match_result']['weighted_score']['final_score']})")
    
    # 2. Get API Token
    manifest_path = "evaluation/data/ingestion_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        login_data = {"email": "eval3@tendermatch-research.internal", "password": "EvalSecure2026!"}
        login_resp = await client.post("/auth/login", json=login_data)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Post Feedback
        payload = {"match_id": match_id, "signal": "won"}
        resp = await client.post("/match/feedback", json=payload, headers=headers)
        print("\n--- Feedback API Response ---")
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
        
    # Wait for Celery worker to process
    print("Waiting 2 seconds for Celery to process feedback...")
    await asyncio.sleep(2)
    
    # 4. Query Postgres
    print("\n--- Checking Postgres `vendor_profile_weights` ---")
    async with get_pg_session() as session:
        result = await session.execute(text("""
            SELECT v.vendor_id, w.weight_domain, w.weight_geography, w.weight_financial, w.weight_experience, w.weight_certification, w.weight_semantic, w.weight_confidence, w.total_feedback_count
            FROM vendor_profile_weights w
            JOIN vendor_profiles v ON w.vendor_profile_id = v.id
            WHERE v.vendor_id = 'V-EVAL-001'
        """))
        row = result.fetchone()
        if row:
            print("Postgres Row Found!")
            print(f"Vendor: {row[0]}, Feedback Count: {row[8]}")
            print(f"Domain: {row[1]:.4f}, Geog: {row[2]:.4f}, Fin: {row[3]:.4f}, Exp: {row[4]:.4f}, Cert: {row[5]:.4f}, Sem: {row[6]:.4f}, Conf: {row[7]:.4f}")
        else:
            print("Postgres Row STILL NOT FOUND! Celery might not be running or task failed.")
            
    await close_mongo_connection()
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
