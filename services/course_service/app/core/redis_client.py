import redis.asyncio as aioredis
from app.core.settings import settings

redis_client: aioredis.Redis | None = None

async def connect_redis() -> None:
    global redis_client
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_response=True,
    )

async def disconnect_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None

def get_redis() -> aioredis.Redis:
    return redis_client