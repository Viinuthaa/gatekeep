
import os

from fastapi import HTTPException
from redis.asyncio import Redis


redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)

LIMIT = 20
WINDOW_SECONDS = 60


async def check_rate_limit(tenant_id: str) -> None:
    key = f"rate_limit:{tenant_id}"

    try:
        request_count = await redis_client.incr(key)

        if request_count == 1:
            await redis_client.expire(key, WINDOW_SECONDS)

        if request_count > LIMIT:
            ttl = await redis_client.ttl(key)
            retry_after = max(ttl, 1)

            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service is unavailable.",
        ) from exc
