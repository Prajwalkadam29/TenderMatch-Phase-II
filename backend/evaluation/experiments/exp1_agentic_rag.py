"""
Experiment 1: Agentic RAG Validation
Validates that the Planner Agent makes correct routing decisions across different vendor-tender scenarios.
"""
import os
import json
import time
import httpx
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# Use the shared style
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import plot_style
    plot_style.set_academic_style()
except ImportError:
    pass

API_BASE = "http://localhost:8000"

async def run_scenario(client, token, scenario_id, vendor_id, tender_mongo_id, expected_strategy):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "vendor_profile_id": vendor_id,
        "tender_mongo_id": tender_mongo_id,
        "force_refresh": True # bypass cache for cold run
    }
    
    start_time = time.time()
    try:
        from app.agents.graph import run_match_pipeline
        
        start_time = time.time()
        data = await run_match_pipeline(
            vendor_profile_id=vendor_id,
            tender_mongo_id=tender_mongo_id,
            org_id=None
        )
        latency = (time.time() - start_time) * 1000
        
        if data.get("status") == "error":
            return {
                "scenario_id": scenario_id,
                "vendor_id": vendor_id,
                "tender_id": tender_mongo_id,
                "error": data.get("error"),
                "actual_strategy": "error"
            }
            
        match_result = data.get("match_result", {})
        
        # The planner info is likely in planner_decision
        actual_plan = data.get("planner_decision", {})
        actual_strategy = actual_plan.get("retrieval_strategy", "unknown")
        
        return {
            "scenario_id": scenario_id,
            "vendor_id": vendor_id,
            "tender_id": tender_mongo_id,
            "actual_plan": actual_plan,
            "expected_retrieval_strategy": expected_strategy,
            "plan_matched_expectation": (actual_strategy == expected_strategy),
            "plan_reasoning": actual_plan.get("reasoning", "No reasoning provided"),
            "redis_cache_hit": data.get("cache_hit", False),
            "planner_latency_ms": latency,
            "actual_strategy": actual_strategy
        }
    except httpx.HTTPStatusError as e:
        error_msg = f"{e}. Response: {e.response.text}"
        return {
            "scenario_id": scenario_id,
            "vendor_id": vendor_id,
            "tender_id": tender_mongo_id,
            "error": error_msg,
            "actual_strategy": "error"
        }
    except Exception as e:
        return {
            "scenario_id": scenario_id,
            "vendor_id": vendor_id,
            "tender_id": tender_mongo_id,
            "error": str(e),
            "actual_strategy": "error"
        }

async def main():
    from app.core.postgres import init_postgres
    from app.core.database import connect_to_mongo
    from app.core.redis_client import init_redis
    
    await init_postgres()
    await connect_to_mongo()
    await init_redis()
    
    eval_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(eval_dir, "data", "ingestion_manifest.json")
    
    if not os.path.exists(manifest_path):
        print("Manifest not found. Run ingestion first.")
        return
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    tenders = {t["tender_id"]: t["mongo_id"] for t in manifest.get("tenders", [])}
    vendors = {v["vendor_id"]: v["profile_id"] for v in manifest.get("vendor_profiles", [])}
    
    if not tenders or not vendors:
        print("Empty tenders or vendors in manifest.")
        return
        
    # Get a civil low threshold tender
    civil_tenders = [t for t in manifest.get("tenders", []) if "CIVIL" in t["tender_id"]]
    it_tenders = [t for t in manifest.get("tenders", []) if "IT" in t["tender_id"]]
    elec_tenders = [t for t in manifest.get("tenders", []) if "ELECTRICAL" in t["tender_id"]]
    road_tenders = [t for t in manifest.get("tenders", []) if "ROADS" in t["tender_id"]]
    
    scenarios = []
    
    # Try to add predefined scenarios if the domain tenders exist
    if civil_tenders: scenarios.append(("S1", "V-EVAL-001", civil_tenders[0]["mongo_id"], "vector_only"))
    if it_tenders: scenarios.append(("S2", "V-EVAL-009", it_tenders[0]["mongo_id"], "bm25_fallback"))
    if road_tenders: scenarios.append(("S3", "V-EVAL-007", road_tenders[0]["mongo_id"], "vector_only"))
    if elec_tenders: scenarios.append(("S4", "V-EVAL-006", elec_tenders[0]["mongo_id"], "bm25_fallback"))
    if len(civil_tenders) > 1: scenarios.append(("S5", "V-EVAL-008", civil_tenders[1]["mongo_id"], "hybrid"))
    elif civil_tenders: scenarios.append(("S5", "V-EVAL-008", civil_tenders[0]["mongo_id"], "hybrid"))
    
    # Generate random scenarios to fill up to 20
    import random
    vendor_ids = list(vendors.keys())
    tender_ids = [t["mongo_id"] for t in manifest.get("tenders", [])]
    current_s = len(scenarios) + 1
    for i in range(current_s, 51):
        v = random.choice(vendor_ids)
        t = random.choice(tender_ids)
        scenarios.append((f"S{i}", v, t, "unknown"))
        
    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch a real token since manifest might have a dummy one
        login_data = {"email": "eval3@tendermatch-research.internal", "password": "EvalSecure2026!"}
        login_resp = await client.post(f"{API_BASE}/auth/login", json=login_data)
        if login_resp.status_code == 200:
            token = login_resp.json()["access_token"]
        else:
            print("Failed to get real token, falling back to manifest token")
            token = manifest["access_token"]

        for s in scenarios:
            print(f"Running scenario {s[0]}...")
            res = await run_scenario(client, token, s[0], vendors[s[1]], s[2], s[3])
            res["vendor_code"] = s[1] # original vendor ID for analysis
            results.append(res)
            
    # Teardown database connections
    try:
        from app.core.postgres import close_postgres
        from app.core.database import close_mongo
        from app.core.redis_client import close_redis
        await close_postgres()
        await close_mongo()
        await close_redis()
    except Exception as e:
        print(f"Teardown error: {e}")
            
    # Save results
    out_dir = os.path.join(eval_dir, "results")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "exp1_agentic_rag.json")
    
    with open(out_file, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "script_version": "1.0.0",
            "results": results
        }, f, indent=4)
        
    print(f"Saved results to {out_file}")
    
    # Generate visualizations
    df = pd.DataFrame(results)
    if "actual_strategy" in df:
        strategies = df["actual_strategy"].value_counts()
        fig_dir = os.path.join(eval_dir, "figures", "agentic_rag")
        os.makedirs(fig_dir, exist_ok=True)
        
        plt.figure(figsize=(8, 8))
        plt.pie(strategies.values, labels=strategies.index, autopct='%1.1f%%', startangle=140)
        plt.title('Planner Agent Retrieval Strategy Distribution')
        plt.savefig(os.path.join(fig_dir, "fig_agentic_rag_plan_distribution.pdf"))
        plt.savefig(os.path.join(fig_dir, "fig_agentic_rag_plan_distribution.png"), dpi=150)
        plt.close()
        
        print(f"Saved figures to {fig_dir}")

if __name__ == "__main__":
    asyncio.run(main())
