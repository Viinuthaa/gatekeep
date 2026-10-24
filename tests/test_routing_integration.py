
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_response_includes_routing_metadata():
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
        ) as provider,
        patch(
            "app.main.get_cached_response",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi there"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["routing"]["complexity"] == "simple"
    assert response.json()["routing"]["selected_model"] == "test-model"
    assert response.json()["cache_hit"] is False
    provider.assert_awaited_once()


def test_chat_response_uses_cached_result():
    cached_result = {
        "id": "cached-response",
        "model": "test-model",
        "content": "Cached answer",
        "prompt_tokens": 10,
        "completion_tokens": 8,
    }

    with (
        patch(
            "app.main.get_chat_completion",
            new_callable=AsyncMock,
        ) as provider,
        patch(
            "app.main.get_cached_response",
            new_callable=AsyncMock,
            return_value=cached_result,
        ),
        patch("app.main.set_cached_response", new_callable=AsyncMock),
        patch("app.main.check_rate_limit", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/chat/completions",
            headers={"Authorization": "Bearer gk_test_demo_key"},
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi there"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["content"] == "Cached answer"
    assert response.json()["cache_hit"] is True
    assert response.json()["prompt_tokens"] == 0
    provider.assert_not_awaited()
