"""Unit: multitenancy.routers.cells.

Mini-app pattern: cells router + workspace_cells router included in a
fresh FastAPI, all DB / service deps overridden with AsyncMocks. Mirrors
the workspace router suite for consistency.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from src._shared.middleware.tenant_context import (
    get_current_cell_id,
    get_tenant_db_session,
)
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.multitenancy.exceptions import (
    CellNotFound,
    MemberNotFound,
    MultitenancyError,
)
from src.multitenancy.routers.cells import (
    get_cell_repo,
    get_cell_service,
    workspace_cells_router,
)
from src.multitenancy.routers.cells import (
    router as cells_router,
)
from src.rbac.exceptions import RbacError


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


def _fake_cell(*, slug: str = "default") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        slug=slug,
        display_name=slug.title(),
        vertical_template_slug=None,
        settings_jsonb={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        archived_at=None,
    )


def _fake_member() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        role_id=uuid4(),
        joined_at=datetime.now(UTC),
        invited_by=None,
        last_active_at=None,
    )


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


def _grant_session() -> AsyncMock:
    """Tenant session mock whose execute().first() returns a row → guard grants.

    The Phase 01.7 `require_cell_permission` guard reads cell_members via the
    tenant-scoped session; a truthy `.first()` = the caller is Owner. These
    router tests assert routing/mapping behaviour with an Owner caller; the
    Owner-allowed / Member-denied contract itself is covered by
    tests/rbac/test_require_cell_permission.py.
    """
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = (1,)
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.fixture
def client(mock_service: AsyncMock, mock_repo: AsyncMock) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(cells_router, prefix="/api/v1")
    app.include_router(workspace_cells_router, prefix="/api/v1")

    @app.exception_handler(MultitenancyError)
    async def _h(request: Request, exc: MultitenancyError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "title": exc.title},
        )

    @app.exception_handler(RbacError)
    async def _rbac_h(request: Request, exc: RbacError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code})

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_cell_service] = lambda: mock_service
    app.dependency_overrides[get_cell_repo] = lambda: mock_repo
    # Owner-grant guard deps (see _grant_session docstring).
    app.dependency_overrides[get_tenant_db_session] = _grant_session
    app.dependency_overrides[get_current_cell_id] = lambda: uuid4()

    yield TestClient(app)

    app.dependency_overrides.clear()


# ── POST /workspaces/{wsid}/cells ─────────────────────────────────────────


def test_create_cell_201(client: TestClient, mock_service: AsyncMock) -> None:
    cell = _fake_cell(slug="alpha")
    mock_service.provision_cell.return_value = cell
    workspace_id = uuid4()
    r = client.post(
        f"/api/v1/workspaces/{workspace_id}/cells",
        json={
            "slug": "alpha",
            "display_name": "Alpha",
            "vertical_template_slug": "wb-seller",
            "settings": {},
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "alpha"


def test_create_cell_slug_conflict_409(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.provision_cell.side_effect = IntegrityError(
        statement="INSERT INTO cells",
        params={},
        orig=Exception("duplicate"),
    )
    r = client.post(
        f"/api/v1/workspaces/{uuid4()}/cells",
        json={"slug": "dup", "display_name": "Dup"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "multitenancy.cell.slug_conflict"


# ── GET /workspaces/{wsid}/cells ──────────────────────────────────────────


def test_list_cells_200(client: TestClient, mock_repo: AsyncMock) -> None:
    mock_repo.list_by_workspace.return_value = [_fake_cell(), _fake_cell(slug="beta")]
    r = client.get(f"/api/v1/workspaces/{uuid4()}/cells")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2


# ── GET /cells/{id} ───────────────────────────────────────────────────────


def test_get_cell_200(client: TestClient, mock_repo: AsyncMock) -> None:
    cell = _fake_cell(slug="found")
    mock_repo.find_by_id.return_value = cell
    r = client.get(f"/api/v1/cells/{cell.id}")
    assert r.status_code == 200
    assert r.json()["slug"] == "found"


def test_get_cell_404(client: TestClient, mock_repo: AsyncMock) -> None:
    mock_repo.find_by_id.return_value = None
    r = client.get(f"/api/v1/cells/{uuid4()}")
    assert r.status_code == 404
    assert r.json()["code"] == "multitenancy.cell.not_found"


# ── /cells/{id}/members ───────────────────────────────────────────────────


def test_list_members_200(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.list_members.return_value = [_fake_member(), _fake_member()]
    r = client.get(f"/api/v1/cells/{uuid4()}/members")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_members_empty(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.list_members.return_value = []
    r = client.get(f"/api/v1/cells/{uuid4()}/members")
    assert r.status_code == 200
    assert r.json() == []


def test_invite_member_201(client: TestClient, mock_service: AsyncMock) -> None:
    inv_id = uuid4()
    when = datetime.now(UTC)
    mock_service.invite_member.return_value = (inv_id, when)
    r = client.post(
        f"/api/v1/cells/{uuid4()}/members/invite",
        json={"email": "i@x.dev", "role_id": str(uuid4())},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "i@x.dev"


def test_change_role_200(client: TestClient, mock_service: AsyncMock) -> None:
    member = _fake_member()
    mock_service.change_role.return_value = member
    r = client.patch(
        f"/api/v1/cells/{member.cell_id}/members/{member.user_id}",
        json={"role_id": str(uuid4())},
    )
    assert r.status_code == 200


def test_change_role_member_not_found_404(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.change_role.side_effect = MemberNotFound()
    r = client.patch(
        f"/api/v1/cells/{uuid4()}/members/{uuid4()}",
        json={"role_id": str(uuid4())},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "multitenancy.member.not_found"


def test_remove_member_204(client: TestClient, mock_service: AsyncMock) -> None:
    r = client.delete(f"/api/v1/cells/{uuid4()}/members/{uuid4()}")
    assert r.status_code == 204


def test_remove_member_not_found_404(client: TestClient, mock_service: AsyncMock) -> None:
    mock_service.remove_member.side_effect = MemberNotFound()
    r = client.delete(f"/api/v1/cells/{uuid4()}/members/{uuid4()}")
    assert r.status_code == 404


def test_get_cell_not_found_propagated(client: TestClient, mock_repo: AsyncMock) -> None:
    mock_repo.find_by_id.side_effect = CellNotFound()
    r = client.get(f"/api/v1/cells/{uuid4()}")
    assert r.status_code == 404
