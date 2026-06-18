"""TaskRepository port + SQLAlchemy adapter (AC-W1-4).

Introduces a persistence port so ``TaskService`` depends on the *capability*
(create / load / cancel-cascade / write-outbox) rather than a raw
``AsyncSession``. The SQLAlchemy adapter keeps the Wave-0 SQL (BFS cascade,
parent-chain walk) but adds the transactional-outbox write — a domain
CloudEvent INSERTed in the SAME session/TX as the state change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.models import OutboxEvent, Task


class TaskRepository(Protocol):
    """Persistence port for the tasks bounded context."""

    async def add(self, task: Task) -> Task: ...

    async def get(self, task_id: UUID) -> Task | None: ...

    async def parent_id(self, task_id: UUID) -> UUID | None: ...

    async def descendant_ids(self, root_id: UUID) -> list[UUID]: ...

    async def cancel_cascade(self, task_ids: list[UUID], *, at: datetime) -> None: ...

    async def add_outbox_event(
        self,
        *,
        ce_type: str,
        ce_source: str,
        data: dict[str, Any],
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> OutboxEvent: ...


class SqlAlchemyTaskRepository:
    """``TaskRepository`` over an ``AsyncSession``. Writes participate in the
    caller's outer transaction (commit is the caller's responsibility)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: Task) -> Task:
        self._session.add(task)
        await self._session.flush()  # materialize id
        return task

    async def get(self, task_id: UUID) -> Task | None:
        return await self._session.get(Task, task_id)

    async def parent_id(self, task_id: UUID) -> UUID | None:
        stmt = select(Task.parent_task_id).where(Task.id == task_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def descendant_ids(self, root_id: UUID) -> list[UUID]:
        """BFS over the parent_task_id graph rooted at ``root_id``."""
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

    async def cancel_cascade(self, task_ids: list[UUID], *, at: datetime) -> None:
        await self._session.execute(
            update(Task).where(Task.id.in_(task_ids)).values(status="cancelled", completed_at=at)
        )

    async def add_outbox_event(
        self,
        *,
        ce_type: str,
        ce_source: str,
        data: dict[str, Any],
        subject: str | None = None,
        correlation_id: str | None = None,
    ) -> OutboxEvent:
        event = OutboxEvent(
            ce_type=ce_type,
            ce_source=ce_source,
            ce_subject=subject,
            correlation_id=correlation_id,
            data=data,
        )
        self._session.add(event)
        await self._session.flush()  # materialize id + ce_id
        return event
