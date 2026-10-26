
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.web_search import (
    _extract_results,
    build_search_context,
    needs_web_search,
    search_web,
)


def test_needs_web_search_for_current_information():
    assert needs_web_search("What is the latest OpenAI news?")
    assert needs_web_search("What happened today?")
    assert not needs_web_search("Explain how photosynthesis works")


def test_extract_results_accepts_valid_urls():
    results = _extract_results([
        {
            "title": "Example article",
            "url": "https://example.com/article",
            "content": "A short summary.",
        },
        {
            "title": "Invalid URL",
            "url": "javascript:alert(1)",
            "content": "Should be ignored.",
        },
    ])

    assert len(results) == 1
    assert results[0]["title"] == "Example article"
    assert results[0]["url"] == "https://example.com/article"
    assert results[0]["snippet"] == "A short summary."


def test_build_search_context_includes_source_urls():
    context = build_search_context([
        {
            "title": "Example article",
            "url": "https://example.com/article",
            "snippet": "Useful information.",
        }
    ])

    assert "Example article" in context
    assert "https://example.com/article" in context
    assert "Useful information." in context


@pytest.mark.asyncio
async def test_search_web_handles_connection_failure():
    with patch(
        "app.web_search.httpx.AsyncClient",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        results, succeeded = await search_web("latest news")

    assert results == []
    assert succeeded is False
