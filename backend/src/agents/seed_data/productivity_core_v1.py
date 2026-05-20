"""Seed: `productivity-core` v1 — horizontal team preset (Wave 0 anchor).

Four archetypes (coordinator, researcher, writer, analyst-as-analyzer) +
one team_preset bundling them. Idempotent — re-running is a no-op via
natural-key conflict check (vertical_slug + slug + prompt_version).

Per ADR-017 revision 2026-05-15: the Wave 0 horizontal anchor moved from
WB-Seller vertical to `productivity-core` horizontal preset.

Note on `analyst` ↔ `analyzer` mismatch: contracts/agents/schema.sql
enum has `analyzer` (the broader role category); the role-prompt file is
`contracts/role-prompts/analyst.md` (UI-facing slug). We use `analyst`
as the `slug` but `analyzer` as the `role_category` enum literal.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import AgentArchetype, TeamPreset

VERTICAL_SLUG = "horizontal"
PRESET_SLUG = "productivity-core"
PROMPT_VERSION = "0.1.0"

# (role_slug, role_category, display_name, model_provider, model, tools_allowed)
_ARCHETYPES: list[tuple[str, str, str, str, str, list[str]]] = [
    (
        "coordinator",
        "coordinator",
        "Координатор «Твои личные ассистенты»",
        "deepseek",
        "deepseek-reasoner",
        ["delegate_task", "web_search", "read_url"],
    ),
    (
        "researcher",
        "researcher",
        "Исследователь «Твои личные ассистенты»",
        "deepseek",
        "deepseek-chat",
        ["web_search", "read_url"],
    ),
    (
        "writer",
        "writer",
        "Копирайтер «Твои личные ассистенты»",
        "deepseek",
        "deepseek-chat",
        [],
    ),
    (
        "analyst",
        "analyzer",  # schema enum is 'analyzer' (broader); slug is 'analyst' (UI)
        "Аналитик «Твои личные ассистенты»",
        "deepseek",
        "deepseek-reasoner",
        [],
    ),
]


async def ensure_productivity_core_seed(session: AsyncSession) -> tuple[list[UUID], UUID]:
    """Insert (or load) the productivity-core archetypes + team_preset.

    Returns (archetype_ids_in_canonical_order, team_preset_id).
    Canonical order: coordinator, researcher, writer, analyst.
    """
    archetype_ids: list[UUID] = []

    for slug, role_category, display_name, provider, model, tools in _ARCHETYPES:
        # Natural-key lookup: (vertical_slug, slug, prompt_version) unique.
        existing_stmt = select(AgentArchetype).where(
            AgentArchetype.vertical_slug == VERTICAL_SLUG,
            AgentArchetype.slug == slug,
            AgentArchetype.prompt_version == PROMPT_VERSION,
        )
        existing = (await session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            archetype_ids.append(existing.id)
            continue

        archetype = AgentArchetype(
            slug=slug,
            vertical_slug=VERTICAL_SLUG,
            display_name=display_name,
            role_category=role_category,
            prompt_version=PROMPT_VERSION,
            model_provider_slug=provider,
            model_name=model,
            tools_allowed=tools,
            is_active=True,
            status="draft",  # Wave 0 first-pass; promote → 'locked' before public beta
        )
        session.add(archetype)
        await session.flush()
        archetype_ids.append(archetype.id)

    # Team preset.
    preset_stmt = select(TeamPreset).where(
        TeamPreset.vertical_slug == VERTICAL_SLUG,
        TeamPreset.slug == PRESET_SLUG,
    )
    preset = (await session.execute(preset_stmt)).scalar_one_or_none()
    if preset is None:
        preset = TeamPreset(
            vertical_slug=VERTICAL_SLUG,
            slug=PRESET_SLUG,
            display_name="Твои личные ассистенты",
            description=(
                "Горизонтальный preset для Wave 0 internal demo. Четыре роли: "
                "Координатор, Исследователь, Копирайтер, Аналитик. "
                "Master-Agent layer и vertical-packs — Wave 1+."
            ),
            archetype_ids=archetype_ids,
            default_workflow_dag_json={
                "nodes": [
                    {"id": "coordinator", "role": "coordinator"},
                    {"id": "researcher", "role": "researcher"},
                    {"id": "analyst", "role": "analyzer"},
                    {"id": "writer", "role": "writer"},
                ],
                "edges": [
                    {"from": "coordinator", "to": "researcher"},
                    {"from": "coordinator", "to": "analyst"},
                    {"from": "researcher", "to": "writer"},
                    {"from": "analyst", "to": "writer"},
                    {"from": "writer", "to": "coordinator"},
                ],
            },
        )
        session.add(preset)
        await session.flush()
    return archetype_ids, preset.id
