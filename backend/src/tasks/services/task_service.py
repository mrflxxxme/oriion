"""TaskService — CRUD + cancel cascade for tasks bounded context.

AC-W1-4: persistence goes through the ``TaskRepository`` port, and state-change
domain events are written to the transactional outbox in the SAME transaction as
the change (no dual-write). The relay (``runtime.queue.outbox_relay``)
republishes outbox rows at-least-once.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.events import TASKS_EVENT_SOURCE
from src.tasks.exceptions import DelegationDepthExceeded, TaskNotFound
from src.tasks.models import Task
from src.tasks.services.repository import SqlAlchemyTaskRepository, TaskRepository

DEFAULT_MAX_DELEGATION_DEPTH = 5


class TaskService:
    """Wave 0 minimum task CRUD. Orchestration lives in
    src.runtime.orchestrator (Commit 6 sibling)."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: TaskRepository | None = None,
    ) -> None:
        # Session retained so callers that share it (audit, provisioning) keep
        # the same outer TX; persistence is delegated to the repository port.
        self._session = session
        self._repo: TaskRepository = repository or SqlAlchemyTaskRepository(session)

    async def create_task(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        title: str,
        description: str,
        prompt: str,
        parent_task_id: UUID | None = None,
        max_delegation_depth: int = DEFAULT_MAX_DELEGATION_DEPTH,
    ) -> Task:
        """Create a task row + write a task.created outbox event (same TX).

        Enforces delegation depth invariant (AC12): walking the
        parent_task chain must stay ≤ max_delegation_depth.
        """
        if parent_task_id is not None:
            depth = await self._depth_from_root(parent_task_id)
            if depth >= max_delegation_depth:
                raise DelegationDepthExceeded(
                    f"parent chain depth {depth} >= max {max_delegation_depth}"
                )

        task = Task(
            cell_id=cell_id,
            initiated_by_user_id=user_id,
            parent_task_id=parent_task_id,
            title=title,
            description=description,
            input_jsonb={"prompt": prompt},
            status="queued",
        )
        await self._repo.add(task)
        await self._repo.add_outbox_event(
            ce_type="oriion.tasks.created.v1",
            ce_source=TASKS_EVENT_SOURCE,
            data={
                "task_id": str(task.id),
                "cell_id": str(cell_id),
                "initiated_by_user_id": str(user_id),
                "parent_task_id": str(parent_task_id) if parent_task_id else None,
            },
        )
        return task

    async def get_task(self, task_id: UUID) -> Task:
        task = await self._repo.get(task_id)
        if task is None:
            raise TaskNotFound(f"task {task_id} not found")
        return task

    async def cancel_task(self, task_id: UUID) -> list[UUID]:
        """Cancel task + cascade to children. Returns cascaded task_ids.

        AC12 anchor: parent.status='cancelled' + ALL descendant tasks
        flipped atomically in the same TX, and a task.cancelled event written
        to the outbox in that same TX (AC-W1-4).
        """
        task = await self.get_task(task_id)

        descendants = await self._repo.descendant_ids(task_id)
        all_ids = [task_id, *descendants]

        await self._repo.cancel_cascade(all_ids, at=datetime.now(UTC))
        await self._repo.add_outbox_event(
            ce_type="oriion.tasks.cancelled.v1",
            ce_source=TASKS_EVENT_SOURCE,
            data={
                "task_id": str(task.id),
                "cascaded_to_task_ids": [str(t) for t in descendants],
            },
        )
        return descendants

    async def _depth_from_root(self, task_id: UUID) -> int:
        """Walk parent_task chain — Wave 0 simple recursion (bounded by
        max_delegation_depth so worst case is O(depth) selects)."""
        depth = 1  # this task counts as 1 step up from itself
        current_id: UUID | None = task_id
        while current_id is not None:
            parent = await self._repo.parent_id(current_id)
            if parent is None:
                break
            current_id = parent
            depth += 1
            if depth > DEFAULT_MAX_DELEGATION_DEPTH * 2:  # safety
                break
        return depth
