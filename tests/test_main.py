
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.limiter import check_rate_limit
from app.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to Gatekeep!"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_unknown_route():
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404


def test_api_info():
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json()["name"] == "Gatekeep"
    assert response.json()["version"] == "0.1.0"


def test_valid_chat_request():
    response = client.post(
        "/api/v1/chat/completions/validate",
        json={
            "model": "example-model",
            "messages": [{"role": "user", "content": "Hello Gatekeep!"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["message_count"] == 1


def test_invalid_chat_request():
    response = client.post(
        "/api/v1/chat/completions/validate",
        json={"model": "example-model", "messages": []},
    )
    assert response.status_code == 422


def test_invalid_message_role():
    response = client.post(
        "/api/v1/chat/completions/validate",
        json={
            "model": "example-model",
            "messages": [{"role": "banana", "content": "Hello!"}],
        },
    )
    assert response.status_code == 422


def test_chat_completions():
    mock_result = {
        "id": "test-response",
        "model": "test-model",
        "content": "Hello from Gatekeep!",
        "prompt_tokens": 5,
        "completion_tokens": 4,
    }

    with (
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello!"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["content"] == "Hello from Gatekeep!"
    assert response.json()["model"] == "test-model"
    assert response.json()["tenant_id"] == "demo-tenant"


def test_chat_completions_without_api_key():
    response = client.post(
        "/api/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        },
    )
    assert response.status_code == 401


def test_chat_completions_with_invalid_api_key():
    response = client.post(
        "/api/v1/chat/completions",
        headers={"Authorization": "Bearer wrong-key"},
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_allows_requests():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch("app.limiter.redis_client", fake_redis):
        await check_rate_limit("tenant-test")
        await check_rate_limit("tenant-test")

    assert await fake_redis.get("rate_limit:tenant-test") == "2"
    await fake_redis.aclose()


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess_requests():
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch("app.limiter.redis_client", fake_redis):
        for _ in range(20):
            await check_rate_limit("tenant-test")

        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("tenant-test")

        assert exc_info.value.status_code == 429

    await fake_redis.aclose()


def test_current_question_triggers_web_search():
    mock_result = {
        "id": "test-response",
        "model": "test-model",
        "content": "OpenAI announced a new feature.",
        "prompt_tokens": 10,
        "completion_tokens": 8,
    }
    search_results = [
        {
            "title": "Official announcement",
            "url": "https://example.com/news",
            "snippet": "Details of the announcement.",
        }
    ]

    with (
        patch(
            "app.main.search_web",
            new_callable=AsyncMock,
            return_value=(search_results, True),
        ) as mock_search,
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_ai,
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
        patch("app.main.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the latest OpenAI news?",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["search_used"] is True
    assert response.json()["search_status"] == "success"
    mock_search.assert_awaited_once()
    ai_messages = mock_ai.await_args.kwargs["messages"]
    assert "https://example.com/news" in ai_messages[0]["content"]


def test_normal_question_skips_web_search():
    mock_result = {
        "id": "test-response",
        "model": "test-model",
        "content": "Photosynthesis converts light energy into chemical energy.",
        "prompt_tokens": 10,
        "completion_tokens": 8,
    }

    with (
        patch(
            "app.main.search_web",
            new_callable=AsyncMock,
        ) as mock_search,
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
        patch("app.main.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain photosynthesis.",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["search_used"] is False
    assert response.json()["search_status"] == "not_needed"
    mock_search.assert_not_awaited()


def test_search_failure_still_attempts_ai_response():
    mock_result = {
        "id": "test-response",
        "model": "test-model",
        "content": "I could not verify the latest information.",
        "prompt_tokens": 10,
        "completion_tokens": 8,
    }

    with (
        patch(
            "app.main.search_web",
            new_callable=AsyncMock,
            return_value=([], False),
        ),
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_ai,
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
        patch("app.main.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the latest OpenAI news?",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["search_used"] is False
    assert response.json()["search_status"] == "unavailable"
    mock_ai.assert_awaited_once()


def test_successful_search_without_results_is_reported():
    mock_result = {
        "id": "test-response",
        "model": "test-model",
        "content": "I could not find recent sources.",
        "prompt_tokens": 10,
        "completion_tokens": 8,
    }

    with (
        patch(
            "app.main.search_web",
            new_callable=AsyncMock,
            return_value=([], True),
        ),
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
        patch("app.main.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the latest OpenAI news?",
                    }
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["search_used"] is False
    assert response.json()["search_status"] == "no_results"
