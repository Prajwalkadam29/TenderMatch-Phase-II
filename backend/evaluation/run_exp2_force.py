import asyncio
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from sqlalchemy import select
from app.db.models.document import VendorProfile, Tender
from app.services.matching_service import HardFilterEngine, WeightedScoringEngine

async def run_all_matches():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    tenders = [t for t in manifest.get("tenders", []) if t.get("status") == "completed"]
    vendors = manifest.get("vendor_profiles", [])
    
    print(f"Generating matches for {len(vendors)} vendors against {len(tenders)} tenders...")
    
    # Pre-fetch vendors from pg
    vendor_ids = [v["profile_id"] for v in vendors]
    async with get_pg_session() as session:
        result = await session.execute(select(VendorProfile).where(VendorProfile.id.in_(vendor_ids)))
        pg_vendors = {str(v.id): v for v in result.scalars().all()}
        
        tender_ids = [t["mongo_id"] for t in tenders]
        result = await session.execute(select(Tender).where(Tender.mongo_id.in_(tender_ids)))
        pg_tenders = {t.mongo_id: t for t in result.scalars().all()}
        
    from bson import ObjectId
    mongo_tenders_cursor = db.documents.find({"_id": {"$in": [ObjectId(t) for t in tender_ids]}})
    mongo_tenders_list = await mongo_tenders_cursor.to_list(length=100)
    mongo_tenders = {str(t["_id"]): t for t in mongo_tenders_list}
    
    docs_to_insert = []
    
    for v in vendors:
        v_id = v["profile_id"]
        v_orm = pg_vendors.get(v_id)
        if not v_orm: continue
        
        for t in tenders:
            t_id = t["mongo_id"]
            t_mongo = mongo_tenders.get(t_id)
            if not t_mongo: continue
            
            # evaluate
            v_data = v_orm.profile_data
            t_data = t_mongo.get("structured_data", {})
            
            hf = HardFilterEngine.evaluate(v_data, t_data)
            score = 0
            if hf["overall_pass"]:
                # calc score
                import numpy as np
                t_orm = pg_tenders.get(t_id)
                sem_score = 0.0
                if v_orm.embedding is not None and t_orm is not None and t_orm.embedding is not None:
                    v_vec = np.array(v_orm.embedding)
                    t_vec = np.array(t_orm.embedding)
                    norm_v = np.linalg.norm(v_vec)
                    norm_t = np.linalg.norm(t_vec)
                    if norm_v > 0 and norm_t > 0:
                        sem_score = float(np.dot(v_vec, t_vec) / (norm_v * norm_t))
                        
                ws = WeightedScoringEngine.calculate_score(v_data, t_data, sem_score, None)
                score = ws["final_score"]
                breakdown = ws["breakdown"]
            else:
                score = 0
                breakdown = {}
                
            match_id = f"MR-{v_orm.vendor_id}-{t_id[-8:]}"
            
            doc = {
                "match_result": {
                    "_meta": {
                        "match_id": match_id,
                        "vendor_profile_id": v_id,
                        "vendor_id": v_orm.vendor_id,
                        "tender_mongo_id": t_id
                    },
                    "hard_filter_results": hf,
                    "weighted_score": {
                        "final_score": score,
                        "breakdown": breakdown,
                        "eligibility_status": "Eligible" if hf["overall_pass"] else "Ineligible"
                    }
                }
            }
            
            docs_to_insert.append(doc)
            
    print(f"Upserting {len(docs_to_insert)} matches...")
    for doc in docs_to_insert:
        await db.match_results.replace_one(
            {"match_result._meta.match_id": doc["match_result"]["_meta"]["match_id"]},
            doc,
            upsert=True
        )
        
    print("Done!")
    
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run_all_matches())
