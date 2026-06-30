"""Memory-curator agents — auto-extraction filter + conversation summarizer.

Phase 01.4b (ADR-011 Wave-1) closes the **automatic** half of the memory path
that Phase 01.4 shipped as a seam (AC-01.4.7 + AC-01.4.6 summarizer impl):

* the **filter-agent** runs after a *succeeded* task, judges whether the
  deliverable holds durable, reusable cell knowledge, and emits a structured
  ``MemoryExtraction`` (``should_remember`` + ``entries``) that the runtime maps
  into ``memory.memory_entries`` rows (``source='filter_agent'``);
* the **summarizer** condenses an overflowing conversation window into a short
  free-text digest — the ``ConversationSummarizer`` port that
  ``ConversationHistoryService.append`` already accepts.

This is the **agents-layer** half: pure Pydantic-AI schemas + factories with no
``runtime``/``dispatch`` import (so ``runtime`` may import it without a cycle),
mirroring ``agents/master.py``. The orchestration object (``MemoryExtractor``),
the billing recorder, and the summarizer adapter live in ``runtime.dispatch``.

Model split mirrors the Master (grill 2026-06-24): the **extraction** call needs
structured JSON (``MemoryExtraction``) so it runs on ``deepseek-chat``
(``role_key='memory_filter'``) via ``PromptedOutput`` — ``deepseek-reasoner``/R1
emits reasoning prose that breaks fenced-JSON. The **summary** is free text and
also runs on the lite ``deepseek-chat`` (``role_key='memory_summary'``). Both are
the cheap chat tier (grill Q2).

SECURITY: the agents carry no tools and never echo their input; the runtime that
drives them logs ids/counts only (never content or embeddings).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput

from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

# Router role-keys (mapped in llm_gateway.services.router_service.ROLE_TO_MODEL).
ROLE_KEY_MEMORY_FILTER = "memory_filter"
ROLE_KEY_MEMORY_SUMMARY = "memory_summary"

# Cell-memory kinds the filter-agent may assign. Mirrors the CHECK on
# ``memory.memory_entries.kind`` MINUS ``conversation_summary`` (summarizer-only),
# so the filter is constrained to durable knowledge kinds. A value off this list
# would trip the DB CHECK on insert; PromptedOutput validates it up-front.
MemoryKind = Literal["fact", "note", "glossary"]


# ── structured output of the filter-agent ─────────────────────────────────


class MemoryExtractionEntry(BaseModel):
    """One memory-worthy item the filter distilled from a deliverable."""

    content: str = Field(..., min_length=1)
    kind: MemoryKind = "fact"
    title: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryExtraction(BaseModel):
    """Structured verdict of the post-task filter-agent (ADR-011 Wave-1).

    ``should_remember`` is the gate: when ``False`` the runtime writes nothing
    (the common case — most tasks add no durable cell knowledge). When ``True``,
    each ``entries`` item becomes a ``memory.memory_entries`` row
    (``source='filter_agent'``).
    """

    should_remember: bool = False
    entries: list[MemoryExtractionEntry] = Field(default_factory=list)


# ── per-run deps for the curator's own Pydantic-AI agents ─────────────────


@dataclass
class MemoryCuratorDeps:
    """Minimal deps for the curator agents (no tools, identity context only).

    ``task_id`` is optional because the summarizer may run outside a task path
    (the conversation-history producer is a later follow-up); the extraction
    path always supplies it.
    """

    cell_id: UUID
    task_id: UUID | None = None


# ── billing payload + recorder port for the curator's own LLM calls ───────


@dataclass(frozen=True)
class MemoryCallBilling:
    """Everything the recorder needs to bill + persist one curator LLM call.

    Persisted as a ``task_steps`` row (``step_type='llm_call'`` — the step CHECK
    has no 'memory_extraction' value, so the phase lives in ``input_jsonb``) on the
    task under the seeded ``memory_curator`` archetype FK, so the per-task
    step-sum (the cost authority) includes the auto-extraction overhead —
    parallels ``MasterCallBilling`` for the Master's own plan/synthesis calls.
    """

    parent_task_id: UUID
    cell_id: UUID
    user_id: UUID
    phase: str  # 'extraction' | 'summary'
    step_index: int
    provider_slug: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


# A recorder bills one curator LLM call + returns its cost in credits. The
# orchestrator wraps the session-bound biller into this ctx-aware port (fold into
# accumulated_cost + SSE), symmetric to the Master's ``MasterCallRecorder``.
MemoryCallRecorder = Callable[[MemoryCallBilling], Awaitable[Decimal]]


# ── system prompts (inlined — internal utility agents, NOT 9-section personas) ─
# The filter/summarizer are infrastructure agents, not user-facing vertical
# personas, so they are not authored as ``contracts/role-prompts/*.md`` (which
# enforce a frontmatter + 9-section contract). Keeping the prompts here avoids
# coupling internal agents to that persona pipeline + its container path var.

_FILTER_SYSTEM_PROMPT = """\
Ты — фильтр долговременной памяти команды ИИ-агентов внутри рабочей ячейки (cell).
После успешно выполненной задачи ты получаешь запрос пользователя и финальный результат
работы команды. Реши, содержит ли результат знания, которые стоит запомнить НАДОЛГО и
переиспользовать в будущих задачах этой ячейки.

