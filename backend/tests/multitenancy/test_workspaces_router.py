"""Unit: multitenancy.routers.workspaces.

Mini-app pattern (matches tests/llm_gateway/test_routers_stubs.py):
construct a FastAPI instance that includes only the workspaces router
and override the FastAPI dependencies (auth + workspace service) with
mocks. Exercises the router glue WITHOUT requiring the routers to be
mounted in src/main.py (their main.py inclusion is Phase 00.5 work per
src/multitenancy/routers/cells.py:11 docstring).

Coverage target per Phase 00.2.5 §6: multitenancy ≥85%.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.multitenancy.exceptions import MultitenancyError, WorkspaceNotFound
from src.multitenancy.routers.workspaces import (
    get_workspace_service,
)
from src.multitenancy.routers.workspaces import (
    router as workspaces_router,
)


def _install_multitenancy_handler(app: FastAPI) -> None:
    """Mirror the production handler so 404/409 surface cleanly in tests."""

    @app.exception_handler(MultitenancyError)
    async def _h(request: Request, exc: MultitenancyError) -> JSONResponse:
        body = {"code": exc.code, "title": exc.title, "status": exc.status_code}
        if exc.detail:
            body["detail"] = exc.detail
        return JSONResponse(status_code=exc.status_code, content=body)


def _fake_user() -> AuthenticatedUser:
    user = SimpleNamespace(
        id=uuid4(),
        email="auth@example.com",
        email_verified_at=datetime.now(UTC),
        display_name="Auth User",
        locale="ru-RU",
        timezone="Europe/Moscow",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return AuthenticatedUser(claims=None, user=user)  # type: ignore[arg-type]


def _fake_workspace(*, slug: str = "acme-corp", display_name: str = "Acme Corp") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        slug=slug,
        display_name=display_name,
        billing_email=None,
        country_code="RU",
        timezone="Europe/Moscow",
        plan_tier="free",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_service: AsyncMock) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(workspaces_router, prefix="/api/v1")
    _install_multitenancy_handler(app)

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_workspace_service] = lambda: mock_service

    yield TestClient(app)

    app.dependency_overrides.clear()


# ── POST /workspaces ──────────────────────────────────────────────────────


def test_create_workspace_201(client: TestClient, mock_service: AsyncMock) -> None:
    ws = _fake_workspace(slug="acme", display_name="Acme")
    mock_service.create_workspace.return_value = ws

    r = client.post(
        "/api/v1/workspaces",
        json={"display_name": "Acme", "slug": "acme"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "acme"
    assert body["plan_tier"] == "free"


def test_create_workspace_slug_conflict_409(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.create_workspace.side_effect = IntegrityError(
        statement="INSERT INTO workspaces ...",
        params={},
        orig=Exception("duplicate key value violates unique constraint"),
    )
    r = client.post(
        "/api/v1/workspaces",
        json={"display_name": "Dup", "slug": "dup"},
    )
    assert r.status_code == 409


def test_create_workspace_unauthenticated_routes_through_iam_middleware() -> None:
    """Without the get_current_user override, the iam middleware rejects."""
    from src.iam.exceptions import IamError, TokenInvalid

    app = FastAPI()
    app.include_router(workspaces_router, prefix="/api/v1")

    @app.exception_handler(IamError)
    async def _iam(request: Request, exc: IamError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code})

    c = TestClient(app)
    r = c.post(
        "/api/v1/workspaces",
        json={"display_name": "Anon", "slug": "anon"},
    )
    # iam middleware raises TokenInvalid → 401 via the installed handler.
    assert r.status_code == 401
    assert r.json()["code"] == TokenInvalid().code


# ── GET /workspaces ───────────────────────────────────────────────────────


def test_list_workspaces_200(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.list_for_user.return_value = [
        _fake_workspace(slug="one"),
        _fake_workspace(slug="two"),
    ]
    r = client.get("/api/v1/workspaces")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert {w["slug"] for w in body["items"]} == {"one", "two"}
    assert body["next_cursor"] is None


def test_list_workspaces_empty(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.list_for_user.return_value = []
    r = client.get("/api/v1/workspaces")
    assert r.status_code == 200
    assert r.json() == {"items": [], "next_cursor": None}


# ── GET /workspaces/{id} ──────────────────────────────────────────────────


def test_get_workspace_by_id_200(client: TestClient, mock_service: AsyncMock) -> None:
    ws = _fake_workspace(slug="found")
    mock_service.find_by_id.return_value = ws

    r = client.get(f"/api/v1/workspaces/{ws.id}")
    assert r.status_code == 200
    assert r.json()["slug"] == "found"


def test_get_workspace_by_id_404(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.find_by_id.return_value = None
    r = client.get(f"/api/v1/workspaces/{uuid4()}")
    assert r.status_code == 404
    assert r.json()["code"] == "multitenancy.workspace.not_found"
    assert mock_service.find_by_id.await_count == 1


def test_get_workspace_by_id_propagates_workspace_not_found(
    client: TestClient, mock_service: AsyncMock
) -> None:
    mock_service.find_by_id.side_effect = WorkspaceNotFound()
    r = client.get(f"/api/v1/workspaces/{uuid4()}")
    assert r.status_code == 404
