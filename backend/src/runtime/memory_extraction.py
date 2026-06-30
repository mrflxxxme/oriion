"""Post-task memory auto-extraction — filter-agent + summarizer (Phase 01.4b).

Closes the automatic half of ADR-011 Wave-1 (AC-01.4.7 + the AC-01.4.6 summarizer
impl). The runtime drives the lite ``memory_curator`` agents and bills each LLM
call as a ``task_steps`` row (the step-sum cost authority), mirroring
``runtime.dispatch.MasterAgent`` + ``record_master_call_step``.

* ``MemoryExtractor`` — run the filter-agent on a *succeeded* task's final
  deliverable, map a positive verdict into ``memory.memory_entries``
  (``source='filter_agent'``), and bill the call as a step.
* ``build_memory_extraction_hook`` — assemble the orchestrator's post-success
  hook (``Callable[[deliverable, step_index], cost]``); the worker wires it.
* ``LLMConversationSummarizer`` — the ``ConversationSummarizer`` port impl used by
  ``ConversationHistoryService`` on overflow (the turn-capture PRODUCER is a later
  follow-up — grill Q3).

INVARIANT (billing): the extractor writes the memory entries FIRST and bills the
``task_steps`` row LAST, returning its cost only after the step exists. The
orchestrator folds that cost into ``ctx.accumulated_cost`` only on a successful
return and runs the hook best-effort (swallowing errors), so
``task.total_cost_credits == SUM(steps)`` holds whether or not extraction runs.

SECURITY: logs ids/counts/verdict only — never the deliverable, entry content, or
embeddings (mirrors the memory-service logging contract).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from decimal import Decimal
from time import perf_counter
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.memory_curator import (
    ROLE_KEY_MEMORY_FILTER,
    ROLE_KEY_MEMORY_SUMMARY,
    MemoryCallBilling,
    MemoryCuratorDeps,
    MemoryExtraction,
    build_conversation_summarizer_agent,
    build_memory_extraction_agent,
)
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel
from src.llm_gateway.services.router_service import LLMRouter
from src.memory.services.memory_service import CellMemoryService
from src.runtime.dispatch import _extract_usage, record_memory_call_step
from src.runtime.orchestrator import MemoryExtractionHook

logger = structlog.get_logger(__name__)

# Session-bound biller for one curator LLM call (defaults to the real-ledger
# ``record_memory_call_step``; unit tests inject a no-DB fake).
MemoryStepRecorder = Callable[[AsyncSession, MemoryCallBilling], Awaitable[Decimal]]


def _compose_extraction_prompt(user_prompt: str, deliverable: str) -> str:
    """Filter-agent input (grill Q7): the user's request + the final deliverable."""
    return f"## Запрос пользователя\n{user_prompt}\n\n## Итоговый результат команды\n{deliverable}"


