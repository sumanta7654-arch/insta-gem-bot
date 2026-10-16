import redis.asyncio as aioredis

from app.core.config import REDIS_URL
from app.services.redis_service import GEMINI_USAGE_CHANNEL


async_redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)


async def subscribe_gemini_usage():
    pubsub = async_redis_client.pubsub()

    try:
        await pubsub.subscribe(GEMINI_USAGE_CHANNEL)

        async for message in pubsub.listen():
            if message["type"] == "message":
                yield message["data"]

    finally:
        await pubsub.unsubscribe(GEMINI_USAGE_CHANNEL)
        await pubsub.aclose()