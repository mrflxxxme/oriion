"""Unit: agency-marketing-ru seed (Master + horizontal reuse) — AC-W1-3, Commit 7.

Stubbed session (no PG). Covers both branches of ensure_agency_marketing_ru_seed
(insert + idempotent) and that provision_team routes the marketing preset
through the vertical seed.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from src.agents.models import AgentArchetype, AgentInstance, TeamPreset
from src.agents.seed_data.agency_marketing_ru_v1 import ensure_agency_marketing_ru_seed
from src.agents.services.team_provisioning_service import TeamProvisioningService

from tests.agents._session_stub import Result, StubSession


def _arc(slug: str, vertical: str = "horizontal") -> AgentArchetype:
    arc = AgentArchetype(
        slug=slug,
        vertical_slug=vertical,
        display_name=slug.title(),
        role_category="coordinator" if slug in ("coordinator", "master") else slug,
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=[],
    )
    arc.id = uuid4()
    return arc


@pytest.mark.asyncio
async def test_seed_fresh_inserts_master_and_reuses_horizontal() -> None:
    # 4 horizontal archetypes + horizontal preset + master + marketing preset → all miss.
    session = StubSession(results=[Result(scalar=None) for _ in range(7)])

    ids, preset_id = await ensure_agency_marketing_ru_seed(session)  # type: ignore[arg-type]

    masters = [o for o in session.added if isinstance(o, AgentArchetype) and o.slug == "master"]
    assert len(masters) == 1
    master = masters[0]
    assert master.vertical_slug == "agency_marketing_ru"
    assert master.role_category == "coordinator"  # CHECK has no 'master' — reuse
    assert master.status == "draft"  # AI baseline; founder evaluator run → 'reviewed'
    assert master.tools_allowed == []

    # Canonical order: master first, then the 4 reused horizontal archetypes.
    assert ids[0] == master.id
    assert len(ids) == 5

    presets = [
        o for o in session.added if isinstance(o, TeamPreset) and o.slug == "agency-marketing-ru"
    ]
    assert len(presets) == 1
    assert presets[0].archetype_ids == ids
    assert presets[0].vertical_slug == "agency_marketing_ru"
    assert preset_id == presets[0].id


@pytest.mark.asyncio
async def test_seed_idempotent_no_inserts() -> None:
    horizontal = [_arc(s) for s in ("coordinator", "researcher", "writer", "analyst")]
    horizontal_preset = TeamPreset(
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="x",
        archetype_ids=[a.id for a in horizontal],
    )
    horizontal_preset.id = uuid4()
    master = _arc("master", vertical="agency_marketing_ru")
    marketing_preset = TeamPreset(
        vertical_slug="agency_marketing_ru",
        slug="agency-marketing-ru",
        display_name="Маркетинговое агентство РФ",
        archetype_ids=[master.id, *[a.id for a in horizontal]],
    )
    marketing_preset.id = uuid4()
    session = StubSession(
        results=[
            *[Result(scalar=a) for a in horizontal],
            Result(scalar=horizontal_preset),
            Result(scalar=master),
            Result(scalar=marketing_preset),
        ]
    )

    ids, preset_id = await ensure_agency_marketing_ru_seed(session)  # type: ignore[arg-type]

    assert session.added == []  # idempotent
    assert ids[0] == master.id
    assert preset_id == marketing_preset.id


@pytest.mark.asyncio
async def test_provision_team_routes_marketing_preset_through_vertical_seed() -> None:
    """provision_team(agency-marketing-ru) seeds the Master + provisions 5 instances."""
    horizontal = [_arc(s) for s in ("coordinator", "researcher", "writer", "analyst")]
    horizontal_preset = TeamPreset(
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="x",
        archetype_ids=[a.id for a in horizontal],
    )
    horizontal_preset.id = uuid4()
    master = _arc("master", vertical="agency_marketing_ru")
    archetype_ids = [master.id, *[a.id for a in horizontal]]
    marketing_preset = TeamPreset(
        vertical_slug="agency_marketing_ru",
        slug="agency-marketing-ru",
        display_name="Маркетинговое агентство РФ",
        archetype_ids=archetype_ids,
    )
    marketing_preset.id = uuid4()
    existing_instances = [
        AgentInstance(cell_id=uuid4(), agent_archetype_id=aid) for aid in archetype_ids
    ]
    for inst in existing_instances:
        inst.id = uuid4()

    session = StubSession(
        results=[
            *[Result(scalar=a) for a in horizontal],
            Result(scalar=horizontal_preset),
            Result(scalar=master),
            Result(scalar=marketing_preset),  # seed: marketing preset found
            Result(scalar=marketing_preset),  # _load_preset
            Result(scalar_list=existing_instances),  # all archetypes already provisioned
        ]
    )
    service = TeamProvisioningService(session)  # type: ignore[arg-type]

    instances = await service.provision_team(
        preset_slug="agency-marketing-ru", cell_id=uuid4(), user_id=uuid4()
    )

    assert len(instances) == 5  # master + 4 horizontal
    assert session.added == []  # idempotent
