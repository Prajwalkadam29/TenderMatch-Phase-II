import asyncio
import redis.asyncio as redis

async def c():
    r = redis.from_url('redis://localhost:6380/0', decode_responses=True)
    await r.flushdb()
    await r.aclose()

asyncio.run(c())
