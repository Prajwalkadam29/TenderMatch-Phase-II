import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    c = AsyncIOMotorClient('mongodb://localhost:27018')
    count = await c.tendermatch.match_results.count_documents({})
    print("Match Results Count:", count)
    doc = await c.tendermatch.match_results.find_one({})
    print("Sample doc:", doc)

asyncio.run(check())
