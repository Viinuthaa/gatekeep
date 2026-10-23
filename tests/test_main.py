
from fastapi.testclient import TestClient

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
