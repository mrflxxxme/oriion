"""Router-wiring tests for the memory API (no DB; service + auth deps faked).

Validates request/response shapes, status codes, the soft-cap header, the
explicit «запомни» POST path, and that a missing entry maps to RFC-7807
``memory.entry_not_found`` (404). Real RLS + pgvector round-trip live in the
integration suite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest_asyncio
from httpx import ASGITransport
from src.memory.exceptions import MemoryEntryNotFound

_CELL = uuid4()
_WS = uuid4()
_USER = uuid4()
_NOW = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
# kept in sync with src.memory.routers.memory._SOFT_CAP_HEADER
_SOFT_CAP_HEADER = "X-Memory-Soft-Cap-Exceeded"


def _cell_entry(content: str = "remember me", **over: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "id": uuid4(),
        "cell_id": _CELL,
        "kind": "fact",
        "title": None,
        "content": content,
        "tags": [],
        "source": "manual",
        "contains_pii": False,
        "created_at": _NOW,
        "updated_at": _NOW,
    }
    base.update(over)
    return SimpleNamespace(**base)


def _role_entry(content: str = "prefers brevity", **over: Any) -> SimpleNamespace:
    entry = _cell_entry(content, **over)
    entry.agent_id = over.get("agent_id", uuid4())
    return entry


class _FakeCellSvc:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []
        self.over_cap = False
        self.raise_not_found = False
        self.deleted: list[UUID] = []
        self.search_hits: list[tuple[Any, float]] = []
        self.recent: list[Any] = []

    async def add(self, **kw: Any) -> tuple[Any, bool]:
        self.added.append(kw)
        return _cell_entry(kw["content"]), self.over_cap

    async def search(self, *, cell_id: UUID, query: str, limit: int) -> list[tuple[Any, float]]:
        self.last_query = query
        return self.search_hits

    async def list_recent(self, *, cell_id: UUID, limit: int, offset: int = 0) -> list[Any]:
        return self.recent

    async def delete(self, *, cell_id: UUID, entry_id: UUID) -> None:
        if self.raise_not_found:
            raise MemoryEntryNotFound(str(entry_id))
        self.deleted.append(entry_id)


class _FakeRoleSvc:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []
        self.over_cap = False
        self.deleted: list[UUID] = []
        self.recent: list[Any] = []

    async def add(self, **kw: Any) -> tuple[Any, bool]:
        self.added.append(kw)
        return _role_entry(kw["content"], agent_id=kw["agent_id"]), self.over_cap

    async def list_recent(
        self, *, cell_id: UUID, agent_id: UUID, limit: int, offset: int = 0
    ) -> list[Any]:
        return self.recent

    async def delete(self, *, cell_id: UUID, agent_id: UUID, entry_id: UUID) -> None:
        self.deleted.append(entry_id)


@pytest_asyncio.fixture
async def ctx() -> AsyncIterator[tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc]]:
    from src._shared.middleware.tenant_context import (
        get_current_cell_id,
        get_current_workspace_id,
    )
    from src.iam.middleware import get_current_user
    from src.main import app
    from src.memory.deps import get_cell_memory_service, get_role_memory_service

    cell_svc, role_svc = _FakeCellSvc(), _FakeRoleSvc()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user=SimpleNamespace(id=_USER)
    )
    app.dependency_overrides[get_current_cell_id] = lambda: _CELL
    app.dependency_overrides[get_current_workspace_id] = lambda: _WS
    app.dependency_overrides[get_cell_memory_service] = lambda: cell_svc
    app.dependency_overrides[get_role_memory_service] = lambda: role_svc

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, cell_svc, role_svc
    app.dependency_overrides.clear()


async def test_post_cell_memory_creates_and_passes_context(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, cell_svc, _ = ctx
    resp = await client.post(
        "/api/v1/memory", json={"content": "Client is in Kazan", "kind": "fact"}
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Client is in Kazan"
    assert "embedding" not in resp.json()  # vector never leaks
    assert _SOFT_CAP_HEADER not in resp.headers
    # service got the RLS-resolved cell/workspace/user, not client-supplied.
    call = cell_svc.added[0]
    assert call["cell_id"] == _CELL
    assert call["workspace_id"] == _WS
    assert call["created_by_user_id"] == _USER


async def test_post_cell_memory_sets_soft_cap_header(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, cell_svc, _ = ctx
    cell_svc.over_cap = True
    resp = await client.post("/api/v1/memory", json={"content": "x"})
    assert resp.status_code == 201
    assert resp.headers[_SOFT_CAP_HEADER] == "true"


async def test_search_returns_hits_with_scores(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, cell_svc, _ = ctx
    cell_svc.search_hits = [(_cell_entry("nearest"), 0.93)]
    resp = await client.get("/api/v1/memory/search", params={"q": "where", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["score"] == 0.93
    assert body[0]["entry"]["content"] == "nearest"
    assert cell_svc.last_query == "where"


async def test_delete_missing_maps_to_404_problem(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, cell_svc, _ = ctx
    cell_svc.raise_not_found = True
    resp = await client.delete(f"/api/v1/memory/{uuid4()}")
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    assert resp.json()["code"] == "memory.entry_not_found"


async def test_delete_existing_returns_204(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, cell_svc, _ = ctx
    entry_id = uuid4()
    resp = await client.delete(f"/api/v1/memory/{entry_id}")
    assert resp.status_code == 204
    assert cell_svc.deleted == [entry_id]


async def test_role_memory_post_and_delete(
    ctx: tuple[httpx.AsyncClient, _FakeCellSvc, _FakeRoleSvc],
) -> None:
    client, _, role_svc = ctx
    agent_id = uuid4()
    resp = await client.post(
        f"/api/v1/memory/agents/{agent_id}",
        json={"content": "wants weekly digests", "kind": "preference"},
    )
    assert resp.status_code == 201
    assert resp.json()["agent_id"] == str(agent_id)
    assert role_svc.added[0]["agent_id"] == agent_id

    entry_id = uuid4()
    del_resp = await client.delete(f"/api/v1/memory/agents/{agent_id}/{entry_id}")
    assert del_resp.status_code == 204
    assert role_svc.deleted == [entry_id]
