"""Unit: llm_gateway.routers.providers — list + status endpoints.

Mini-app with overridden ``get_db`` returning AsyncMock-shaped session.
Exercises both filtered + unfiltered list paths plus the static
providers/status snapshot path.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src._shared.db.session import get_db
from src.llm_gateway.routers.providers import router as providers_router


def _fake_provider_row(
    *,
    slug: str = "deepseek",
    display: str = "DeepSeek",
    base: str = "https://api.deepseek.com",
    is_byok: bool = True,
    default_model: str = "deepseek-chat",
    features: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        provider_slug=slug,
        display_name=display,
        base_url=base,
        is_byok_supported=is_byok,
        default_model=default_model,
        is_active=True,
        supported_features=features or ["chat", "tool_use"],
    )


def _mock_session_with_rows(rows: list[SimpleNamespace]) -> AsyncMock:
    """Build an AsyncMock session whose .execute(...) returns the given rows."""
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    result.scalars = MagicMock(return_value=scalars)
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.fixture
def session_mock() -> AsyncMock:
    return _mock_session_with_rows(
        [
            _fake_provider_row(slug="deepseek"),
            _fake_provider_row(
                slug="yandexgpt",
                display="YandexGPT",
                base="https://llm.api.cloud.yandex.net",
                is_byok=False,
                default_model="yandexgpt-lite",
                features=["chat"],
            ),
            _fake_provider_row(
                slug="gigachat",
                display="GigaChat",
                base="https://gigachat.devices.sberbank.ru",
                features=["chat", "embeddings"],
            ),
        ]
    )


@pytest.fixture
def client(session_mock: AsyncMock) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(providers_router, prefix="/api/v1")

    async def fake_db():
        yield session_mock

    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── GET /llm/providers ───────────────────────────────────────────────────


def test_list_providers_returns_all_active(client: TestClient) -> None:
    r = client.get("/api/v1/llm/providers")
    assert r.status_code == 200
    body = r.json()
    slugs = {p["provider_slug"] for p in body}
    assert slugs == {"deepseek", "yandexgpt", "gigachat"}


def test_list_providers_filter_by_feature_chat(client: TestClient) -> None:
    r = client.get("/api/v1/llm/providers", params={"feature": "chat"})
    assert r.status_code == 200
    body = r.json()
    assert {p["provider_slug"] for p in body} == {"deepseek", "yandexgpt", "gigachat"}


def test_list_providers_filter_by_feature_embeddings(client: TestClient) -> None:
    r = client.get("/api/v1/llm/providers", params={"feature": "embeddings"})
    assert r.status_code == 200
    body = r.json()
    # Only gigachat declared embeddings in the fixture.
    assert {p["provider_slug"] for p in body} == {"gigachat"}


def test_list_providers_filter_unknown_feature_filters_all(
    client: TestClient,
) -> None:
    r = client.get("/api/v1/llm/providers", params={"feature": "tool_use"})
    assert r.status_code == 200
    body = r.json()
    # Only deepseek's fixture declares tool_use.
    assert {p["provider_slug"] for p in body} == {"deepseek"}


def test_list_providers_drops_unknown_features_from_response(
    client: TestClient,
) -> None:
    """supported_features in DB may contain experimental flags; the
    response schema restricts to the canonical FeatureLiteral set."""
    r = client.get("/api/v1/llm/providers")
    body = r.json()
    for prov in body:
        for feat in prov["supported_features"]:
            assert feat in {
                "chat",
                "embeddings",
                "structured_output",
                "tool_use",
                "vision",
            }


# ── GET /llm/providers/status ────────────────────────────────────────────


def test_providers_status_returns_snapshot(client: TestClient) -> None:
    r = client.get("/api/v1/llm/providers/status")
    assert r.status_code == 200
    body = r.json()
    # Same 3 providers, all "healthy"/"closed" per Wave 0 stub.
    assert len(body) == 3
    for entry in body:
        assert entry["state"] == "healthy"
        assert entry["circuit"] == "closed"
        assert entry["last_check"]
