"""Conversation history service — append + FIFO window + summarize-on-overflow.

ADR-011 Wave-1 (grill Q2). Keeps the last ``window`` (=50) messages per
(cell, agent). On overflow, when a summarizer + cell-memory sink are wired, the
overflow is distilled into a ``memory.memory_entries`` row tagged
``kind='conversation_summary'`` before being trimmed; otherwise it is a plain
FIFO delete. The summarizer (a lite-LLM agent that records its own cost via
``record_llm_cost``) is injected by the worker — keeping this service free of
billing/LLM coupling so it is unit-testable without a model.

SECURITY: logs cell/agent ids + counts only, never message content.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import structlog

from src.memory.models import ConversationMessage
from src.memory.repositories.conversation_repository import ConversationRepository
from src.memory.services.memory_service import CellMemoryService

logger = structlog.get_logger(__name__)

# ADR-011: keep the last N=50 messages per agent as the live FIFO window.
DEFAULT_HISTORY_WINDOW = 50


class ConversationSummarizer(Protocol):
    """Lite-LLM seam: condense overflow messages into a short summary string."""

    async def summarize(self, messages: list[str]) -> str:
        """Return a compact (~500-token) summary of ``messages`` (oldest→newest)."""
        ...


class ConversationHistoryService:
    """Per agent-instance conversation log with a FIFO window + summary spill."""

    def __init__(
        self, repo: ConversationRepository, *, window: int = DEFAULT_HISTORY_WINDOW
    ) -> None:
        self._repo = repo
        self._window = window

    async def append(
        self,
        *,
        cell_id: UUID,
        workspace_id: UUID,
        agent_id: UUID,
        role: str,
        content: str,
        token_count: int | None = None,
        summarizer: ConversationSummarizer | None = None,
        cell_memory: CellMemoryService | None = None,
    ) -> ConversationMessage:
        """Append a message; if the window overflows, summarize+trim or FIFO-trim."""
        message = await self._repo.append(
            cell_id=cell_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        count = await self._repo.count(cell_id, agent_id)
        if count > self._window:
            overflow = await self._repo.oldest(cell_id, agent_id, count - self._window)
            if overflow:
                if summarizer is not None and cell_memory is not None:
                    summary = await summarizer.summarize([m.content for m in overflow])
                    await cell_memory.add(
                        cell_id=cell_id,
                        workspace_id=workspace_id,
                        content=summary,
                        kind="conversation_summary",
                        source="summary",
                    )
                    logger.info(
                        "memory.conversation.summarized",
                        cell_id=str(cell_id),
                        agent_id=str(agent_id),
                        summarized=len(overflow),
                    )
                await self._repo.delete_ids([m.id for m in overflow])
        return message

    async def recent(
        self, *, cell_id: UUID, agent_id: UUID, limit: int | None = None
    ) -> list[ConversationMessage]:
        """The current FIFO window (oldest→newest), default ``window`` size."""
        return await self._repo.recent(cell_id, agent_id, limit=limit or self._window)
