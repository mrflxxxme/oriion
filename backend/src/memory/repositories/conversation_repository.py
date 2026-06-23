"""Conversation history repository — memory.conversation_history (RLS).

Ordering is by the monotonic ``seq`` IDENTITY column, NOT ``created_at`` (which
ties for messages appended in one transaction). Cell-isolated via RLS.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.models import ConversationMessage


class ConversationRepository:
    """Append-only per agent-instance message log."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        agent_id: UUID,
        role: str,
        content: str,
        token_count: int | None = None,
    ) -> ConversationMessage:
        row = ConversationMessage(
            cell_id=cell_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def count(self, cell_id: UUID, agent_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ConversationMessage)
            .where(
                ConversationMessage.cell_id == cell_id,
                ConversationMessage.agent_id == agent_id,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def recent(
        self, cell_id: UUID, agent_id: UUID, *, limit: int
    ) -> list[ConversationMessage]:
        """The last ``limit`` messages in chronological (oldest→newest) order."""
        stmt = (
            select(ConversationMessage)
            .where(
                ConversationMessage.cell_id == cell_id,
                ConversationMessage.agent_id == agent_id,
            )
            .order_by(ConversationMessage.seq.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(reversed(rows))

    async def oldest(self, cell_id: UUID, agent_id: UUID, count: int) -> list[ConversationMessage]:
        """The ``count`` oldest messages (FIFO overflow candidates)."""
        stmt = (
            select(ConversationMessage)
            .where(
                ConversationMessage.cell_id == cell_id,
                ConversationMessage.agent_id == agent_id,
            )
            .order_by(ConversationMessage.seq.asc())
            .limit(count)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete_ids(self, ids: Sequence[UUID]) -> None:
        if not ids:
            return
        await self._session.execute(
            delete(ConversationMessage).where(ConversationMessage.id.in_(list(ids)))
        )
