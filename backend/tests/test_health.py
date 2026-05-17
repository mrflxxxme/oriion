"""Smoke tests for FastAPI app + /health endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from src import __version__
from src.main import API_DESCRIPTION, API_TITLE, HealthResponse, app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient bound to FastAPI app instance."""
    return TestClient(app)


def test_app_metadata() -> None:
    """FastAPI app exposes expected metadata."""
    assert app.title == API_TITLE
    assert app.description == API_DESCRIPTION
    assert app.version == __version__


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """GET /health returns 200 + structured HealthResponse."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "version": __version__}


def test_health_response_model_shape() -> None:
    """HealthResponse pydantic model has expected fields."""
    payload = HealthResponse(status="ok", version="9.9.9")
    assert payload.status == "ok"
    assert payload.version == "9.9.9"


def test_openapi_docs_available(client: TestClient) -> None:
    """Swagger UI mounted at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_redoc_disabled(client: TestClient) -> None:
    """ReDoc explicitly disabled (redoc_url=None per main.py)."""
    response = client.get("/redoc")
    assert response.status_code == 404
