import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
import os
from dotenv import load_dotenv

load_dotenv('d:/Python-Projects/TenderMatch_Phase_2-2-/backend/.env')

async def main():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DATABASE_NAME", "tendermatch")]
    
    # get one with feedback_signal
    match = await db.match_results.find_one({"feedback_signal": {"$ne": None}})
    if match:
        print("Found with feedback_signal:")
        print("Root keys:", list(match.keys()))
        print("feedback_signal:", match.get("feedback_signal"))
    else:
        print("no match found with feedback_signal")
        # try finding one with match_result
        match = await db.match_results.find_one({"match_result": {"$exists": True}})
        if match:
            print("Found with match_result:")
            print("Root keys:", list(match.keys()))
            mr = match.get("match_result", {})
            print("mr keys:", list(mr.keys()))
            exp = mr.get("explanation", {})
            print("exp keys:", list(exp.keys()) if isinstance(exp, dict) else type(exp))
            if isinstance(exp, dict):
                print("executive_summary:", exp.get("executive_summary"))
            
            print("retrieval_scores:", type(mr.get("retrieval_scores")))
            if mr.get("retrieval_scores"):
                print("retrieval_scores keys:", list(mr.get("retrieval_scores")[0].keys()) if len(mr.get("retrieval_scores")) > 0 else "empty")
        else:
            print("No match with match_result either.")

if __name__ == "__main__":
    asyncio.run(main())
