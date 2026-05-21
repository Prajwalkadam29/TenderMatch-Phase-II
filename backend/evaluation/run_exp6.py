import asyncio
import httpx
import json
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from sqlalchemy import text

async def get_match_id(db, vendor_id, tender_scope_keyword, pg_tenders_map):
    cursor = db.match_results.find({
        "match_result._meta.vendor_id": vendor_id
    })
    
    matches = await cursor.to_list(100)
    # Sort by score DESC
    matches.sort(key=lambda x: x["match_result"]["weighted_score"]["final_score"], reverse=True)
    
    for m in matches:
        t_id = m["match_result"]["_meta"]["tender_mongo_id"]
        filename = pg_tenders_map.get(t_id, "").lower()
        if tender_scope_keyword.lower() in filename:
            return m["match_result"]["_meta"]["match_id"]
            
    print(f"Warning: No match found for {vendor_id} with keyword {tender_scope_keyword}")
    return None

async def run_sequence(client, headers, vendor_id, sequence, db, pg_tenders_map):
    print(f"\nRunning Sequence for {vendor_id}...")
    results = []
    current_count = 0  # track actual DB feedback count
    
    for idx, step in enumerate(sequence):
        signal = step["signal"]
        keyword = step["keyword"]
        
        match_id = await get_match_id(db, vendor_id, keyword, pg_tenders_map)
        if not match_id:
            print(f"  Step {idx+1}: SKIPPED — no match found for keyword '{keyword}'")
            continue
            
        print(f"  Step {idx+1}: Sending '{signal}' on tender matching '{keyword}' (Match: {match_id})")
        await client.post("/match/feedback", json={"match_id": match_id, "signal": signal}, headers=headers)
        expected_count = current_count + 1
        
        # Poll deterministically until Celery commits the new row
        captured = False
        for attempt in range(20):
            await asyncio.sleep(1.5)
            async with get_pg_session() as session:
                result = await session.execute(text(f"""
                    SELECT w.weight_domain, w.weight_geography, w.weight_financial,
                           w.weight_experience, w.weight_certification,
                           w.weight_semantic, w.weight_confidence, w.total_feedback_count
                    FROM vendor_profile_weights w
                    JOIN vendor_profiles v ON w.vendor_profile_id = v.id
                    WHERE v.vendor_id = '{vendor_id}'
                """))
                row = result.fetchone()
                if row and row[7] >= expected_count:
                    current_count = row[7]
                    results.append({
                        "step": idx + 1,
                        "signal": signal,
                        "keyword": keyword,
                        "weights": {
                            "domain": row[0],
                            "geography": row[1],
                            "financial": row[2],
                            "experience": row[3],
                            "certification": row[4],
                            "semantic": row[5],
                            "confidence": row[6]
                        }
                    })
                    captured = True
                    break
        if not captured:
            print(f"  Step {idx+1}: TIMEOUT waiting for Celery to process!")
                
    return results

async def main():
    await connect_to_mongo()
    await init_postgres()
    db = get_db()
    
    # 1. Reset Postgres Weights
    print("Resetting vendor_profile_weights for V-EVAL-001 and V-EVAL-004...")
    async with get_pg_session() as session:
        await session.execute(text("""
            DELETE FROM vendor_profile_weights 
            WHERE vendor_profile_id IN (
                SELECT id FROM vendor_profiles WHERE vendor_id IN ('V-EVAL-001', 'V-EVAL-004')
            )
        """))
        await session.commit()
        
    # 2. Get API Token
    manifest_path = "evaluation/data/ingestion_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        login_resp = await client.post("/auth/login", json={"email": "eval3@tendermatch-research.internal", "password": "EvalSecure2026!"})
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        
        # Load pg tenders map
        async with get_pg_session() as session:
            res = await session.execute(text("SELECT mongo_id, filename FROM tenders"))
            pg_tenders_map = {row[0]: row[1] for row in res.fetchall()}
            
        seq_v1 = [
            {"signal": "won", "keyword": "CIVIL"},
            {"signal": "submitted", "keyword": "CIVIL"},
            {"signal": "not_relevant", "keyword": "IT"},
            {"signal": "interested", "keyword": "CIVIL"},
            {"signal": "not_relevant", "keyword": "HEALTH"},
            {"signal": "lost", "keyword": "CIVIL"},
            {"signal": "won", "keyword": "CIVIL"}
        ]
        
        seq_v4 = [
            {"signal": "won", "keyword": "IT"},
            {"signal": "submitted", "keyword": "IT"},
            {"signal": "not_relevant", "keyword": "CIVIL"},
            {"signal": "interested", "keyword": "IT"},
            {"signal": "not_relevant", "keyword": "ROADS"},
            {"signal": "lost", "keyword": "IT"},
            {"signal": "won", "keyword": "IT"}
        ]
        
        v1_results = await run_sequence(client, headers, "V-EVAL-001", seq_v1, db, pg_tenders_map)
        v4_results = await run_sequence(client, headers, "V-EVAL-004", seq_v4, db, pg_tenders_map)
        
        # Print Table 6a format
        print("\n=== Table 6a: V-EVAL-001 Weight Evolution ===")
        print("Step | Signal | Domain | Geog | Fin | Exp | Cert | Sem | Conf")
        print("0 | START | 0.2500 | 0.1500 | 0.2000 | 0.1500 | 0.1000 | 0.1000 | 0.0500")
        for r in v1_results:
            w = r['weights']
            print(f"{r['step']} | {r['signal']} | {w['domain']:.4f} | {w['geography']:.4f} | {w['financial']:.4f} | {w['experience']:.4f} | {w['certification']:.4f} | {w['semantic']:.4f} | {w['confidence']:.4f}")

        print("\n=== Table 6a: V-EVAL-004 Weight Evolution ===")
        print("Step | Signal | Domain | Geog | Fin | Exp | Cert | Sem | Conf")
        print("0 | START | 0.2500 | 0.1500 | 0.2000 | 0.1500 | 0.1000 | 0.1000 | 0.0500")
        for r in v4_results:
            w = r['weights']
            print(f"{r['step']} | {r['signal']} | {w['domain']:.4f} | {w['geography']:.4f} | {w['financial']:.4f} | {w['experience']:.4f} | {w['certification']:.4f} | {w['semantic']:.4f} | {w['confidence']:.4f}")
            
    await close_mongo_connection()
    await close_postgres()

if __name__ == "__main__":
    asyncio.run(main())
