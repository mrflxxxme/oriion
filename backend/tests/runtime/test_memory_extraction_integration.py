"""Integration: memory auto-extraction on real Postgres (Phase 01.4b C6).

Real PG (testcontainers) under RLS as ``oriion_app`` for the memory writes, and
owner-role real-ledger billing for the invariant (mirrors
tests/tasks/test_task_steps_billing_integration.py):

* filter-extraction → ``memory.memory_entries`` rows with ``source='filter_agent'``
  + persisted 256-dim embeddings (fake LLM verdict + fake recorder, real repo/RLS);
* conversation overflow + real summarizer → ``memory_entries`` with
  ``kind='conversation_summary'`` + the FIFO window trims to size;
* BILLING INVARIANT — ``task.total_cost_credits == SUM(task_steps.cost_credits)``
  with the new memory-extraction step present exactly once (no double-count).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context
from src.agents.memory_curator import (
    MemoryCallBilling,
    MemoryExtraction,
    MemoryExtractionEntry,
)
from src.agents.seed_data.memory_curator_v1 import ensure_memory_curator_archetype
from src.memory.repositories.conversation_repository import ConversationRepository
from src.memory.repositories.memory_repository import CellMemoryRepository
from src.memory.services.conversation_service import ConversationHistoryService
from src.memory.services.memory_service import CellMemoryService
from src.runtime.dispatch import StepBilling, record_delegation_step, record_memory_call_step
from src.runtime.memory_extraction import LLMConversationSummarizer, MemoryExtractor

from tests.memory._fakes import DeterministicEmbedder

pytestmark = pytest.mark.integration


# ── fakes ──────────────────────────────────────────────────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeRun:
    output: Any
    _usage: _FakeUsage

    def usage(self) -> _FakeUsage:
        return self._usage


class _FakeModel:
    _last_provider_slug = "deepseek"
    _last_model_name = "deepseek-chat"


class _FakeAgent:
    def __init__(self, output: Any, *, in_tok: int = 70, out_tok: int = 30) -> None:
        self._output = output
        self._in = in_tok
        self._out = out_tok
        self.model = _FakeModel()

    async def run(self, _prompt: str, *, deps: Any) -> _FakeRun:
        return _FakeRun(self._output, _FakeUsage(self._in, self._out))


class _FakeRecorder:
    def __init__(self, cost: Decimal = Decimal("0.4")) -> None:
        self.billings: list[Any] = []
        self._cost = cost

    async def __call__(self, _session: Any, billing: Any) -> Decimal:
        self.billings.append(billing)
        return self._cost


# ── seed helpers (owner role bypasses RLS for setup) ───────────────────────


async def _make_ws_cell(session: AsyncSession) -> tuple[UUID, UUID]:
    ws_id, cell_id = uuid4(), uuid4()
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
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    return ws_id, cell_id


async def _make_agent(session: AsyncSession, cell_id: UUID) -> UUID:
    archetype_id, agent_id = uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO agents.agent_archetypes "
            "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
            " model_provider_slug, model_name) "
            "VALUES (:id, :slug, :vs, 'Test', 'researcher', 'v1', 'deepseek', 'deepseek-chat')"
        ),
        {"id": str(archetype_id), "slug": f"arch-{archetype_id}", "vs": f"vt-{archetype_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO agents.agent_instances (id, cell_id, agent_archetype_id) "
            "VALUES (:id, :cell, :arch)"
        ),
        {"id": str(agent_id), "cell": str(cell_id), "arch": str(archetype_id)},
    )
    return agent_id


# ── A. filter-extraction writes source='filter_agent' entries (real PG, RLS) ──


async def test_extraction_writes_filter_agent_entries(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_ws_cell(db_session)
    verdict = MemoryExtraction(
        should_remember=True,
        entries=[
            MemoryExtractionEntry(content="Клиент работает на рынке РФ.", kind="fact"),
            MemoryExtractionEntry(content="CTR — click-through rate.", kind="glossary"),
        ],
    )
    recorder = _FakeRecorder(Decimal("0.4"))

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        extractor = MemoryExtractor(
            session=db_session,
            cell_id=cell_id,
            user_id=uuid4(),
            task_id=uuid4(),
            workspace_id=ws_id,
            cell_memory=CellMemoryService(
                CellMemoryRepository(db_session), DeterministicEmbedder()
            ),
            user_prompt="Сделай анализ",
            agent=_FakeAgent(verdict),
            recorder=recorder,
        )
        cost, _in_tok, _out_tok = await extractor.extract("Итоговый отчёт.", step_index=7)
        rows = (
            await db_session.execute(
                text(
                    "SELECT content, kind, source, embedding IS NOT NULL "
                    "FROM memory.memory_entries ORDER BY content"
                )
            )
        ).all()

    assert cost == Decimal("0.4")
    assert len(rows) == 2
    assert all(r[2] == "filter_agent" for r in rows)  # tagged as the auto-filter
    assert {r[1] for r in rows} == {"fact", "glossary"}
    assert all(r[3] for r in rows)  # 256-dim embedding persisted for each entry
    assert len(recorder.billings) == 1  # the LLM call is billed exactly once


# ── B. conversation overflow → kind='conversation_summary' (real PG, RLS) ─────


async def test_conversation_overflow_writes_summary(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_ws_cell(db_session)
    agent_id = await _make_agent(db_session, cell_id)
    summarizer = LLMConversationSummarizer(
        cell_id=cell_id, agent=_FakeAgent("Резюме истории диалога.")
    )
    cell_memory = CellMemoryService(CellMemoryRepository(db_session), DeterministicEmbedder())
    convo = ConversationHistoryService(ConversationRepository(db_session), window=2)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        for i in range(4):
            await convo.append(
                cell_id=cell_id,
                workspace_id=ws_id,
                agent_id=agent_id,
                role="agent",
                content=f"сообщение {i}",
                summarizer=summarizer,
                cell_memory=cell_memory,
            )
        summary_rows = (
            await db_session.execute(
                text(
                    "SELECT content, kind, source FROM memory.memory_entries "
                    "WHERE kind = 'conversation_summary' ORDER BY created_at"
                )
            )
        ).all()
        remaining = (
            await db_session.execute(
                text(
                    "SELECT count(*) FROM memory.conversation_history "
                    "WHERE cell_id = :c AND agent_id = :a"
                ),
                {"c": str(cell_id), "a": str(agent_id)},
            )
        ).scalar_one()

    # window=2, 4 appends → 2 overflow summaries; the live window holds the last 2.
    assert len(summary_rows) == 2
    assert all(r[0] == "Резюме истории диалога." for r in summary_rows)
    assert all(r[1] == "conversation_summary" and r[2] == "summary" for r in summary_rows)
    assert remaining == 2


# ── C. billing invariant: total == SUM(steps) WITH the memory step ────────────


@pytest.mark.commit_required
async def test_billing_invariant_with_memory_step(db_session_committed: AsyncSession) -> None:
    session = db_session_committed
    ws_id, cell_id, user_id, parent_id = uuid4(), uuid4(), uuid4(), uuid4()
    await session.execute(
        text("INSERT INTO multitenancy.workspaces (id, slug, display_name) VALUES (:id, :s, 'WS')"),
        {"id": str(ws_id), "s": f"ws-{ws_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO multitenancy.cells (id, workspace_id, slug, display_name) "
            "VALUES (:id, :ws, 'default', 'C')"
        ),
        {"id": str(cell_id), "ws": str(ws_id)},
    )
    # A 'researcher' archetype for the delegation steps + the curator archetype
    # for the memory step (unique vertical_slug avoids the natural-key clash).
    await session.execute(
        text(
            "INSERT INTO agents.agent_archetypes "
            "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
            " model_provider_slug, model_name) "
            "VALUES (:id, 'researcher', :vs, 'R', 'researcher', 'v1', 'deepseek', 'deepseek-chat')"
        ),
        {"id": str(uuid4()), "vs": f"c6-{uuid4()}"},
    )
    await ensure_memory_curator_archetype(session)
    await session.execute(
        text(
            "INSERT INTO tasks.tasks (id, cell_id, initiated_by_user_id, title, description, status) "
            "VALUES (:id, :cell, :user, 'parent', '', 'running')"
        ),
        {"id": str(parent_id), "cell": str(cell_id), "user": str(user_id)},
    )
    for guc, val in (
        ("app.current_user_id", user_id),
        ("app.current_cell_id", cell_id),
        ("app.current_workspace_id", ws_id),
    ):
        await session.execute(text("SELECT set_config(:k, :v, true)"), {"k": guc, "v": str(val)})

    # 2 delegation steps (leaves) + 1 memory-extraction step — the orchestrator
    # accumulates each into ctx.accumulated_cost → task.total_cost_credits.
    accumulated = Decimal(0)
    for i in (1, 2):
        accumulated += await record_delegation_step(
            session,
            StepBilling(
                parent_task_id=parent_id,
                cell_id=cell_id,
                user_id=user_id,
                step_index=i,
                target_agent_slug="researcher",
                provider_slug="deepseek",
                model_name="deepseek-chat",
                input_tokens=1000,
                output_tokens=2000,
                latency_ms=10,
            ),
        )
    mem_cost = await record_memory_call_step(
        session,
        MemoryCallBilling(
            parent_task_id=parent_id,
            cell_id=cell_id,
            user_id=user_id,
            phase="extraction",
            step_index=3,
            provider_slug="deepseek",
            model_name="deepseek-chat",
            input_tokens=100,
            output_tokens=120,
            latency_ms=5,
        ),
    )
    accumulated += mem_cost
    await session.execute(
        text("UPDATE tasks.tasks SET total_cost_credits = :t WHERE id = :id"),
        {"t": str(accumulated), "id": str(parent_id)},
    )

    rows = (
        await session.execute(
            text(
                "SELECT step_index, step_type, cost_credits, input_jsonb "
                "FROM tasks.task_steps WHERE task_id = :t ORDER BY step_index"
            ),
            {"t": str(parent_id)},
        )
    ).all()
    steps_sum = (
        await session.execute(
            text("SELECT coalesce(sum(cost_credits), 0) FROM tasks.task_steps WHERE task_id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()
    persisted = (
        await session.execute(
            text("SELECT total_cost_credits FROM tasks.tasks WHERE id = :t"),
            {"t": str(parent_id)},
        )
    ).scalar_one()

    # INVARIANT: task.total == SUM(steps) == the orchestrator's accumulated cost.
    assert steps_sum == persisted == accumulated
    assert mem_cost > 0  # real-ledger cost, not zero
    # exactly 3 steps; the memory step appears once (no double-count of its cost).
    assert [r[0] for r in rows] == [1, 2, 3]
    mem_steps = [
        r for r in rows if isinstance(r[3], dict) and r[3].get("kind") == "memory_extraction"
    ]
    assert len(mem_steps) == 1
    assert mem_steps[0][1] == "llm_call"  # CHECK has no 'memory_extraction' value