class MemoryExtractor:
    """Runs the filter-agent over a deliverable + persists the verdict to cell
    memory, billing the LLM call as a ``task_steps`` row.

    Production builds the agent from ``llm_router``; unit tests inject a pre-built
    ``agent`` (FakeLLMGatewayModel-backed) + a fake ``recorder`` so no PG/provider
    is needed.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        cell_id: UUID,
        user_id: UUID,
        task_id: UUID,
        workspace_id: UUID,
        cell_memory: CellMemoryService,
        user_prompt: str,
        llm_router: LLMRouter | None = None,
        agent: Any = None,
        recorder: MemoryStepRecorder = record_memory_call_step,
    ) -> None:
        self._session = session
        self._cell_id = cell_id
        self._user_id = user_id
        self._task_id = task_id
        self._workspace_id = workspace_id
        self._cell_memory = cell_memory
        self._user_prompt = user_prompt
        self._llm_router = llm_router
        self._agent = agent
        self._recorder = recorder

    def _build_agent(self) -> tuple[Any, Any]:
        if self._agent is not None:
            return self._agent, getattr(self._agent, "model", None)
        if self._llm_router is None:
            raise ValueError("MemoryExtractor needs an llm_router or an injected agent.")
        model = LLMGatewayModel(
            role_key=ROLE_KEY_MEMORY_FILTER,
            llm_router=self._llm_router,
            workspace_id=self._workspace_id,
        )
        return build_memory_extraction_agent(model=model), model

    async def extract(self, deliverable: str, step_index: int) -> tuple[Decimal, int, int]:
        """Run the filter-agent, persist any entries, bill the call.

        Returns ``(cost, input_tokens, output_tokens)`` for the task rollup.

        Entries are written BEFORE the billing step so the orchestrator's
        best-effort swallow keeps ``task.total_cost == SUM(steps)``: the cost is
        returned (and folded) only after the step row exists.
        """
        agent, model = self._build_agent()
        prompt = _compose_extraction_prompt(self._user_prompt, deliverable)
        started = perf_counter()
        run = await agent.run(
            prompt, deps=MemoryCuratorDeps(cell_id=self._cell_id, task_id=self._task_id)
        )
        latency_ms = int((perf_counter() - started) * 1000)

        verdict = getattr(run, "output", None)
        if verdict is None:
            verdict = getattr(run, "data", None)
        if not isinstance(verdict, MemoryExtraction):
            raise TypeError(
                f"memory filter-agent did not return a MemoryExtraction "
                f"(got {type(verdict).__name__})."
            )

        if verdict.should_remember:
            for entry in verdict.entries:
                await self._cell_memory.add(
                    cell_id=self._cell_id,
                    workspace_id=self._workspace_id,
                    content=entry.content,
                    kind=entry.kind,
                    title=entry.title,
                    tags=list(entry.tags),
                    source="filter_agent",
                )

        input_tokens, output_tokens = _extract_usage(run)
        cost = await self._recorder(
            self._session,
            MemoryCallBilling(
                parent_task_id=self._task_id,
                cell_id=self._cell_id,
                user_id=self._user_id,
                phase="extraction",
                step_index=step_index,
                provider_slug=getattr(model, "_last_provider_slug", None) or "",
                model_name=getattr(model, "_last_model_name", None) or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            ),
        )
        logger.info(
            "memory.extraction.completed",
            cell_id=str(self._cell_id),
            task_id=str(self._task_id),
            should_remember=verdict.should_remember,
            entries=len(verdict.entries) if verdict.should_remember else 0,
        )
        return cost, input_tokens, output_tokens


def build_memory_extraction_hook(
    *,
    session: AsyncSession,
    llm_router: LLMRouter,
    cell_id: UUID,
    user_id: UUID,
    task_id: UUID,
    workspace_id: UUID,
    cell_memory: CellMemoryService,
    user_prompt: str,
) -> MemoryExtractionHook:
    """Build the orchestrator's post-success memory-extraction hook.

    Wired by the worker (``runtime.queue.actor``); the orchestrator default is
    ``None`` ⇒ no-op (unit tests), mirroring ``quota_admission``.
    """
    extractor = MemoryExtractor(
        session=session,
        cell_id=cell_id,
        user_id=user_id,
        task_id=task_id,
        workspace_id=workspace_id,
        cell_memory=cell_memory,
        user_prompt=user_prompt,
        llm_router=llm_router,
    )

    async def _hook(deliverable: str, step_index: int) -> tuple[Decimal, int, int]:
        return await extractor.extract(deliverable, step_index)

    return _hook


class LLMConversationSummarizer:
    """``ConversationSummarizer`` port impl — free-text digest via the lite agent.

    The conversation-history PRODUCER (capturing agent turns during a task) is a
    later follow-up (grill Q3, 2026-06-24); in 01.4b this adapter is wired +
    unit/integration-tested via direct ``ConversationHistoryService.append`` calls.
    Its own ``task_steps`` billing rides with that producer (``append()`` carries
    no task/step context), so this only produces the summary string.
    """

    def __init__(
        self,
        *,
        cell_id: UUID,
        llm_router: LLMRouter | None = None,
        workspace_id: UUID | None = None,
        agent: Any = None,
    ) -> None:
        self._cell_id = cell_id
        self._llm_router = llm_router
        self._workspace_id = workspace_id
        self._agent = agent

    def _build_agent(self) -> Any:
        if self._agent is not None:
            return self._agent
        if self._llm_router is None:
            raise ValueError("LLMConversationSummarizer needs an llm_router or an injected agent.")
        model = LLMGatewayModel(
            role_key=ROLE_KEY_MEMORY_SUMMARY,
            llm_router=self._llm_router,
            workspace_id=self._workspace_id,
        )
        return build_conversation_summarizer_agent(model=model)

    async def summarize(self, messages: list[str]) -> str:
        agent = self._build_agent()
        joined = "\n".join(f"- {m}" for m in messages)
        run = await agent.run(joined, deps=MemoryCuratorDeps(cell_id=self._cell_id))
        out = getattr(run, "output", None)
        if out is None:
            out = getattr(run, "data", None)
        return str(out) if out is not None else ""


__all__ = [
    "LLMConversationSummarizer",
    "MemoryExtractionHook",
    "MemoryExtractor",
    "MemoryStepRecorder",
    "build_memory_extraction_hook",
]
