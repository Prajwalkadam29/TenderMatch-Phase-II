import json
import os
from pymongo import MongoClient

def run_hard_filter_eval():
    # Load manifest mapping
    manifest_path = os.path.join(os.path.dirname(__file__), "data", "ingestion_manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    vendor_map = {}
    for v in manifest.get("vendor_profiles", []):
        vendor_map[v["vendor_id"]] = v["profile_id"]
        
    client = MongoClient("mongodb://localhost:27018/")
    db = client["tendermatch"]
    match_results = list(db["match_results"].find())
    
    # Filter out old flat match results
    new_matches = [m for m in match_results if "match_result" in m]
    
    total_matches = len(new_matches)
    passed = sum(1 for m in new_matches if m.get("match_result", {}).get("hard_filter_results", {}).get("overall_pass", False))
    failed = total_matches - passed
    
    print("Hard Filter Evaluation Results:")
    print("===============================")
    print(f"Total Matches Evaluated: {total_matches}")
    print(f"Passed Hard Filter: {passed} ({(passed/total_matches)*100 if total_matches else 0:.1f}%)")
    print(f"Failed Hard Filter: {failed} ({(failed/total_matches)*100 if total_matches else 0:.1f}%)")
    
    if failed > 0:
        print("\nSample Disqualification Reasons:")
        failed_list = [m for m in new_matches if not m.get("match_result", {}).get("hard_filter_results", {}).get("overall_pass", False)]
        for f in failed_list[:5]:
            print("-", f.get("match_result", {}).get("hard_filter_results", {}).get("disqualification_reason"))

    
    # Check V-EVAL-009
    v009_uuid = vendor_map.get("V-EVAL-009")
    v_009_matches = [m for m in new_matches if m.get("match_result", {}).get("_meta", {}).get("vendor_profile_id") == v009_uuid]
    v_009_passed = sum(1 for m in v_009_matches if m.get("match_result", {}).get("hard_filter_results", {}).get("overall_pass", False))
    
    print("\nEdge Case: V-EVAL-009 (Low Turnover / Experience)")
    print(f"Total Matches for V-EVAL-009: {len(v_009_matches)}")
    print(f"Passed: {v_009_passed}")
    print(f"Failed: {len(v_009_matches) - v_009_passed}")
    
    # Show reasons for failure for V-EVAL-009
    if len(v_009_matches) > 0:
        print("\nFailure reasons for V-EVAL-009 (Sample):")
        failed_009 = [m for m in v_009_matches if not m.get("match_result", {}).get("hard_filter_results", {}).get("overall_pass", False)]
        for f in failed_009[:3]:
            tender_id = f.get("match_result", {}).get("_meta", {}).get("tender_mongo_id", "Unknown")
            reason = f.get("match_result", {}).get("hard_filter_results", {}).get("disqualification_reason", "No reason provided")
            print(f"- Tender {tender_id}: {reason}")
            
    # Check V-EVAL-010
    v010_uuid = vendor_map.get("V-EVAL-010")
    v_010_matches = [m for m in new_matches if m.get("match_result", {}).get("_meta", {}).get("vendor_profile_id") == v010_uuid]
    v_010_passed = sum(1 for m in v_010_matches if m.get("match_result", {}).get("hard_filter_results", {}).get("overall_pass", False))
    
    print("\nEdge Case: V-EVAL-010 (Consultancy - Low Turnover)")
    print(f"Total Matches for V-EVAL-010: {len(v_010_matches)}")
    print(f"Passed: {v_010_passed}")
    print(f"Failed: {len(v_010_matches) - v_010_passed}")

if __name__ == "__main__":
    run_hard_filter_eval()
