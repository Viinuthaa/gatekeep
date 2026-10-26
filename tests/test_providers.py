
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.providers as providers


@pytest.mark.asyncio
async def test_get_chat_completion_returns_expected_fields(monkeypatch):
    mock_response = SimpleNamespace(
        id="chatcmpl-test",
        model="qwen2.5:3b",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Hello from Ollama")
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=12,
            completion_tokens=8,
        ),
    )

    mock_create = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    result = await providers.get_chat_completion(
        model="requested-model",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result == {
        "id": "chatcmpl-test",
        "model": "qwen2.5:3b",
        "content": "Hello from Ollama",
        "prompt_tokens": 12,
        "completion_tokens": 8,
    }

    mock_create.assert_awaited_once_with(   
         model=providers.settings.OLLAMA_MODEL
        if providers.settings.AI_PROVIDER == "ollama"
        else "requested-model",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=180,
        temperature=0.2,
    )


@pytest.mark.asyncio
async def test_get_chat_completion_handles_missing_usage(monkeypatch):
    mock_response = SimpleNamespace(
        id="chatcmpl-no-usage",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Test response")
            )
        ],
        usage=None,
    )

    mock_create = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    result = await providers.get_chat_completion(
        model="test-model",
        messages=[{"role": "user", "content": "Test"}],
    )

    assert result["prompt_tokens"] == 0
    assert result["completion_tokens"] == 0
    assert result["content"] == "Test response"


@pytest.mark.asyncio
async def test_get_chat_completion_propagates_provider_errors(monkeypatch):
    mock_create = AsyncMock(side_effect=RuntimeError("Provider unavailable"))
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        await providers.get_chat_completion(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
