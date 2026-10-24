
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_document_ingestion_and_search():
    document_id = f"doc-{uuid4().hex}"
    headers = {"Authorization": "Bearer gk_test_demo_key"}

    ingest_response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={
            "document_id": document_id,
            "text": "Gatekeep protects LLM requests using authentication and rate limiting.",
        },
    )

    assert ingest_response.status_code == 200
    assert ingest_response.json()["chunks_created"] == 1

    search_response = client.post(
        "/api/v1/documents/search",
        headers=headers,
        json={
            "query": "authentication rate limiting",
            "limit": 5,
        },
    )

    assert search_response.status_code == 200
    data = search_response.json()
    assert data["result_count"] >= 1
    assert any(
        result["document_id"] == document_id
        for result in data["results"]
    )


def test_document_search_is_tenant_isolated():
    document_id = f"private-{uuid4().hex}"

    client.post(
        "/api/v1/documents",
        headers={"Authorization": "Bearer gk_test_demo_key"},
        json={
            "document_id": document_id,
            "text": "Unique information about photosynthesis and chlorophyll.",
        },
    )

    response = client.post(
        "/api/v1/documents/search",
        headers={"Authorization": "Bearer invalid-key"},
        json={
            "query": "photosynthesis chlorophyll",
            "limit": 5,
        },
    )

    assert response.status_code == 401


def test_document_ingestion_requires_api_key():
    response = client.post(
        "/api/v1/documents",
        json={
            "document_id": "unauthorized-doc",
            "text": "This should not be ingested.",
        },
    )

    assert response.status_code == 401


def test_document_search_requires_api_key():
    response = client.post(
        "/api/v1/documents/search",
        json={
            "query": "Gatekeep",
            "limit": 5,
        },
    )

    assert response.status_code == 401


def test_empty_document_is_rejected_by_validation():
    response = client.post(
        "/api/v1/documents",
        headers={"Authorization": "Bearer gk_test_demo_key"},
        json={
            "document_id": f"empty-{uuid4().hex}",
            "text": "",
        },
    )

    assert response.status_code == 422


def test_invalid_search_limit_is_rejected():
    response = client.post(
        "/api/v1/documents/search",
        headers={"Authorization": "Bearer gk_test_demo_key"},
        json={
            "query": "Gatekeep",
            "limit": 0,
        },
    )

    assert response.status_code == 422
