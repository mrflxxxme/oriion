"""Unit tests for ConversationHistoryService (fake repo / summarizer / sink).

Validates: FIFO trim to the window, summarize-on-overflow spilling into cell
memory before trimming, plain trim when no summarizer is wired, and chronological
recent().
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from src.memory.services.conversation_service import ConversationHistoryService

_CELL = uuid4()
_WS = uuid4()
_AGENT = uuid4()


class _FakeConvRepo:
    def __init__(self) -> None:
        self.msgs: list[Any] = []
        self._seq = 0

    async def append(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        agent_id: UUID,
        role: str,
        content: str,
        token_count: int | None = None,
    ) -> Any:
        self._seq += 1
        msg = SimpleNamespace(
            id=uuid4(), seq=self._seq, cell_id=cell_id, agent_id=agent_id, content=content
        )
        self.msgs.append(msg)
        return msg

    def _scoped(self, cell_id: UUID, agent_id: UUID) -> list[Any]:
        return sorted(
            (m for m in self.msgs if m.cell_id == cell_id and m.agent_id == agent_id),
            key=lambda m: m.seq,
        )

    async def count(self, cell_id: UUID, agent_id: UUID) -> int:
        return len(self._scoped(cell_id, agent_id))

    async def recent(self, cell_id: UUID, agent_id: UUID, *, limit: int) -> list[Any]:
        return self._scoped(cell_id, agent_id)[-limit:]

    async def oldest(self, cell_id: UUID, agent_id: UUID, count: int) -> list[Any]:
        return self._scoped(cell_id, agent_id)[:count]

    async def delete_ids(self, ids: Any) -> None:
        drop = set(ids)
        self.msgs = [m for m in self.msgs if m.id not in drop]


class _FakeSummarizer:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def summarize(self, messages: list[str]) -> str:
        self.calls.append(messages)
        return f"summary-of-{len(messages)}"


class _FakeCellMemory:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []

    async def add(self, **kw: Any) -> tuple[Any, bool]:
        self.added.append(kw)
        return SimpleNamespace(id=uuid4()), False


async def _append(svc: ConversationHistoryService, content: str, **kw: Any) -> Any:
    return await svc.append(
        cell_id=_CELL, workspace_id=_WS, agent_id=_AGENT, role="agent", content=content, **kw
    )


async def test_append_under_window_keeps_all() -> None:
    repo = _FakeConvRepo()
    svc = ConversationHistoryService(repo, window=3)  # type: ignore[arg-type]
    for i in range(3):
        await _append(svc, f"m{i}")
    assert await repo.count(_CELL, _AGENT) == 3


async def test_append_over_window_fifo_trims_without_summarizer() -> None:
    repo = _FakeConvRepo()
    svc = ConversationHistoryService(repo, window=3)  # type: ignore[arg-type]
    for i in range(5):
        await _append(svc, f"m{i}")
    remaining = [m.content for m in await svc.recent(cell_id=_CELL, agent_id=_AGENT)]
    assert remaining == ["m2", "m3", "m4"]  # oldest two dropped, chronological


async def test_overflow_summarized_into_cell_memory_then_trimmed() -> None:
    repo = _FakeConvRepo()
    summarizer = _FakeSummarizer()
    sink = _FakeCellMemory()
    svc = ConversationHistoryService(repo, window=2)  # type: ignore[arg-type]

    for i in range(4):
        await _append(svc, f"m{i}", summarizer=summarizer, cell_memory=sink)  # type: ignore[arg-type]

    # The window is 2; each append past 2 spills exactly the single oldest.
    assert summarizer.calls == [["m0"], ["m1"]]
    assert len(sink.added) == 2
    assert sink.added[0]["kind"] == "conversation_summary"
    assert sink.added[0]["source"] == "summary"
    remaining = [m.content for m in await svc.recent(cell_id=_CELL, agent_id=_AGENT)]
    assert remaining == ["m2", "m3"]


async def test_recent_returns_chronological_window() -> None:
    repo = _FakeConvRepo()
    svc = ConversationHistoryService(repo, window=10)  # type: ignore[arg-type]
    for i in range(5):
        await _append(svc, f"m{i}")
    got = [m.content for m in await svc.recent(cell_id=_CELL, agent_id=_AGENT, limit=2)]
    assert got == ["m3", "m4"]
