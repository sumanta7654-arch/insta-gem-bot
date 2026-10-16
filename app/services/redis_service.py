import redis
import json
from datetime import datetime, timezone, timedelta

from app.core.config import REDIS_URL

GEMINI_USAGE_CHANNEL = "gemini:usage:events"

RECENT_MESSAGES_LIMIT = 6
RECENT_MESSAGES_TTL = 60 * 60 * 24

GEMINI_USAGE_TTL = 60 * 60 * 48

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


def check_redis_connection() -> bool:
    try:
        return redis_client.ping()
    except redis.RedisError as e:
        print(f"Redis connection failed: {e}")
        return False


def get_recent_messages(user_id: int) -> list[dict] | None:
    key = f"user:{user_id}:recent_messages"

    try:
        messages = redis_client.lrange(key, 0, -1)

        if not messages:
            return None

        return [json.loads(message) for message in messages]

    except redis.RedisError as e:
        print(f"Redis read failed: {e}")
        return None


def cache_message(
    user_id: int,
    role: str,
    content: str,
    created_at: str
) -> bool:
    key = f"user:{user_id}:recent_messages"

    message = json.dumps({
        "role": role,
        "content": content,
        "created_at": created_at,
    })

    try:
        redis_client.rpush(key, message)
        redis_client.ltrim(
            key,
            -RECENT_MESSAGES_LIMIT,
            -1
        )
        redis_client.expire(
            key,
            RECENT_MESSAGES_TTL
        )

        return True

    except redis.RedisError as e:
        print(f"Redis write failed: {e}")
        return False


USER_CONTEXT_TTL = 60 * 60 * 24


def get_cached_user_summary(user_id: int) -> str | None:
    key = f"user:{user_id}:memory"

    try:
        return redis_client.get(key)
    except redis.RedisError as e:
        print(f"Redis memory read failed: {e}")
        return None


def cache_user_summary(user_id: int, summary: str) -> bool:
    key = f"user:{user_id}:memory"

    try:
        redis_client.set(
            key,
            summary,
            ex=USER_CONTEXT_TTL
        )
        return True
    except redis.RedisError as e:
        print(f"Redis memory write failed: {e}")
        return False


def get_cached_conversation_summary(
    user_id: int
) -> str | None:
    key = f"user:{user_id}:conversation_summary"

    try:
        return redis_client.get(key)
    except redis.RedisError as e:
        print(f"Redis conversation summary read failed: {e}")
        return None


def cache_conversation_summary(
    user_id: int,
    summary: str
) -> bool:
    key = f"user:{user_id}:conversation_summary"

    try:
        redis_client.set(
            key,
            summary,
            ex=USER_CONTEXT_TTL
        )
        return True
    except redis.RedisError as e:
        print(
            f"Redis conversation summary write failed: {e}"
        )
        return False


def record_gemini_usage(
    model: str,
    api_key: str,
    status: str,
    operation: str = "unknown",
    fallback: bool = False,
) -> bool:

    now = datetime.now(timezone.utc)
    bucket = now.strftime("%Y-%m-%d:%H")

    base_key = f"gemini:usage:{bucket}"

    try:
        pipe = redis_client.pipeline()

        pipe.hincrby(base_key, "total", 1)

        if status == "success":
            pipe.hincrby(base_key, "success", 1)
        else:
            pipe.hincrby(base_key, "failed", 1)

        if fallback:
            pipe.hincrby(base_key, "fallback", 1)

        if api_key == "key1":
            pipe.hincrby(base_key, "key1", 1)
        elif api_key == "key2":
            pipe.hincrby(base_key, "key2", 1)

        model_key = (
            f"gemini:usage:model:{model}:{bucket}"
        )

        operation_key = (
            f"gemini:usage:operation:{operation}:{bucket}"
        )

        pipe.incr(model_key)
        pipe.incr(operation_key)

        pipe.expire(base_key, GEMINI_USAGE_TTL)
        pipe.expire(model_key, GEMINI_USAGE_TTL)
        pipe.expire(operation_key, GEMINI_USAGE_TTL)

        event = {
            "type": "gemini_usage",
            "model": model,
            "api_key": api_key,
            "status": status,
            "operation": operation,
            "fallback": fallback,
            "timestamp": now.isoformat(),
        }

        pipe.publish(
            GEMINI_USAGE_CHANNEL,
            json.dumps(event),
        )

        pipe.execute()

        return True

    except redis.RedisError as e:
        print(f"Gemini usage tracking failed: {e}")
        return False


def get_gemini_usage_last_24h() -> dict:
    now = datetime.now(timezone.utc)

    total = 0
    success = 0
    failed = 0
    fallback = 0
    key1 = 0
    key2 = 0

    by_model = {}
    by_operation = {}

    try:
        for hour_offset in range(24):
            bucket_time = now - timedelta(hours=hour_offset)
            bucket = bucket_time.strftime("%Y-%m-%d:%H")

            usage_key = f"gemini:usage:{bucket}"
            usage = redis_client.hgetall(usage_key)

            if usage:
                total += int(usage.get("total", 0))
                success += int(usage.get("success", 0))
                failed += int(usage.get("failed", 0))
                fallback += int(usage.get("fallback", 0))
                key1 += int(usage.get("key1", 0))
                key2 += int(usage.get("key2", 0))

            model_pattern = f"gemini:usage:model:*:{bucket}"

            for key in redis_client.scan_iter(
                match=model_pattern
            ):
                model = key[
                    len("gemini:usage:model:"):
                    -len(f":{bucket}")
                ]

                count = int(redis_client.get(key) or 0)
                by_model[model] = by_model.get(model, 0) + count

            operation_pattern = (
                f"gemini:usage:operation:*:{bucket}"
            )

            for key in redis_client.scan_iter(
                match=operation_pattern
            ):
                operation = key[
                    len("gemini:usage:operation:"):
                    -len(f":{bucket}")
                ]

                count = int(redis_client.get(key) or 0)
                by_operation[operation] = (
                    by_operation.get(operation, 0) + count
                )

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "fallback": fallback,
            "key1": key1,
            "key2": key2,
            "by_model": by_model,
            "by_operation": by_operation,
        }

    except redis.RedisError as e:
        print(f"Gemini usage read failed: {e}")

        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "fallback": 0,
            "key1": 0,
            "key2": 0,
            "by_model": {},
            "by_operation": {},
        }
