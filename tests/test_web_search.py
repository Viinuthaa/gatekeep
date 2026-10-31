from unittest.mock import patch
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.web_search import (
    _extract_results,
    _fetch_official_python_release,
    _is_python_release_query,
    build_search_context,
    needs_web_search,
    search_web,
)


def test_needs_web_search_for_current_information():
    assert needs_web_search("What is the latest OpenAI news?")
    assert needs_web_search("What happened today?")
    assert not needs_web_search("Explain how photosynthesis works")


def test_extract_results_accepts_valid_urls():
    results, answer = _extract_results({
        "answer": "A search summary.",
        "results": [
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
        ],
    })

    assert len(results) == 1
    assert results[0]["title"] == "Example article"
    assert results[0]["url"] == "https://example.com/article"
    assert results[0]["snippet"] == "A short summary."
    assert answer == "A search summary."


def test_extract_results_handles_list_payload():
    results, answer = _extract_results([
        {
            "title": "Example article",
            "url": "https://example.com/article",
            "content": "A short summary.",
        }
    ])

    assert len(results) == 1
    assert answer == ""


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
    assert "official sources" in context.lower()


@pytest.mark.asyncio
async def test_search_web_handles_connection_failure():
    with patch(
        "app.web_search.httpx.AsyncClient",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        results, succeeded = await search_web("latest news")

    assert results == []
    assert succeeded is False

def test_detects_python_release_queries():
    assert _is_python_release_query("What is the latest Python version?")
    assert _is_python_release_query("Download stable Python release")
    assert not _is_python_release_query("Explain Python functions")


def test_builds_official_python_search_query():
    from app.web_search import _build_search_query

    query = _build_search_query("latest Python version")

    assert "python.org/downloads" in query


@pytest.mark.asyncio
async def test_fetches_official_python_release():
    mock_response = httpx.Response(
        200,
        text="<html><body>Latest Python 3 Release - Python 3.14.1</body></html>",
        request=httpx.Request(
            "GET",
            "https://www.python.org/downloads/windows/",
        ),
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await _fetch_official_python_release(mock_client)

    assert result is not None
    assert "3.14.1" in result["title"]
    assert "python.org" in result["url"]


@pytest.mark.asyncio
async def test_python_release_returns_none_for_unexpected_html():
    mock_response = httpx.Response(
        200,
        text="<html><body>Welcome to Python</body></html>",
        request=httpx.Request(
            "GET",
            "https://www.python.org/downloads/windows/",
        ),
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await _fetch_official_python_release(mock_client)

    assert result is None