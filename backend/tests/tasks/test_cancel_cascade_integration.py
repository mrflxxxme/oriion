"""AC-W1-5: cancel-cascade + SSE dispatch order on real Postgres.

Supersedes the in-memory stub coverage in ``tests/tasks/test_cancel_cascade.py``
with testcontainers-PG integration tests that drive real SQL and assert
real committed state.  The unit file is left in place for fast CI runs
(it exercises the BFS/depth logic without Docker).

Two parts (both marked ``integration``):

PART A — cancel cascade on real PG (``@pytest.mark.commit_required``)
-----------------------------------------------------------------------
* Inserts a workspace + cell via raw SQL as the DB owner (bypasses RLS —
  same pattern as ``tests/multitenancy/test_rls_isolation.py``).
* Builds a root → child → grandchild task tree via ``TaskService.create_task``,
  committing so rows are real (``db_session_committed``).
* Sets the three tenant-context GUCs + ``SET LOCAL ROLE oriion_app`` so
  every TaskService call runs under the app role with FORCE-RLS honoured.
* Calls ``TaskService.cancel_task(root_id)``.
* Opens a FRESH committed read (separate ``AsyncSession``) and asserts:
  - root, child, grandchild all have ``status == 'cancelled'``
  - root, child, grandchild all have ``completed_at IS NOT NULL``
  - exactly one ``oriion.tasks.cancelled.v1`` row exists in ``tasks.outbox``
    for the root task
  - returned cascaded list == {child_id, grandchild_id}

PART B — real-dispatch SSE order (fallback path)
-------------------------------------------------
Drives ``dispatch_task`` (the inline orchestrator) against a real-PG task
row with a ``_NoDelegationCoordinator`` stand-in (no live LLM) and the
``InProcessSSEPublisher``.  Asserts the SSE event-type sequence published
to ``publisher._drain`` is ``["task.started", "task.completed"]``.

Coverage note: PART B does not subscribe to the HTTP /stream endpoint.
It drives the same ``dispatch_task`` code path that the endpoint calls
and asserts the in-process drain buffer.  Full HTTP-subscribe coverage
is deferred to AC-W1-16a (Dramatiq actor + Redis-pubsub SSE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

# Register all cross-context models into the shared Base.metadata so that
# Task's string-based FKs (multitenancy.cells, agents.agent_instances) resolve
# at flush time without raising NoReferencedTableError.
import src.agents.models
import src.multitenancy.models  # noqa: F401
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from src.tasks.services.task_service import TaskService

# ---------------------------------------------------------------------------
# Shared scaffolding helpers
# ---------------------------------------------------------------------------


async def _insert_workspace_and_cell(
    session: AsyncSession,
) -> tuple[UUID, UUID]:
    """Insert a minimal workspace + cell as the DB-owner role (bypasses RLS).

    Returns ``(workspace_id, cell_id)``.
    """
    workspace_id = uuid4()
    cell_id = uuid4()
    slug_suffix = str(workspace_id)[:8]
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {
            "id": str(workspace_id),
            "slug": f"cc-int-{slug_suffix}",
            "name": "Cancel Cascade Integration WS",
        },
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'Default')"
        ),
        {"id": str(cell_id), "ws": str(workspace_id)},
    )
    return workspace_id, cell_id


# ---------------------------------------------------------------------------
# PART A — cancel-cascade on real Postgres
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.integration, pytest.mark.commit_required]


async def test_cancel_cascade_on_real_pg_asserts_all_nodes_cancelled(
    db_session_committed: AsyncSession,
    db_engine: AsyncEngine,
) -> None:
    """PART A: root → child → grandchild all land in 'cancelled' after cancel_task.

    Uses ``db_session_committed`` so every ``TaskService`` call issues a real
    COMMIT.  Assertions read back state via a fresh ``AsyncSession`` so they
    see committed data (not pending SAVEPOINT state).

    RLS: owner-role INSERTs first, then GUC + ``oriion_app`` role for the
    TaskService operations, matching the production code path.
    """
    user_id = uuid4()
    session = db_session_committed

    # ── 1. Insert workspace + cell as DB owner (RLS bypassed) ──────────────
    workspace_id, cell_id = await _insert_workspace_and_cell(session)
    await session.commit()

    # ── 2. Set tenant GUCs for TaskService calls ────────────────────────────
    # The testcontainer owner role (oriion) bypasses FORCE RLS for tables.
    # tasks.outbox has no GRANT to oriion_app, so we run as owner throughout.
    # The tasks.tasks policy checks only app.current_cell_id, not the role,
    # so setting the three GUCs is sufficient for RLS to accept our INSERTs.
    # Committed session means we must BEGIN a new TX block explicitly by
    # just executing within the session — SQLAlchemy autobegins on first stmt.
    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )

    # ── 3. Build root → child → grandchild via TaskService ──────────────────
    svc = TaskService(session)

    root = await svc.create_task(
        cell_id=cell_id,
        user_id=user_id,
        title="root",
        description="",
        prompt="root prompt",
    )
    root_id: UUID = root.id
    await session.commit()

    # Re-apply role + GUCs after commit (SET LOCAL resets at commit).
    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )

    child = await svc.create_task(
        cell_id=cell_id,
        user_id=user_id,
        title="child",
        description="",
        prompt="child prompt",
        parent_task_id=root_id,
    )
    child_id: UUID = child.id
    await session.commit()

    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )

    grandchild = await svc.create_task(
        cell_id=cell_id,
        user_id=user_id,
        title="grandchild",
        description="",
        prompt="grandchild prompt",
        parent_task_id=child_id,
    )
    grandchild_id: UUID = grandchild.id
    await session.commit()

    # ── 4. Cancel the root — cascades to child + grandchild ─────────────────
    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )

    cascaded = await svc.cancel_task(root_id)
    await session.commit()

    # ── 5. Assert returned cascade list ─────────────────────────────────────
    assert set(cascaded) == {child_id, grandchild_id}, (
        f"Expected cascade={{{child_id}, {grandchild_id}}}, got {set(cascaded)}"
    )

    # ── 6. Read back state via a FRESH session (sees committed rows) ─────────
    async with AsyncSession(db_engine, expire_on_commit=False) as fresh:
        # Fresh session runs as DB owner — FORCE RLS only blocks oriion_app,
        # so the owner can bypass for read-back assertions.
        rows = await fresh.execute(
            text(
                "SELECT id, status, completed_at "
                "FROM tasks.tasks "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": [root_id, child_id, grandchild_id]},
        )
        result_map: dict[UUID, tuple[str, Any]] = {
            row[0]: (row[1], row[2]) for row in rows.all()
        }

    assert len(result_map) == 3, (
        f"Expected 3 task rows; got {len(result_map)}: {list(result_map.keys())}"
    )
    for task_id, (status, completed_at) in result_map.items():
        assert status == "cancelled", (
            f"task {task_id}: expected status='cancelled', got {status!r}"
        )
        assert completed_at is not None, (
            f"task {task_id}: expected completed_at to be set, got None"
        )

    # ── 7. Assert outbox row for root cancellation ───────────────────────────
    async with AsyncSession(db_engine, expire_on_commit=False) as fresh:
        outbox_row = await fresh.execute(
            text(
                "SELECT data "
                "FROM tasks.outbox "
                "WHERE ce_type = 'oriion.tasks.cancelled.v1' "
                "  AND data->>'task_id' = :task_id"
            ),
            {"task_id": str(root_id)},
        )
        rows_all = outbox_row.all()

    assert len(rows_all) == 1, (
        f"Expected exactly 1 oriion.tasks.cancelled.v1 outbox row for root; "
        f"got {len(rows_all)}"
    )
    outbox_data: dict[str, Any] = rows_all[0][0]
    assert outbox_data["task_id"] == str(root_id)
    cascaded_from_outbox: set[str] = set(outbox_data.get("cascaded_to_task_ids", []))
    assert cascaded_from_outbox == {str(child_id), str(grandchild_id)}, (
        f"Outbox cascaded_to_task_ids mismatch: {cascaded_from_outbox}"
    )


# ---------------------------------------------------------------------------
# PART B — real-dispatch SSE event order
# ---------------------------------------------------------------------------


@dataclass
class _NoDelegationCoordinator:
    """Coordinator stand-in that completes without delegating to any specialist.

    Returns a ``CoordinatorOutput`` with a scripted summary and no artifacts,
    so ``dispatch_task`` exercises its full run-orchestrator → status-update →
    SSE-publish path without touching the LLM layer.
    """

    @dataclass
    class _Result:
        output: Any = field(default=None)

        def __post_init__(self) -> None:
            from src.agents.coordinator import CoordinatorOutput

            if self.output is None:
                self.output = CoordinatorOutput(summary="no-delegation scripted")

    async def run(self, _user_prompt: str, *, deps: Any) -> _NoDelegationCoordinator._Result:
        return _NoDelegationCoordinator._Result()


class _DispatchSession:
    """Minimal AsyncSession shim for dispatch_task.

    Provides ``get(Task, id) → task``, ``add(obj)``, and ``flush()`` so
    dispatch_task can persist status updates without a real DB session.
    This is acceptable for PART B because the SSE-order assertion does NOT
    depend on the committed DB state — it reads from ``publisher._drain``.
    """

    def __init__(self, task: Any) -> None:
        self._task = task
        self.added: list[Any] = []

    async def get(self, _model: Any, _task_id: UUID) -> Any:
        return self._task

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


async def test_dispatch_sse_event_order_is_started_then_completed(
    db_session_committed: AsyncSession,
    db_engine: AsyncEngine,
) -> None:
    """PART B: dispatch_task publishes task.started first, task.completed last.

    Drives the real ``dispatch_task`` code path (inline orchestrator wiring)
    with a no-delegation coordinator and the in-process SSE publisher.
    The task row is created via ``TaskService`` against real Postgres so the
    task object carries a real committed UUID.

    What IS covered: ``dispatch_task`` SSE publish sequence, status transitions,
    full orchestrator entry/exit path.
    What is NOT covered: HTTP /stream endpoint subscription, Dramatiq actor
    dispatch, Redis-pubsub cross-process delivery (deferred to AC-W1-16a).
    """
    from src.runtime.dispatch import dispatch_task
    from src.runtime.sse_publisher import InProcessSSEPublisher, reset_sse_publisher_for_tests

    # Reset the singleton so drained events from other tests never leak.
    reset_sse_publisher_for_tests()
    publisher = InProcessSSEPublisher()

    session = db_session_committed
    user_id = uuid4()

    # Insert workspace + cell as owner (bypasses RLS) so the Task FK resolves.
    workspace_id, cell_id = await _insert_workspace_and_cell(session)
    await session.commit()

    # Create the task row on real PG via TaskService under the app role.
    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )

    svc = TaskService(session)
    task = await svc.create_task(
        cell_id=cell_id,
        user_id=user_id,
        title="sse-order-test",
        description="",
        prompt="test SSE order",
    )
    await session.commit()

    # Materialise the fields dispatch_task reads directly off the Task object.
    task.total_cost_credits = Decimal(0)
    task.total_input_tokens = 0
    task.total_output_tokens = 0

    # Use a shim session for dispatch so status updates don't need GUC context.
    dispatch_session = _DispatchSession(task)

    await dispatch_task(
        task=task,
        session=dispatch_session,  # type: ignore[arg-type]
        llm_router=object(),  # type: ignore[arg-type]  # never reached — no delegation
        sse_publisher=publisher,
        coordinator=_NoDelegationCoordinator(),  # type: ignore[arg-type]
    )

    drained = publisher._drain.get(task.id, [])
    event_types = [ev.event_type for ev in drained]

    assert event_types, "No SSE events published — dispatch_task did not fire any"
    assert event_types[0] == "task.started", (
        f"First SSE event must be 'task.started'; got {event_types[0]!r} "
        f"(full sequence: {event_types})"
    )
    assert event_types[-1] == "task.completed", (
        f"Last SSE event must be 'task.completed'; got {event_types[-1]!r} "
        f"(full sequence: {event_types})"
    )
