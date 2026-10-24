
import hashlib
import json

from redis.asyncio import Redis

from app.config import settings


redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)

CACHE_TTL_SECONDS = 300


def build_cache_key(
    tenant_id: str,
    model: str,
    messages: list[dict],
) -> str:
    payload = json.dumps(
        {
            "tenant_id": tenant_id,
            "model": model,
            "messages": messages,
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return f"gatekeep:cache:{fingerprint}"


async def get_cached_response(
    tenant_id: str,
    model: str,
    messages: list[dict],
) -> dict | None:
    key = build_cache_key(tenant_id, model, messages)

    try:
        cached_value = await redis_client.get(key)

        if cached_value is None:
            return None

        return json.loads(cached_value)
    except Exception:
        return None


async def set_cached_response(
    tenant_id: str,
    model: str,
    messages: list[dict],
    response: dict,
) -> None:
    key = build_cache_key(tenant_id, model, messages)

    try:
        await redis_client.set(
            key,
            json.dumps(response),
            ex=CACHE_TTL_SECONDS,
        )
    except Exception:
        return
