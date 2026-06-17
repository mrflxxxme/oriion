"""Unit: ArchetypeService — read-only catalog (stubbed session)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from src.agents.exceptions import AgentArchetypeNotFound
from src.agents.models import AgentArchetype
from src.agents.services.archetype_service import ArchetypeService

from tests.agents._session_stub import Result, StubSession


def _archetype(slug: str) -> AgentArchetype:
    arc = AgentArchetype(
        slug=slug,
        vertical_slug="horizontal",
        display_name=slug.title(),
        role_category=slug,
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=[],
    )
    arc.id = uuid4()
    return arc


@pytest.mark.asyncio
async def test_list_active_returns_rows() -> None:
    rows = [_archetype("researcher"), _archetype("writer")]
    session = StubSession(results=[Result(scalar_list=rows)])
    service = ArchetypeService(session)  # type: ignore[arg-type]

    out = await service.list_active()
    assert [a.slug for a in out] == ["researcher", "writer"]


@pytest.mark.asyncio
async def test_list_active_filtered_by_vertical() -> None:
    session = StubSession(results=[Result(scalar_list=[_archetype("researcher")])])
    service = ArchetypeService(session)  # type: ignore[arg-type]

    out = await service.list_active(vertical_slug="horizontal")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_get_by_id_found() -> None:
    arc = _archetype("analyst")
    session = StubSession(get_map={arc.id: arc})
    service = ArchetypeService(session)  # type: ignore[arg-type]

    assert await service.get_by_id(arc.id) is arc


@pytest.mark.asyncio
async def test_get_by_id_missing_raises() -> None:
    session = StubSession()
    service = ArchetypeService(session)  # type: ignore[arg-type]

    with pytest.raises(AgentArchetypeNotFound):
        await service.get_by_id(uuid4())
