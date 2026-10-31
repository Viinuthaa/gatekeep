
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
                message=SimpleNamespace(
                    content="Hello from Ollama",
                    refusal=None,
                ),
                finish_reason="stop",
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

    if providers.settings.AI_PROVIDER == "ollama":
        expected_model = providers.settings.OLLAMA_MODEL
    elif providers.settings.AI_PROVIDER == "openrouter":
        expected_model = providers.settings.OPENROUTER_MODEL
    else:
        expected_model = "requested-model"

    mock_create.assert_awaited_once_with(
        model=expected_model,
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=500,
        temperature=0.2,
    )


@pytest.mark.asyncio
async def test_get_chat_completion_handles_missing_usage(monkeypatch):
    mock_response = SimpleNamespace(
        id="chatcmpl-no-usage",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Test response",
                    refusal=None,
                ),
                finish_reason="stop",
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
    mock_create = AsyncMock(
        side_effect=RuntimeError("Provider unavailable")
    )
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


@pytest.mark.asyncio
async def test_get_chat_completion_rejects_empty_content(monkeypatch):
    mock_response = SimpleNamespace(
        id="chatcmpl-empty",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, refusal=None),
                finish_reason="length",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=100,
        ),
    )

    mock_create = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    with pytest.raises(RuntimeError, match="returned no text content"):
        await providers.get_chat_completion(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
@pytest.mark.asyncio
async def test_get_chat_completion_rejects_reasoning_without_content(
    monkeypatch,
):
    mock_response = SimpleNamespace(
        id="chatcmpl-reasoning",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    refusal=None,
                    reasoning="The answer is being calculated.",
                ),
                finish_reason="stop",
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

    with pytest.raises(RuntimeError, match="returned no text content"):
        await providers.get_chat_completion(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
        )

@pytest.mark.asyncio
async def test_get_chat_completion_retries_empty_response(monkeypatch):
    empty_response = SimpleNamespace(
        id="empty",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, refusal=None),
                finish_reason="stop",
            )
        ],
        usage=None,
    )

    valid_response = SimpleNamespace(
        id="success",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Successful retry", refusal=None),
                finish_reason="stop",
            )
        ],
        usage=None,
    )

    mock_create = AsyncMock(
        side_effect=[empty_response, valid_response]
    )
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    result = await providers.get_chat_completion(
        model="test-model",
        messages=[{"role": "user", "content": "Hello"}],
    )

    assert result["content"] == "Successful retry"
    assert mock_create.await_count == 2


@pytest.mark.asyncio
async def test_get_chat_completion_fails_after_two_empty_responses(monkeypatch):
    empty_response = SimpleNamespace(
        id="empty",
        model="test-model",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, refusal=None),
                finish_reason="stop",
            )
        ],
        usage=None,
    )

    mock_create = AsyncMock(return_value=empty_response)
    monkeypatch.setattr(
        providers.client.chat.completions,
        "create",
        mock_create,
    )

    with pytest.raises(RuntimeError, match="no text content after retrying"):
        await providers.get_chat_completion(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
        )

    assert mock_create.await_count == 2