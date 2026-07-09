"""Unit: telegram-creator seed (Master + community-manager + horizontal reuse).

Second Wave-1 vertical (Phase 01.10), mirrors ``test_seed_agency_marketing.py``
exactly. Stubbed session (no PG). Covers both branches of
``ensure_telegram_creator_seed`` (insert + idempotent).

No provision-team-routing test here (unlike agency-marketing-ru): as of this
phase ``TeamProvisioningService.provision_team`` only special-cases
``AGENCY_MARKETING_PRESET_SLUG`` and falls through to the horizontal-only seed
for every other ``preset_slug`` — wiring ``telegram-creator`` through that
routing is an explicit known follow-up (see ``telegram_creator_v1`` module
docstring + ``.planning/verticals/telegram-creator/changelog.md``), not needed
for the evaluator run (which calls the Master agent factories directly).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from src.agents.models import AgentArchetype, TeamPreset
from src.agents.seed_data.telegram_creator_v1 import (
    COMMUNITY_MANAGER_SLUG,
    MASTER_SLUG,
    PRESET_SLUG,
    VERTICAL_SLUG,
    ensure_telegram_creator_seed,
)

from tests.agents._session_stub import Result, StubSession


def _arc(slug: str, vertical: str = "horizontal") -> AgentArchetype:
    arc = AgentArchetype(
        slug=slug,
        vertical_slug=vertical,
        display_name=slug.title(),
        role_category="master" if slug == MASTER_SLUG else slug,
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=[],
    )
    arc.id = uuid4()
    return arc


@pytest.mark.asyncio
async def test_seed_fresh_inserts_master_and_community_manager_and_reuses_horizontal() -> None:
    # 4 horizontal archetypes + horizontal preset + master + community-manager
    # + telegram-creator preset → all miss.
    session = StubSession(results=[Result(scalar=None) for _ in range(8)])

    ids, preset_id = await ensure_telegram_creator_seed(session)  # type: ignore[arg-type]

    masters = [o for o in session.added if isinstance(o, AgentArchetype) and o.slug == MASTER_SLUG]
    assert len(masters) == 1
    master = masters[0]
    assert master.vertical_slug == VERTICAL_SLUG
    assert master.role_category == "master"
    assert master.status == "draft"
    assert master.tools_allowed == []

    community_managers = [
        o
        for o in session.added
        if isinstance(o, AgentArchetype) and o.slug == COMMUNITY_MANAGER_SLUG
    ]
    assert len(community_managers) == 1
    community_manager = community_managers[0]
    assert community_manager.vertical_slug == VERTICAL_SLUG
    assert community_manager.role_category == "communicator"
    assert community_manager.status == "draft"
    assert community_manager.tools_allowed == [
        "telegram_read_updates",
        "telegram_draft_message",
    ]
    # send_telegram (DANGEROUS) must never appear on this archetype.
    assert "send_telegram" not in community_manager.tools_allowed

    # Canonical order: master, community-manager, then the 4 reused
    # horizontal archetypes.
    assert ids[0] == master.id
    assert ids[1] == community_manager.id
    assert len(ids) == 6

    presets = [o for o in session.added if isinstance(o, TeamPreset) and o.slug == PRESET_SLUG]
    assert len(presets) == 1
    assert presets[0].archetype_ids == ids
    assert presets[0].vertical_slug == VERTICAL_SLUG
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
    master = _arc(MASTER_SLUG, vertical=VERTICAL_SLUG)
    community_manager = _arc(COMMUNITY_MANAGER_SLUG, vertical=VERTICAL_SLUG)
    telegram_preset = TeamPreset(
        vertical_slug=VERTICAL_SLUG,
        slug=PRESET_SLUG,
        display_name="Telegram-крейтор",
        archetype_ids=[master.id, community_manager.id, *[a.id for a in horizontal]],
    )
    telegram_preset.id = uuid4()
    session = StubSession(
        results=[
            *[Result(scalar=a) for a in horizontal],
            Result(scalar=horizontal_preset),
            Result(scalar=master),
            Result(scalar=community_manager),
            Result(scalar=telegram_preset),
        ]
    )

    ids, preset_id = await ensure_telegram_creator_seed(session)  # type: ignore[arg-type]

    assert session.added == []  # idempotent
    assert ids[0] == master.id
    assert ids[1] == community_manager.id
    assert preset_id == telegram_preset.id
