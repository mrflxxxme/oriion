"""Unit: TeamProvisioningService + productivity-core seed (stubbed session).

Exercises both branches of ensure_productivity_core_seed (insert + idempotent),
provision_team (create + reuse), the preset-not-found error, and the
NullTeamProvisioningService no-op default (AC-W1-7).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from src.agents.exceptions import TeamPresetNotFound
from src.agents.models import AgentArchetype, AgentInstance, TeamPreset
from src.agents.services.team_provisioning_service import (
    NULL_TEAM_PROVISIONING,
    NullTeamProvisioningService,
    TeamProvisioningService,
)

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


def _preset(archetype_ids: list[UUID]) -> TeamPreset:
    preset = TeamPreset(
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="Твои личные ассистенты",
        archetype_ids=archetype_ids,
    )
    preset.id = uuid4()
    return preset


def _instance(archetype_id: UUID) -> AgentInstance:
    inst = AgentInstance(cell_id=uuid4(), agent_archetype_id=archetype_id)
    inst.id = uuid4()
    return inst


@pytest.mark.asyncio
async def test_provision_team_fresh_inserts_and_emits() -> None:
    """All lookups miss → seed inserts 4 archetypes + preset, then 4 instances."""
    preset = _preset([uuid4() for _ in range(4)])
    results = [
        Result(scalar=None),  # seed archetype: coordinator → insert
        Result(scalar=None),  # researcher → insert
        Result(scalar=None),  # writer → insert
        Result(scalar=None),  # analyst → insert
        Result(scalar=None),  # seed preset → insert
        Result(scalar=preset),  # _load_preset
        Result(scalar_list=[]),  # existing instances → none
        Result(rows=[]),  # _archetype_slug_map → all "unknown"
    ]
    session = StubSession(results=results)
    service = TeamProvisioningService(session)  # type: ignore[arg-type]

    instances = await service.provision_team(
        preset_slug="productivity-core", cell_id=uuid4(), user_id=uuid4()
    )

    assert len(instances) == 4
    # 4 archetypes + 1 preset (seed) + 4 instances added.
    assert len(session.added) == 9


@pytest.mark.asyncio
async def test_provision_team_idempotent_reuses_existing() -> None:
    """Everything already exists → no inserts, no event emission."""
    arcs = [_archetype(s) for s in ("coordinator", "researcher", "writer", "analyst")]
    preset = _preset([a.id for a in arcs])
    instances = [_instance(a.id) for a in arcs]
    results = [
        Result(scalar=arcs[0]),
        Result(scalar=arcs[1]),
        Result(scalar=arcs[2]),
        Result(scalar=arcs[3]),
        Result(scalar=preset),  # seed preset found
        Result(scalar=preset),  # _load_preset found
        Result(scalar_list=instances),  # existing instances cover every archetype
    ]
    session = StubSession(results=results)
    service = TeamProvisioningService(session)  # type: ignore[arg-type]

    out = await service.provision_team(
        preset_slug="productivity-core", cell_id=uuid4(), user_id=uuid4()
    )

    assert len(out) == 4
    assert session.added == []  # idempotent — nothing inserted


@pytest.mark.asyncio
async def test_provision_team_unknown_preset_raises() -> None:
    arcs = [_archetype(s) for s in ("coordinator", "researcher", "writer", "analyst")]
    preset = _preset([a.id for a in arcs])
    results = [
        Result(scalar=arcs[0]),
        Result(scalar=arcs[1]),
        Result(scalar=arcs[2]),
        Result(scalar=arcs[3]),
        Result(scalar=preset),  # seed preset found
        Result(scalar=None),  # _load_preset("ghost") → missing
    ]
    session = StubSession(results=results)
    service = TeamProvisioningService(session)  # type: ignore[arg-type]

    with pytest.raises(TeamPresetNotFound):
        await service.provision_team(preset_slug="ghost", cell_id=uuid4(), user_id=uuid4())


@pytest.mark.asyncio
async def test_null_provisioning_service_is_noop() -> None:
    out = await NullTeamProvisioningService().provision_team(
        preset_slug="productivity-core", cell_id=uuid4(), user_id=uuid4()
    )
    assert out == []
    # the module-level default singleton is a NullTeamProvisioningService
    assert isinstance(NULL_TEAM_PROVISIONING, NullTeamProvisioningService)
