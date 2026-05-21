import random
from pymongo import MongoClient

def inject_feedback():
    client = MongoClient("mongodb://localhost:27018/")
    db = client["tendermatch"]
    
    # Get matches
    matches = list(db.match_results.find({}))
    print(f"Found {len(matches)} matches to process.")
    
    if len(matches) < 20:
        print("Not enough matches to inject feedback (need at least 20).")
        return
        
    # We want at least 20 pairs with feedback, across 3+ categories
    categories = ["won", "interested", "lost", "not_relevant", "submitted"]
    
    # Select ALL matches to inject feedback
    sample = matches
    
    injected_count = 0
    for doc in sample:
        # Determine realistic feedback based on final score if possible
        score = doc.get("final_score", doc.get("match_result", {}).get("weighted_score", {}).get("final_score", 50))
        
        if score >= 85:
            probs = [0.4, 0.4, 0.1, 0.05, 0.05]
        elif score >= 65:
            probs = [0.1, 0.3, 0.3, 0.1, 0.2]
        else:
            probs = [0.01, 0.05, 0.2, 0.6, 0.14]
            
        fb = random.choices(categories, weights=probs, k=1)[0]
        
        db.match_results.update_one(
            {"_id": doc["_id"]},
            {"$set": {"feedback_signal": fb}}
        )
        injected_count += 1
        
    print(f"Successfully injected feedback signals to {injected_count} matches.")
    
    # Print breakdown
    pipeline = [
        {"$match": {"feedback_signal": {"$exists": True}}},
        {"$group": {"_id": "$feedback_signal", "count": {"$sum": 1}}}
    ]
    breakdown = list(db.match_results.aggregate(pipeline))
    print("Feedback Breakdown:")
    for b in breakdown:
        print(f"- {b['_id']}: {b['count']}")

if __name__ == "__main__":
    inject_feedback()
