
import json
from unittest.mock import patch

import fakeredis.aioredis
import pytest

from app.cache import (
    CACHE_TTL_SECONDS,
    build_cache_key,
    get_cached_response,
    set_cached_response,
)


@pytest.mark.asyncio
async def test_cache_key_is_consistent():
    messages = [{"role": "user", "content": "Hello Gatekeep!"}]

    first = build_cache_key("tenant-a", "test-model", messages)
    second = build_cache_key("tenant-a", "test-model", messages)

    assert first == second


@pytest.mark.asyncio
async def test_different_prompts_have_different_keys():
    first = build_cache_key(
        "tenant-a",
        "test-model",
        [{"role": "user", "content": "Hello!"}],
    )
    second = build_cache_key(
        "tenant-a",
        "test-model",
        [{"role": "user", "content": "Goodbye!"}],
    )

    assert first != second


@pytest.mark.asyncio
async def test_different_models_have_different_keys():
    messages = [{"role": "user", "content": "Hello!"}]

    first = build_cache_key("tenant-a", "model-a", messages)
    second = build_cache_key("tenant-a", "model-b", messages)

    assert first != second


@pytest.mark.asyncio
async def test_different_tenants_have_different_keys():
    messages = [{"role": "user", "content": "Hello!"}]

    first = build_cache_key("tenant-a", "test-model", messages)
    second = build_cache_key("tenant-b", "test-model", messages)

    assert first != second


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch("app.cache.redis_client", fake_redis):
        result = await get_cached_response(
            "tenant-a",
            "test-model",
            [{"role": "user", "content": "Not cached"}],
        )

    assert result is None
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_cached_response_can_be_retrieved():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    messages = [{"role": "user", "content": "Hello!"}]
    response = {
        "id": "test-response",
        "model": "test-model",
        "content": "Hello from cache!",
        "prompt_tokens": 5,
        "completion_tokens": 4,
    }

    with patch("app.cache.redis_client", fake_redis):
        await set_cached_response(
            "tenant-a",
            "test-model",
            messages,
            response,
        )

        result = await get_cached_response(
            "tenant-a",
            "test-model",
            messages,
        )

    assert result == response
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_tenant_cannot_read_another_tenants_cache():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    messages = [{"role": "user", "content": "Hello!"}]

    with patch("app.cache.redis_client", fake_redis):
        await set_cached_response(
            "tenant-a",
            "test-model",
            messages,
            {"content": "Tenant A response"},
        )

        result = await get_cached_response(
            "tenant-b",
            "test-model",
            messages,
        )

    assert result is None
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_cached_response_uses_expiration():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    messages = [{"role": "user", "content": "Hello!"}]

    with patch("app.cache.redis_client", fake_redis):
        await set_cached_response(
            "tenant-a",
            "test-model",
            messages,
            {"content": "Cached response"},
        )

        key = build_cache_key("tenant-a", "test-model", messages)
        ttl = await fake_redis.ttl(key)

    assert 0 < ttl <= CACHE_TTL_SECONDS
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_cache_stores_valid_json():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    messages = [{"role": "user", "content": "Hello!"}]

    with patch("app.cache.redis_client", fake_redis):
        await set_cached_response(
            "tenant-a",
            "test-model",
            messages,
            {"content": "Cached response"},
        )

        key = build_cache_key("tenant-a", "test-model", messages)
        raw_value = await fake_redis.get(key)

    assert json.loads(raw_value) == {"content": "Cached response"}
    await fake_redis.aclose()
