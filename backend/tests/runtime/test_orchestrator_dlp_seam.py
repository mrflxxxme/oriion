"""Unit: orchestrator ``output_dlp`` seam (Phase 01.6, ADR-039).

Drives ``execute_agent_task`` with fakes (no PG / no LLM) to assert the A3
hard-block seam: default-None no-op, a clean screen lets the task succeed, and a
``DlpViolation`` stamps ``task.failed`` (code ``security.dlp.blocked``, no raw
PII in the SSE) + runs before memory extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.security.exceptions import DlpViolation
from src.tasks.models import Task


class _FakeOutput(BaseModel):
    summary: str = "demo output"


@dataclass
class _FakeRunResult:
    output: _FakeOutput = field(default_factory=_FakeOutput)


class _FakeAgent:
    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:
        return _FakeRunResult()


@dataclass
class _StubSession:
    task: Task | None = None

    async def get(self, _model: Any, _task_id: UUID) -> Task | None:
        return self.task


def _task(task_id: UUID) -> Task:
    t = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="t",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "p"},
    )
    t.id = task_id
    t.total_cost_credits = Decimal(0)
    t.total_input_tokens = 0
    t.total_output_tokens = 0
    return t


async def _noop_leaf(_inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
    raise AssertionError("leaf should not fire")


class _Screen:
    """Records the deliverable it screened; optionally raises DlpViolation."""

    def __init__(self, *, raise_categories: list[str] | None = None) -> None:
        self.calls: list[str] = []
        self._raise = raise_categories

    async def __call__(self, deliverable: str) -> None:
        self.calls.append(deliverable)
        if self._raise is not None:
            raise DlpViolation(self._raise)


class _MemHook:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def __call__(self, deliverable: str, step_index: int) -> tuple[Decimal, int, int]:
        self.calls.append((deliverable, step_index))
        return (Decimal(0), 0, 0)


@pytest.fixture
def _emit() -> Any:
    with patch("src.runtime.orchestrator.tasks_events") as m:
        m.emit_task_started = AsyncMock()
        m.emit_task_completed = AsyncMock()
        m.emit_task_failed = AsyncMock()
        yield m


async def _run(task: Task, publisher: InProcessSSEPublisher, screen: Any, mem: Any = None) -> None:
    await execute_agent_task(
        task_id=task.id,
        cell_id=uuid4(),
        user_id=uuid4(),
        coordinator_agent=_FakeAgent(),  # type: ignore[arg-type]
        user_prompt="p",
        available_agent_slugs=["researcher"],
        leaf_runner=_noop_leaf,
        sse_publisher=publisher,
        session=_StubSession(task=task),  # type: ignore[arg-type]
        memory_extraction=mem,
        output_dlp=screen,
    )


@pytest.mark.asyncio
async def test_default_none_is_noop(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    await _run(task, publisher, None)
    assert task.status == "succeeded"
    types = [ev.event_type for ev in publisher._drain.get(task.id, [])]
    assert "task.failed" not in types


@pytest.mark.asyncio
async def test_clean_screen_task_succeeds(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    screen = _Screen()
    await _run(task, publisher, screen)
    assert task.status == "succeeded"
    assert screen.calls == ["demo output"]  # screened the deliverable text


@pytest.mark.asyncio
async def test_dlp_block_fails_task_without_leaking(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    screen = _Screen(raise_categories=["inn", "snils"])

    with pytest.raises(DlpViolation):
        await _run(task, publisher, screen)

    assert task.status == "failed"
    failed = next(ev for ev in publisher._drain.get(task.id, []) if ev.event_type == "task.failed")
    assert failed.payload["error_code"] == "security.dlp.blocked"
    assert failed.payload["retry_possible"] is False
    # category labels are present; no raw value can appear (screen never had one).
    assert "inn" in failed.payload["error_message"]
    _emit.emit_task_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_dlp_runs_before_memory_extraction(_emit: Any) -> None:
    task = _task(uuid4())
    publisher = InProcessSSEPublisher()
    screen = _Screen(raise_categories=["inn"])
    mem = _MemHook()

    with pytest.raises(DlpViolation):
        await _run(task, publisher, screen, mem)

    assert task.status == "failed"
    assert mem.calls == []  # blocked deliverable never reaches memory extraction
