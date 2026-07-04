"""Unit: require_cell_permission guard wired into a mini FastAPI app.

Exercises the Owner-allowed / Member-denied contract of the Phase 01.7 guard
without a database: the tenant-scoped session is an AsyncMock whose
``execute().first()`` is toggled to simulate the cell_members→permissions JOIN
returning a row (Owner grant) or nothing (Member deny → default-deny).

Covers:
  * Owner (row found) → guarded endpoint returns 200.
  * Member (no row) → guarded endpoint returns 403 rbac.permission_denied.
  * An UNGUARDED read endpoint returns 200 for BOTH roles (Option A: flat
    visibility — membership = cell access, reads are not gated).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from src._shared.middleware.tenant_context import (
    get_current_cell_id,
    get_tenant_db_session,
)
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.rbac.deps import require_cell_permission
from src.rbac.exceptions import RbacError
from src.rbac.permissions import MEMBER_INVITE


def _fake_user() -> AuthenticatedUser:
    user = SimpleNamespace(id=uuid4(), email="u@x.dev")
    return AuthenticatedUser(claims=None, user=user)  # type: ignore[arg-type]


def _session(*, grant: bool) -> AsyncMock:
    """AsyncMock session; execute().first() returns a row iff grant."""
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = (1,) if grant else None
    session.execute = AsyncMock(return_value=result)
    return session


def _make_client(*, grant: bool) -> Iterator[TestClient]:
    app = FastAPI()

    @app.exception_handler(RbacError)
    async def _rbac_h(request: Request, exc: RbacError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code})

    @app.post("/guarded", dependencies=[Depends(require_cell_permission(MEMBER_INVITE))])
    async def _guarded() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/open")
    async def _open(
        _auth: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    ) -> dict[str, str]:
        return {"ok": "read"}

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_tenant_db_session] = lambda: _session(grant=grant)
    app.dependency_overrides[get_current_cell_id] = lambda: uuid4()

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def owner_client() -> Iterator[TestClient]:
    yield from _make_client(grant=True)


@pytest.fixture
def member_client() -> Iterator[TestClient]:
    yield from _make_client(grant=False)


# ── Owner-only action ─────────────────────────────────────────────────────


def test_owner_allowed_on_guarded(owner_client: TestClient) -> None:
    r = owner_client.post("/guarded")
    assert r.status_code == 200
    assert r.json() == {"ok": "yes"}


def test_member_denied_on_guarded(member_client: TestClient) -> None:
    r = member_client.post("/guarded")
    assert r.status_code == 403
    assert r.json()["code"] == "rbac.permission_denied"


# ── flat visibility: reads are open to both roles ─────────────────────────


def test_owner_sees_open_read(owner_client: TestClient) -> None:
    assert owner_client.get("/open").status_code == 200


def test_member_sees_open_read(member_client: TestClient) -> None:
    # Member is NOT blocked on a read — Option A flat visibility.
    assert member_client.get("/open").status_code == 200
