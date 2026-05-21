import asyncio
from app.core.database import connect_to_mongo, get_db

async def fix():
    await connect_to_mongo()
    db = get_db()
    
    # Find all test tenders that have 'filename' but not 'original_filename'
    cursor = db.documents.find({"filename": {"$regex": "^test_tender_"}})
    docs = await cursor.to_list(length=100)
    
    count = 0
    for doc in docs:
        if "filename" in doc and "original_filename" not in doc:
            await db.documents.update_one(
                {"_id": doc["_id"]},
                {"$set": {"original_filename": doc["filename"]}}
            )
            count += 1
            
    print(f"Successfully fixed {count} test tenders in MongoDB.")

if __name__ == "__main__":
    asyncio.run(fix())