Запоминай ТОЛЬКО устойчивые, переиспользуемые сведения: факты о клиенте, компании, продукте;
согласованные договорённости и предпочтения; терминологию; способы и процессы работы.
НЕ запоминай:
— одноразовые детали конкретной задачи, которые не пригодятся снова;
— общеизвестные факты;
— секреты, пароли, токены, платёжные данные;
— персональные данные, если они не критичны для дальнейшей работы.

Если запоминать нечего — верни should_remember=false и пустой список entries (это нормально
и частый случай). Если есть — верни should_remember=true и от 1 до 5 коротких атомарных записей.
Каждая запись самодостаточна (понятна без контекста задачи), сформулирована по-русски, с kind:
— "fact" — факт о клиенте/компании/продукте/договорённости;
— "glossary" — определение термина или аббревиатуры;
— "note" — заметка о процессе/предпочтении/способе работы.
Не дублируй одну и ту же мысль в нескольких записях."""

_SUMMARY_SYSTEM_PROMPT = """\
Ты — суммаризатор истории диалога команды ИИ-агентов. Ты получаешь самые старые сообщения,
которые выходят за пределы активного окна и будут удалены. Сохрани их суть в одном компактном
резюме (не больше ~500 токенов), чтобы команда не потеряла контекст.

Сохрани: принятые решения; согласованные факты и цифры; открытые вопросы и договорённости;
важные предпочтения пользователя. Опусти: приветствия, служебные реплики, повторы.
Пиши по-русски, сжато, короткими пунктами или абзацами. Верни ТОЛЬКО текст резюме,
без преамбулы и пояснений."""


# ── agent factories ───────────────────────────────────────────────────────


def build_memory_extraction_agent(
    *,
    model: LLMGatewayModel,
) -> Agent[MemoryCuratorDeps, MemoryExtraction]:
    """Filter-agent: structured ``MemoryExtraction`` via ``PromptedOutput``.

    Runs on ``deepseek-chat`` (``role_key='memory_filter'``) so the should-remember
    verdict + entries parse reliably from a fenced-JSON completion.
    """
    return Agent(
        model=model,
        deps_type=MemoryCuratorDeps,
        output_type=PromptedOutput(MemoryExtraction),
        system_prompt=_FILTER_SYSTEM_PROMPT,
        tools=[],
    )


def build_conversation_summarizer_agent(
    *,
    model: LLMGatewayModel,
) -> Agent[MemoryCuratorDeps, str]:
    """Summarizer: free-text ~500-token digest (``role_key='memory_summary'``)."""
    return Agent(
        model=model,
        deps_type=MemoryCuratorDeps,
        output_type=str,
        system_prompt=_SUMMARY_SYSTEM_PROMPT,
        tools=[],
    )


__all__ = [
    "ROLE_KEY_MEMORY_FILTER",
    "ROLE_KEY_MEMORY_SUMMARY",
    "MemoryCallBilling",
    "MemoryCallRecorder",
    "MemoryCuratorDeps",
    "MemoryExtraction",
    "MemoryExtractionEntry",
    "MemoryKind",
    "build_conversation_summarizer_agent",
    "build_memory_extraction_agent",
]
