"""Smoke tests for backend health routes."""

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """Ensure the health endpoint returns a successful response."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert response.json()["checks"]["storage"]["status"] == "ok"


def test_root_health_endpoint_returns_ok(client: TestClient) -> None:
    """Ensure the root health endpoint is available for infrastructure checks."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"]["database"]["status"] == "ok"
    assert response.json()["checks"]["storage"]["status"] == "ok"
