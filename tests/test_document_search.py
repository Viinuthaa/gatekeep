
import pytest

from app.document_search import DocumentSearch


def test_add_document_returns_chunks():
    search = DocumentSearch(chunk_size=5, chunk_overlap=1)

    chunks = search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="Python makes building APIs easier and faster",
    )

    assert len(chunks) == 2
    assert chunks[0].text == "Python makes building APIs easier"
    assert chunks[1].text == "easier and faster"
    assert chunks[0].tenant_id == "tenant-a"


def test_search_finds_relevant_document():
    search = DocumentSearch()

    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="FastAPI is a Python framework for building APIs",
    )
    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-2",
        text="Photosynthesis converts light energy into chemical energy",
    )

    results = search.search("tenant-a", "Python framework APIs")

    assert results
    assert results[0]["document_id"] == "doc-1"
    assert results[0]["score"] == 1.0


def test_search_returns_empty_for_unrelated_query():
    search = DocumentSearch()

    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="FastAPI is a Python framework",
    )

    results = search.search("tenant-a", "volcanic eruption")

    assert results == []


def test_tenant_cannot_search_another_tenants_documents():
    search = DocumentSearch()

    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="Secret information about project Gatekeep",
    )

    results = search.search("tenant-b", "Secret information")

    assert results == []


def test_search_respects_result_limit():
    search = DocumentSearch()

    for index in range(4):
        search.add_document(
            tenant_id="tenant-a",
            document_id=f"doc-{index}",
            text="Python API framework",
        )

    results = search.search("tenant-a", "Python API", limit=2)

    assert len(results) == 2


def test_adding_same_document_replaces_old_chunks():
    search = DocumentSearch()

    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="Old content about biology",
    )
    search.add_document(
        tenant_id="tenant-a",
        document_id="doc-1",
        text="New content about chemistry",
    )

    assert search.search("tenant-a", "biology") == []
    results = search.search("tenant-a", "chemistry")
    assert len(results) == 1
    assert results[0]["document_id"] == "doc-1"


def test_empty_document_is_rejected():
    search = DocumentSearch()

    with pytest.raises(ValueError):
        search.add_document("tenant-a", "doc-1", "   ")


def test_invalid_chunk_settings_are_rejected():
    with pytest.raises(ValueError):
        DocumentSearch(chunk_size=0)

    with pytest.raises(ValueError):
        DocumentSearch(chunk_size=5, chunk_overlap=5)


def test_invalid_search_limit_is_rejected():
    search = DocumentSearch()

    with pytest.raises(ValueError):
        search.search("tenant-a", "Python", limit=0)
