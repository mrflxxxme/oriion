"""Unit: ensure_memory_curator_archetype (stubbed session) — Phase 01.4b."""

from __future__ import annotations

from uuid import uuid4

import pytest
from src.agents.models import AgentArchetype
from src.agents.seed_data.memory_curator_v1 import (
    ROLE_CATEGORY,
    SLUG,
    VERTICAL_SLUG,
    ensure_memory_curator_archetype,
)

from tests.agents._session_stub import Result, StubSession


@pytest.mark.asyncio
async def test_seed_inserts_when_missing() -> None:
    """No existing row → insert one archetype with the curator contract."""
    session = StubSession(results=[Result(scalar=None)])

    archetype_id = await ensure_memory_curator_archetype(session)  # type: ignore[arg-type]

    assert archetype_id is not None
    assert len(session.added) == 1
    arc = session.added[0]
    assert isinstance(arc, AgentArchetype)
    assert arc.slug == SLUG == "memory_curator"
    assert arc.vertical_slug == VERTICAL_SLUG == "horizontal"
    # grill Q1: reuse the 'analyzer' role_category — no CHECK migration.
    assert arc.role_category == ROLE_CATEGORY == "analyzer"
    assert arc.model_provider_slug == "deepseek"
    assert arc.model_name == "deepseek-chat"
    assert arc.is_active is True


@pytest.mark.asyncio
async def test_seed_idempotent_when_present() -> None:
    """Existing row → return its id, no insert (natural-key idempotency)."""
    existing = AgentArchetype(
        slug=SLUG,
        vertical_slug=VERTICAL_SLUG,
        display_name="x",
        role_category=ROLE_CATEGORY,
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=[],
    )
    existing.id = uuid4()
    session = StubSession(results=[Result(scalar=existing)])

    archetype_id = await ensure_memory_curator_archetype(session)  # type: ignore[arg-type]

    assert archetype_id == existing.id
    assert session.added == []
