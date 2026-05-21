import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

async def check():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DATABASE_NAME", "tendermatch")]
    
    # query for match results where final_score > 50
    cursor = db.match_results.find({
        "$or": [
            {"final_score": {"$gt": 50}},
            {"match_result.weighted_score.final_score": {"$gt": 50}},
            {"match_result.final_score": {"$gt": 50}}
        ]
    }).limit(10)
    matches = await cursor.to_list(length=10)
    
    print(f"Found {len(matches)} matches with score > 50")
    for m in matches:
        mr = m.get("match_result", m)
        score_node = mr.get("weighted_score", mr)
        final_score = score_node.get("final_score", m.get("final_score", 0.0))
        
        explanation_node = mr.get("explanation", {})
        if isinstance(explanation_node, dict) and "executive_summary" in explanation_node:
            ans = str(explanation_node.get("executive_summary", ""))
        else:
            ans = str(mr.get("explanation_text", m.get("explanation_text", "")))
            
        print(f"Score: {final_score}, Explanation len: {len(ans)}, Text snippet: {ans[:100]}")

if __name__ == "__main__":
    asyncio.run(check())
