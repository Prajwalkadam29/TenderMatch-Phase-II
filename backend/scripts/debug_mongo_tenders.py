import asyncio
from app.core.database import connect_to_mongo, get_db

async def check():
    await connect_to_mongo()
    db = get_db()
    docs = await db.documents.find({"type": "tender"}).to_list(100)
    print("Found tenders:", len(docs))
    test_tenders = [d for d in docs if "test_tender" in str(d.get("original_filename", "")) or "test_tender" in str(d.get("filename", ""))]
    print("Test tenders found:", len(test_tenders))
    if test_tenders:
        print("First test tender sample:", test_tenders[0])

if __name__ == "__main__":
    asyncio.run(check())
