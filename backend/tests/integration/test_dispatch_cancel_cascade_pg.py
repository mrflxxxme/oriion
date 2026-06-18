"""Integration (testcontainers-PG): real cancel-cascade + real-dispatch SSE order.

AC-W1-5 — replaces the in-memory-mock cancel-cascade unit test + the
route-registration-only SSE test with real-Postgres assertions:

* ``cancel_task`` flips the WHOLE descendant tree to 'cancelled' atomically and
  writes a task.cancelled row to the transactional outbox (AC-W1-4) in the same
  TX — verified by re-querying real rows.
* a real ``execute_agent_task`` dispatch streams its SSE ledger in the correct
  order (task.started → delegation pairs → task.completed) and persists the
  task as 'succeeded'.

Inserts run as the container superuser (``oriion``), which bypasses FORCE-RLS —
the same pattern as tests/multitenancy/test_rls_isolation.py. The ``db_session``
fixture rolls back wholesale at teardown.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
import src.agents.models
import src.multitenancy.models  # noqa: F401 — register multitenancy.* (Task.cell_id FK)
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.runtime.orchestrator import OrchestratorContext, execute_agent_task
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.services.task_service import TaskService

pytestmark = pytest.mark.integration


async def _insert_workspace_cell(session: AsyncSession, ws_id: UUID, cell_id: UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, 'WS')"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'Cell')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )


async def _insert_task(
    session: AsyncSession,
    task_id: UUID,
    cell_id: UUID,
    user_id: UUID,
    *,
    parent: UUID | None,
    status: str,
) -> None:
    await session.execute(
        text(
            "INSERT INTO tasks.tasks "
            "  (id, cell_id, initiated_by_user_id, title, status, parent_task_id) "
            "VALUES (:id, :cell, :user, :title, :status, :parent)"
        ),
        {
            "id": str(task_id),
            "cell": str(cell_id),
            "user": str(user_id),
            "title": f"task-{task_id}",
            "status": status,
            "parent": str(parent) if parent else None,
        },
    )


@pytest.mark.asyncio
async def test_cancel_cascade_flips_all_descendants_on_real_pg(db_session: AsyncSession) -> None:
    ws_id, cell_id, user_id = uuid4(), uuid4(), uuid4()
    await _insert_workspace_cell(db_session, ws_id, cell_id)

    root, a, b, c = uuid4(), uuid4(), uuid4(), uuid4()
    # Tree: root → {a, b}; a → c.
    await _insert_task(db_session, root, cell_id, user_id, parent=None, status="running")
    await _insert_task(db_session, a, cell_id, user_id, parent=root, status="running")
    await _insert_task(db_session, b, cell_id, user_id, parent=root, status="running")
    await _insert_task(db_session, c, cell_id, user_id, parent=a, status="running")

    descendants = await TaskService(db_session).cancel_task(root)

    assert set(descendants) == {a, b, c}

    # Every row in the cell flipped to 'cancelled' in real PG.
    rows = (
        await db_session.execute(
            text("SELECT status, completed_at FROM tasks.tasks WHERE cell_id = :c"),
            {"c": str(cell_id)},
        )
    ).all()
    assert len(rows) == 4
    assert all(r[0] == "cancelled" for r in rows)
    assert all(r[1] is not None for r in rows)

    # A task.cancelled event landed in the transactional outbox (same TX).
    outbox = (
        await db_session.execute(
            text(
                "SELECT data->>'task_id', published_at FROM tasks.outbox "
                "WHERE ce_type = 'oriion.tasks.cancelled.v1'"
            )
        )
    ).all()
    assert len(outbox) == 1
    assert outbox[0][0] == str(root)
    assert outbox[0][1] is None  # unpublished — the relay will pick it up


# ── real-dispatch SSE order ────────────────────────────────────────────────


class _CoordOutput(BaseModel):
    summary: str = "done"


class _CoordRunResult(BaseModel):
    output: _CoordOutput = _CoordOutput()


class _DelegatingCoordinator:
    """Stand-in Coordinator: delegates researcher→writer through deps.runner,
    exactly as the real plan-executor drives the leaf runner."""

    async def run(self, _prompt: str, *, deps: Any) -> _CoordRunResult:
        await deps.runner(DelegateInput(target_agent_slug="researcher", sub_prompt="r"), deps)
        await deps.runner(DelegateInput(target_agent_slug="writer", sub_prompt="w"), deps)
        return _CoordRunResult()


@pytest.mark.asyncio
async def test_dispatch_sse_order_on_real_pg(db_session: AsyncSession) -> None:
    ws_id, cell_id, user_id = uuid4(), uuid4(), uuid4()
    await _insert_workspace_cell(db_session, ws_id, cell_id)
    task_id = uuid4()
    await _insert_task(db_session, task_id, cell_id, user_id, parent=None, status="queued")

    publisher = InProcessSSEPublisher()
    leaf_calls: list[DelegateInput] = []

    async def _leaf_runner(inp: DelegateInput, _ctx: OrchestratorContext) -> DelegateResult:
        leaf_calls.append(inp)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="leaf done",
            cost_credits=Decimal("1"),
            tokens_used=10,
        )

    await execute_agent_task(
        task_id=task_id,
        cell_id=cell_id,
        user_id=user_id,
        coordinator_agent=_DelegatingCoordinator(),  # type: ignore[arg-type]
        user_prompt="market brief please",
        available_agent_slugs=["researcher", "writer"],
        leaf_runner=_leaf_runner,
        sse_publisher=publisher,
        session=db_session,
    )

    assert len(leaf_calls) == 2
    types = [ev.event_type for ev in publisher._drain.get(task_id, [])]
    assert types == [
        "task.started",
        "task.delegation_started",
        "task.delegation_completed",
        "task.delegation_started",
        "task.delegation_completed",
        "task.completed",
    ]

    # The orchestrator flips status on the ORM-loaded row but does not commit
    # (the Dramatiq actor owns the commit). Flush the pending UPDATE so the raw
    # SELECT sees it within this TX — proving the change reaches real PG.
    await db_session.flush()
    status = (
        await db_session.execute(
            text("SELECT status FROM tasks.tasks WHERE id = :id"), {"id": str(task_id)}
        )
    ).scalar_one()
    assert status == "succeeded"
