"""TaskService — CRUD + cancel cascade for tasks bounded context."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks import events as tasks_events
from src.tasks.exceptions import DelegationDepthExceeded, TaskNotFound
from src.tasks.models import Task

DEFAULT_MAX_DELEGATION_DEPTH = 5


class TaskService:
    """Wave 0 minimum task CRUD. Orchestration lives in
    src.runtime.orchestrator (Commit 6 sibling)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        """Create a task row + emit task.created event.

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
        self._session.add(task)
        await self._session.flush()  # materialize id
        await tasks_events.emit_task_created(
            task_id=task.id,
            cell_id=cell_id,
            initiated_by_user_id=user_id,
            parent_task_id=parent_task_id,
        )
        return task

    async def get_task(self, task_id: UUID) -> Task:
        task = await self._session.get(Task, task_id)
        if task is None:
            raise TaskNotFound(f"task {task_id} not found")
        return task

    async def cancel_task(self, task_id: UUID) -> list[UUID]:
        """Cancel task + cascade to children. Returns cascaded task_ids.

        AC12 anchor: parent.status='cancelled' + ALL descendant tasks
        flipped atomically in the same TX.
        """
        task = await self.get_task(task_id)

        descendants = await self._descendant_ids(task_id)
        all_ids = [task_id, *descendants]

        await self._session.execute(
            update(Task)
            .where(Task.id.in_(all_ids))
            .values(status="cancelled", completed_at=datetime.now(UTC))
        )
        await tasks_events.emit_task_cancelled(task_id=task.id, cascaded_to=descendants)
        return descendants

    async def _depth_from_root(self, task_id: UUID) -> int:
        """Walk parent_task chain — Wave 0 simple recursion (bounded by
        max_delegation_depth so worst case is O(depth) selects)."""
        depth = 1  # this task counts as 1 step up from itself
        current_id: UUID | None = task_id
        while current_id is not None:
            stmt = select(Task.parent_task_id).where(Task.id == current_id)
            row = (await self._session.execute(stmt)).scalar_one_or_none()
            if row is None:
                break
            current_id = row
            depth += 1
            if depth > DEFAULT_MAX_DELEGATION_DEPTH * 2:  # safety
                break
        return depth

    async def _descendant_ids(self, root_id: UUID) -> list[UUID]:
        """BFS over parent_task_id graph rooted at root_id."""
        result: list[UUID] = []
        frontier = [root_id]
        while frontier:
            stmt = select(Task.id).where(Task.parent_task_id.in_(frontier))
            children = [row[0] for row in (await self._session.execute(stmt)).all()]
            if not children:
                break
            result.extend(children)
            frontier = children
        return result
