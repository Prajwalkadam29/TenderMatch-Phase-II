import redis.asyncio as redis
from app.core.config import settings

# Global redis connection
redis_client: redis.Redis = None

async def init_redis():
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    print(f"[OK] Connected to Redis: {settings.REDIS_URL}")

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        print("[INFO] Redis connection closed")

def get_redis() -> redis.Redis:
    return redis_client
