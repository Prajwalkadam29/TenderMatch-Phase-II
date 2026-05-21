import asyncio
import os
import sys
import json
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection
from app.core.postgres import init_postgres, close_postgres, get_pg_session
from app.db.models.document import VendorProfile

async def main():
    await init_postgres()
    await connect_to_mongo()
    db = get_db()
    
    # Check old vs new schema count
    total = await db.match_results.count_documents({})
    new_schema = await db.match_results.count_documents({"match_result": {"$exists": True}})
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    manifest_path = os.path.join(data_dir, "ingestion_manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    manifest_vendor_ids = [v["profile_id"] for v in manifest.get("vendor_profiles", [])]
    
    # Fetch from Postgres
    async with get_pg_session() as session:
        result = await session.execute(select(VendorProfile).where(VendorProfile.id.in_(manifest_vendor_ids)))
        vendors = result.scalars().all()
        
    print("| Vendor ID | Vendor Name | Completeness | Total Pairs | Hard Filter Pass | Hard Filter Fail | Pass Rate % | Avg Score (passed) | Top Recommended Tender |")
    print("|---|---|---|---|---|---|---|---|---|")
    
    results = []
    
    for v in vendors:
        vendor_uuid = str(v.id)
        vendor_code = v.vendor_id
        vendor_name = v.business_name or v.profile_data.get("identity", {}).get("company_legal_name", "Unknown")
        completeness = getattr(v, "profile_completeness_pct", 0)
        
        # New v3 schema matches
        matches_cursor = db.match_results.find({"match_result._meta.vendor_profile_id": vendor_uuid})
        matches = await matches_cursor.to_list(length=1000)
        
        total_pairs = len(matches)
        
        hard_filter_pass = 0
        passed_scores = []
        top_tender_name = "N/A"
        top_score = -1
        
        for doc in matches:
            mr = doc.get("match_result", {})
            hfr = mr.get("hard_filter_results", {})
            ws = mr.get("weighted_score", {})
            
            if hfr.get("overall_pass", False):
                hard_filter_pass += 1
                score = ws.get("final_score", 0)
                passed_scores.append(score)
                if score > top_score:
                    top_score = score
                    t_mongo_id = mr.get("_meta", {}).get("tender_mongo_id")
                    if t_mongo_id:
                        # Find title in manifest
                        for t in manifest.get("tenders", []):
                            if t.get("mongo_id") == t_mongo_id:
                                top_tender_name = t.get("tender_id", "Unknown")
                                break
                            
        hard_filter_fail = total_pairs - hard_filter_pass
        pass_rate = (hard_filter_pass / total_pairs * 100) if total_pairs > 0 else 0
        avg_score = (sum(passed_scores) / len(passed_scores)) if passed_scores else 0
        
        print(f"| {vendor_code} | {vendor_name} | {completeness:.1f}% | {total_pairs} | {hard_filter_pass} | {hard_filter_fail} | {pass_rate:.1f}% | {avg_score:.1f} | {top_tender_name} |")
        
        results.append({
            "vendor_id": vendor_code,
            "vendor_name": vendor_name,
            "completeness": round(completeness, 1),
            "total_pairs": total_pairs,
            "hard_filter_pass": hard_filter_pass,
            "hard_filter_fail": hard_filter_fail,
            "pass_rate_pct": round(pass_rate, 1),
            "avg_score_passed": round(avg_score, 1),
            "top_recommended_tender": top_tender_name
        })
        
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "results", "exp2_matching_results.json"), "w") as f:
        json.dump({"total_matches": new_schema, "vendors": results}, f, indent=2)
        
    await close_postgres()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
