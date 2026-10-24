
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

HEADERS = {"Authorization": "Bearer gk_test_demo_key"}


def test_evaluation_endpoint_returns_report():
    response = client.post(
        "/api/v1/evaluations/run",
        headers=HEADERS,
        json={
            "cases": [
                {
                    "name": "passing case",
                    "response": "Gatekeep protects LLM requests.",
                    "expected_contains": ["Gatekeep", "protects"],
                    "expected_not_contains": ["failure"],
                },
                {
                    "name": "failing case",
                    "response": "Some unrelated response.",
                    "expected_contains": ["Gatekeep"],
                    "expected_not_contains": [],
                },
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["tenant_id"] == "demo-tenant"
    assert data["total_cases"] == 2
    assert data["passed_cases"] == 1
    assert data["failed_cases"] == 1
    assert data["pass_rate"] == 50.0


def test_evaluation_endpoint_requires_api_key():
    response = client.post(
        "/api/v1/evaluations/run",
        json={
            "cases": [
                {
                    "name": "test case",
                    "response": "Gatekeep",
                    "expected_contains": ["Gatekeep"],
                    "expected_not_contains": [],
                }
            ]
        },
    )

    assert response.status_code == 401


def test_evaluation_endpoint_rejects_empty_cases():
    response = client.post(
        "/api/v1/evaluations/run",
        headers=HEADERS,
        json={"cases": []},
    )

    assert response.status_code == 422
