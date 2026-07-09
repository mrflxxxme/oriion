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
        Result(scalar=None),  # seed memory_curator → insert
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
    # 4 archetypes + 1 preset + 1 memory_curator (seed) + 4 instances added.
    assert len(session.added) == 10


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
        Result(scalar=arcs[0]),  # seed memory_curator found (idempotent)
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


def _telegram_creator_preset(archetype_ids: list[UUID]) -> TeamPreset:
    preset = TeamPreset(
        vertical_slug="telegram_creator",
        slug="telegram-creator",
        display_name="Telegram-крейтор",
        archetype_ids=archetype_ids,
    )
    preset.id = uuid4()
    return preset


@pytest.mark.asyncio
async def test_provision_team_routes_telegram_creator_preset() -> None:
    """preset_slug='telegram-creator' must route to ensure_telegram_creator_seed
    (not silently fall through to the productivity-core-only branch) — 01.12
    closes the gap flagged in seed_data/telegram_creator_v1.py's module
    docstring ("product-UI provisioning path needs it before this preset is
    user-selectable end-to-end").
    """
    preset = _telegram_creator_preset([uuid4() for _ in range(6)])
    results = [
        # ensure_telegram_creator_seed -> ensure_productivity_core_seed:
        # 4 horizontal archetype lookups + 1 horizontal-preset lookup.
        Result(scalar=None),  # coordinator -> insert
        Result(scalar=None),  # researcher -> insert
        Result(scalar=None),  # writer -> insert
        Result(scalar=None),  # analyst -> insert
        Result(scalar=None),  # horizontal preset -> insert
        # ensure_telegram_creator_seed's own master + community-manager + preset.
        Result(scalar=None),  # master -> insert
        Result(scalar=None),  # community-manager -> insert
        Result(scalar=None),  # telegram-creator preset -> insert
        # ensure_memory_curator_archetype
        Result(scalar=None),  # memory_curator -> insert
        # provision_team's own lookups.
        Result(scalar=preset),  # _load_preset("telegram-creator")
        Result(scalar_list=[]),  # existing instances -> none
        Result(rows=[]),  # _archetype_slug_map -> all "unknown"
    ]
    session = StubSession(results=results)
    service = TeamProvisioningService(session)  # type: ignore[arg-type]

    instances = await service.provision_team(
        preset_slug="telegram-creator", cell_id=uuid4(), user_id=uuid4()
    )

    # 6 archetypes in the telegram-creator preset: master, community-manager,
    # coordinator, researcher, writer, analyst.
    assert len(instances) == 6
    # 4 horizontal archetypes + 1 horizontal preset + master + community-manager
    # + telegram preset + memory_curator (seed) + 6 instances added.
    assert len(session.added) == 15


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
        Result(scalar=arcs[0]),  # seed memory_curator found
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
