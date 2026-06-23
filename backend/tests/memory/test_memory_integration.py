"""Integration: memory domain on real Postgres (pgvector) via testcontainers.

Exercises the migrations + repositories + services end-to-end under RLS as the
non-superuser ``oriion_app`` role:

* embedding round-trip — insert (256-dim fake vectors) → cosine ``<=>`` search →
  the exact-match entry ranks #1 with similarity ~1.0 (validates the pgvector
  column + HNSW + repo + service distance→similarity);
* RLS isolation — cell A cannot read cell B's memory_entries;
* role memory — agent-scoped recall + isolation between agents in one cell;
* conversation FIFO — the seq-ordered window trims the oldest on overflow.

Setup rows (workspaces / cells / agent_instances) are created as the superuser
test role BEFORE dropping to ``oriion_app`` so they bypass RLS; the assertions
run under tenant context + ``SET LOCAL ROLE oriion_app`` so RLS actually
evaluates (superusers bypass even FORCE RLS).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src._shared.db.rls import set_tenant_context
from src.memory.repositories.conversation_repository import ConversationRepository
from src.memory.repositories.memory_repository import CellMemoryRepository
from src.memory.repositories.role_memory_repository import RoleMemoryRepository
from src.memory.services.conversation_service import ConversationHistoryService
from src.memory.services.memory_service import CellMemoryService
from src.memory.services.role_memory_service import RoleMemoryService

from tests.memory._fakes import DeterministicEmbedder

pytestmark = pytest.mark.integration

_FIXED_VEC = [0.1] * 256


async def _make_workspace_cell(session: AsyncSession) -> tuple[UUID, UUID]:
    ws_id, cell_id = uuid4(), uuid4()
    await session.execute(
        text(
            "INSERT INTO multitenancy.workspaces (id, slug, display_name) "
            "VALUES (:id, :slug, :name)"
        ),
        {"id": str(ws_id), "slug": f"ws-{ws_id}", "name": "WS"},
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
    # The archetype catalog is not seeded by migrations alone — create a minimal
    # row (mirrors tests/tasks/test_task_steps_billing_integration.py).
    archetype_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO agents.agent_archetypes "
            "(id, slug, vertical_slug, display_name, role_category, prompt_version, "
            " model_provider_slug, model_name) "
            "VALUES (:id, :slug, 'memory-test', 'Test', 'researcher', 'v1', 'deepseek', "
            " 'deepseek-chat')"
        ),
        {"id": str(archetype_id), "slug": f"arch-{archetype_id}"},
    )
    agent_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO agents.agent_instances (id, cell_id, agent_archetype_id) "
            "VALUES (:id, :cell, :arch)"
        ),
        {"id": str(agent_id), "cell": str(cell_id), "arch": str(archetype_id)},
    )
    return agent_id


async def test_embedding_roundtrip_returns_exact_match_first(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    service = CellMemoryService(CellMemoryRepository(db_session), DeterministicEmbedder())

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        for content in ("apple pie recipe", "banana smoothie steps", "cherry cake notes"):
            await service.add(cell_id=cell_id, workspace_id=ws_id, content=content)
        hits = await service.search(cell_id=cell_id, query="banana smoothie steps", limit=3)

    assert hits[0][0].content == "banana smoothie steps"
    assert hits[0][1] == pytest.approx(1.0, abs=1e-6)  # exact-match cosine similarity
    assert len(hits) == 3


async def test_memory_entries_isolated_by_rls(db_session: AsyncSession) -> None:
    ws_a, cell_a = await _make_workspace_cell(db_session)
    ws_b, cell_b = await _make_workspace_cell(db_session)
    repo = CellMemoryRepository(db_session)

    # Inserted as the superuser test role → RLS bypassed for setup.
    await repo.insert(cell_id=cell_a, workspace_id=ws_a, content="A-secret", embedding=_FIXED_VEC)
    await repo.insert(cell_id=cell_b, workspace_id=ws_b, content="B-secret", embedding=_FIXED_VEC)

    async with set_tenant_context(db_session, workspace_id=ws_a, cell_id=cell_a, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        rows = (
            await db_session.execute(text("SELECT cell_id, content FROM memory.memory_entries"))
        ).all()

    cell_ids = {str(r[0]) for r in rows}
    contents = {r[1] for r in rows}
    assert str(cell_a) in cell_ids
    assert str(cell_b) not in cell_ids, "RLS leak: cell B memory visible to cell A"
    assert "B-secret" not in contents


async def test_role_memory_agent_scoped_and_isolated(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    agent_one = await _make_agent(db_session, cell_id)
    agent_two = await _make_agent(db_session, cell_id)
    service = RoleMemoryService(RoleMemoryRepository(db_session), DeterministicEmbedder())

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        await service.add(
            cell_id=cell_id,
            workspace_id=ws_id,
            agent_id=agent_one,
            content="agent one prefers brevity",
        )
        await service.add(
            cell_id=cell_id,
            workspace_id=ws_id,
            agent_id=agent_two,
            content="agent two prefers detail",
        )
        hits = await service.search(
            cell_id=cell_id, agent_id=agent_one, query="agent one prefers brevity", limit=5
        )
        recent_two = await service.list_recent(cell_id=cell_id, agent_id=agent_two)

    assert hits[0][0].content == "agent one prefers brevity"
    assert all(entry.agent_id == agent_one for entry, _ in hits)  # never agent_two's memory
    assert [m.content for m in recent_two] == ["agent two prefers detail"]


async def test_conversation_history_fifo_trims_oldest(db_session: AsyncSession) -> None:
    ws_id, cell_id = await _make_workspace_cell(db_session)
    agent_id = await _make_agent(db_session, cell_id)
    service = ConversationHistoryService(ConversationRepository(db_session), window=3)

    async with set_tenant_context(db_session, workspace_id=ws_id, cell_id=cell_id, user_id=uuid4()):
        await db_session.execute(text("SET LOCAL ROLE oriion_app"))
        for i in range(5):
            await service.append(
                cell_id=cell_id,
                workspace_id=ws_id,
                agent_id=agent_id,
                role="agent",
                content=f"m{i}",
            )
        recent = await service.recent(cell_id=cell_id, agent_id=agent_id)

    # window=3 → only the last three survive, in chronological (seq) order.
    assert [m.content for m in recent] == ["m2", "m3", "m4"]
