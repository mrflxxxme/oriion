"""Smoke tests for Wave-0 stub routers.

These hit the routers via Starlette TestClient so the OpenAPI surface is
exercised — every stub handler returns 501 Not Implemented with the
canonical ErrorResponse envelope. Phase 00.5 swaps these for live wiring.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from src.llm_gateway.routers.byok import router as byok_router
from src.llm_gateway.routers.chat import router as chat_router
from src.llm_gateway.routers.embeddings import router as embeddings_router
from src.llm_gateway.routers.usage import router as usage_router
from starlette.testclient import TestClient


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(embeddings_router, prefix="/api/v1")
    app.include_router(byok_router, prefix="/api/v1")
    app.include_router(usage_router, prefix="/api/v1")
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app())


def test_chat_completion_stub_returns_501(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/llm/chat/completions",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )
    assert resp.status_code == 501
    body = resp.json()
    assert body["code"] == "llm_gateway.runtime_pending"


def test_embeddings_stub_returns_501(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/llm/embeddings",
        json={
            "provider_slug": "yandexgpt",
            "model": "text-search-doc",
            "input": "ping",
        },
    )
    assert resp.status_code == 501
    body = resp.json()
    assert body["code"] == "llm_gateway.runtime_pending"


def test_byok_create_stub_returns_501(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/llm/byok-keys",
        json={
            "provider_slug": "openai",
            "raw_api_key": "sk-test-very-long-fake-key",  # gitleaks:allow
            "label": "Marketing",
        },
    )
    assert resp.status_code == 501


def test_byok_list_stub_returns_501(client: TestClient) -> None:
    resp = client.get("/api/v1/llm/byok-keys")
    assert resp.status_code == 501


def test_byok_revoke_stub_returns_501(client: TestClient) -> None:
    resp = client.delete(f"/api/v1/llm/byok-keys/{uuid4()}")
    assert resp.status_code == 501


def test_usage_stub_returns_501(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/llm/usage",
        params={
            "from": "2026-05-01T00:00:00Z",
            "to": "2026-05-19T00:00:00Z",
        },
    )
    assert resp.status_code == 501
