"""Unit tests for cell/role memory services (fake repo + deterministic embedder).

No DB, no network. Validates: embed-on-store, soft-cap flagging, distance→
similarity conversion, agent scoping, delete-missing → 404, and that an
embedding failure aborts the write (nothing inserted).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from src.memory.exceptions import EmbeddingUnavailable, MemoryEntryNotFound
from src.memory.models import CELL_MEMORY_SOFT_CAP, ROLE_MEMORY_SOFT_CAP
from src.memory.services.memory_service import (
    CellMemoryService,
    cosine_similarity_from_distance,
)
from src.memory.services.role_memory_service import RoleMemoryService

from tests.memory._fakes import DeterministicEmbedder, FailingEmbedder


class _FakeCellRepo:
    def __init__(
        self,
        *,
        count: int = 0,
        search: list[tuple[Any, float]] | None = None,
        delete_ok: bool = True,
    ) -> None:
        self.inserted: list[dict[str, Any]] = []
        self._count = count
        self._search = search or []
        self._delete_ok = delete_ok

    async def insert(self, **kw: Any) -> Any:
        self.inserted.append(kw)
        return SimpleNamespace(id=uuid4(), **kw)

    async def count_by_cell(self, cell_id: Any) -> int:
        return self._count

    async def search_by_embedding(
        self, cell_id: Any, query_embedding: Any, *, limit: int
    ) -> list[tuple[Any, float]]:
        return self._search[:limit]

    async def list_recent(self, cell_id: Any, *, limit: int, offset: int = 0) -> list[Any]:
        return []

    async def delete_by_id(self, entry_id: Any, *, cell_id: Any) -> bool:
        return self._delete_ok


async def test_add_embeds_and_stores_under_cap() -> None:
    repo = _FakeCellRepo(count=1)
    emb = DeterministicEmbedder()
    svc = CellMemoryService(repo, emb)  # type: ignore[arg-type]

    entry, over_cap = await svc.add(
        cell_id=uuid4(), workspace_id=uuid4(), content="customer prefers VK over Telegram"
    )

    assert over_cap is False
    assert entry.id is not None
    # embedded via the DOCUMENT model, 256-dim, model label persisted.
    assert emb.embed_documents_calls == [["customer prefers VK over Telegram"]]
    assert emb.embed_query_calls == []
    assert len(repo.inserted[0]["embedding"]) == 256
    assert repo.inserted[0]["embedding_model"] == "fake/deterministic-256"


async def test_add_flags_soft_cap_but_still_stores() -> None:
    repo = _FakeCellRepo(count=CELL_MEMORY_SOFT_CAP + 1)
    svc = CellMemoryService(repo, DeterministicEmbedder())  # type: ignore[arg-type]

    _, over_cap = await svc.add(cell_id=uuid4(), workspace_id=uuid4(), content="x")

    assert over_cap is True
    assert len(repo.inserted) == 1  # soft cap does NOT block the write


async def test_search_uses_query_model_and_converts_distance() -> None:
    near, far = SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())
    repo = _FakeCellRepo(search=[(near, 0.0), (far, 0.25)])
    emb = DeterministicEmbedder()
    svc = CellMemoryService(repo, emb)  # type: ignore[arg-type]

    hits = await svc.search(cell_id=uuid4(), query="loyalty program", limit=5)

    assert emb.embed_query_calls == ["loyalty program"]
    assert hits[0] == (near, 1.0)
    assert hits[1][1] == pytest.approx(0.75)


async def test_delete_missing_raises_not_found() -> None:
    repo = _FakeCellRepo(delete_ok=False)
    svc = CellMemoryService(repo, DeterministicEmbedder())  # type: ignore[arg-type]

    with pytest.raises(MemoryEntryNotFound):
        await svc.delete(cell_id=uuid4(), entry_id=uuid4())


async def test_add_aborts_on_embedding_failure() -> None:
    repo = _FakeCellRepo()
    svc = CellMemoryService(repo, FailingEmbedder())  # type: ignore[arg-type]

    with pytest.raises(EmbeddingUnavailable):
        await svc.add(cell_id=uuid4(), workspace_id=uuid4(), content="x")

    assert repo.inserted == []  # embed failed before any insert


def test_similarity_helper() -> None:
    assert cosine_similarity_from_distance(0.0) == 1.0
    assert cosine_similarity_from_distance(0.3) == pytest.approx(0.7)
    assert cosine_similarity_from_distance(2.0) == pytest.approx(-1.0)


# ── role memory ───────────────────────────────────────────────────────── #


class _FakeRoleRepo:
    def __init__(self, *, count: int = 0, delete_ok: bool = True) -> None:
        self.inserted: list[dict[str, Any]] = []
        self._count = count
        self._delete_ok = delete_ok

    async def insert(self, **kw: Any) -> Any:
        self.inserted.append(kw)
        return SimpleNamespace(id=uuid4(), **kw)

    async def count_by_agent(self, cell_id: Any, agent_id: Any) -> int:
        return self._count

    async def delete_by_id(self, entry_id: Any, *, agent_id: Any) -> bool:
        return self._delete_ok


async def test_role_add_scopes_agent_and_flags_cap() -> None:
    repo = _FakeRoleRepo(count=ROLE_MEMORY_SOFT_CAP + 1)
    svc = RoleMemoryService(repo, DeterministicEmbedder())  # type: ignore[arg-type]
    agent_id = uuid4()

    _, over_cap = await svc.add(
        cell_id=uuid4(), workspace_id=uuid4(), agent_id=agent_id, content="prefers concise replies"
    )

    assert over_cap is True
    assert repo.inserted[0]["agent_id"] == agent_id


async def test_role_delete_missing_raises_not_found() -> None:
    repo = _FakeRoleRepo(delete_ok=False)
    svc = RoleMemoryService(repo, DeterministicEmbedder())  # type: ignore[arg-type]

    with pytest.raises(MemoryEntryNotFound):
        await svc.delete(cell_id=uuid4(), agent_id=uuid4(), entry_id=uuid4())
