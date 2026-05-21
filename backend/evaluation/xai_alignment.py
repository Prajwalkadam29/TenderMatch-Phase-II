import json
import os
from pymongo import MongoClient

def run_xai_alignment_eval():
    client = MongoClient("mongodb://localhost:27018/")
    db = client["tendermatch"]
    
    # Get all matching documents that have a "match_result" section
    match_results = list(db["match_results"].find({"match_result": {"$exists": True}}))
    
    total = len(match_results)
    print(f"Loaded {total} structured match results from database.")
    
    if total == 0:
        print("No matches to evaluate.")
        return
        
    alignment_issues = 0
    
    print("\nEvaluating XAI Alignment (Explanation vs. Math):")
    print("==================================================")
    
    for doc in match_results:
        mr = doc.get("match_result", {})
        
        # 1. Recommendation vs Final Score
        final_score = mr.get("weighted_score", {}).get("final_score", 0.0)
        overall_pass = mr.get("hard_filter_results", {}).get("overall_pass", False)
        recommendation = mr.get("recommendation", "")
        
        # Determine what recommendation should be
        if not overall_pass:
            expected = "NOT_ELIGIBLE"
        elif final_score >= 80:
            expected = "HIGH_MATCH"
        elif final_score >= 60:
            expected = "MODERATE_MATCH"
        elif final_score >= 40:
            expected = "LOW_MATCH"
        else:
            expected = "NOT_ELIGIBLE"
            
        if expected != recommendation and (expected != "NOT_ELIGIBLE" or "NOT ELIGIBLE" not in recommendation.upper()):
            alignment_issues += 1
            print(f"- Mismatch in {mr.get('_meta', {}).get('match_id')}:")
            print(f"  Score: {final_score}, Pass: {overall_pass}")
            print(f"  Expected Rec: {expected}, Got: {recommendation}")
    
    aligned = total - alignment_issues
    accuracy = (aligned / total) * 100
    
    print(f"\nXAI Recommendation Accuracy: {aligned}/{total} ({accuracy:.1f}%)")
    print(f"Misalignments found: {alignment_issues}")
    
    if accuracy == 100.0:
        print("\nAll natural language recommendations mathematically align with the scoring engine.")

if __name__ == "__main__":
    run_xai_alignment_eval()
