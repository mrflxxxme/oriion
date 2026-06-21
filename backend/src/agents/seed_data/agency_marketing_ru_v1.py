"""Seed: `agency-marketing-ru` v1 — first vertical preset with a Master-Agent.

Wave-1 reference vertical (ADR-029, AC-W1-3). Adds ONE Master archetype on top
of the horizontal `productivity-core` specialists (reused verbatim — the Master
carries the domain lens via its prompt + the strategic-context preamble, so the
operational Coordinator + leaf specialists stay domain-agnostic and shared).

Idempotent — re-running is a no-op via the natural-key conflict check
(vertical_slug + slug + prompt_version), mirroring
``seed_data.productivity_core_v1``.

Canonical vertical token = ``agency_marketing_ru`` (underscore): matches
``Cell.vertical_template_slug``, the master archetype's ``vertical_slug``, and
the master-prompt filename ``masters/agency_marketing_ru.md``. The human preset
slug is ``agency-marketing-ru`` (hyphen), like ``productivity-core``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import AgentArchetype, TeamPreset
from src.agents.seed_data.productivity_core_v1 import ensure_productivity_core_seed

VERTICAL_SLUG = "agency_marketing_ru"
PRESET_SLUG = "agency-marketing-ru"
PROMPT_VERSION = "0.1.0"
MASTER_SLUG = "master"


async def ensure_agency_marketing_ru_seed(session: AsyncSession) -> tuple[list[UUID], UUID]:
    """Insert (or load) the Marketing-agency Master + preset (reusing horizontal).

    Returns (archetype_ids_in_canonical_order, team_preset_id). Canonical order:
    master, coordinator, researcher, writer, analyst.
    """
    # Horizontal specialists (+ coordinator) are reused verbatim.
    horizontal_ids, _ = await ensure_productivity_core_seed(session)

    # The Master archetype — role_category reuses 'coordinator' (the schema CHECK
    # has no 'master'; adding it is a fast-follow). The actual per-call model is
    # chosen by role_key in LLMGatewayModel (master→chat, master_synthesis→R1);
    # model_name here is catalog metadata only.
    master_stmt = select(AgentArchetype).where(
        AgentArchetype.vertical_slug == VERTICAL_SLUG,
        AgentArchetype.slug == MASTER_SLUG,
        AgentArchetype.prompt_version == PROMPT_VERSION,
    )
    master = (await session.execute(master_stmt)).scalar_one_or_none()
    if master is None:
        master = AgentArchetype(
            slug=MASTER_SLUG,
            vertical_slug=VERTICAL_SLUG,
            display_name="Master «Маркетинговое агентство РФ»",
            role_category="coordinator",  # CHECK has no 'master' — reuse (AC-W1-3)
            prompt_version=PROMPT_VERSION,
            model_provider_slug="deepseek",
            model_name="deepseek-chat",
            tools_allowed=[],
            is_active=True,
            # AI-baseline draft (ADR-026 Pattern-D step 1). Promotion to 'reviewed'
            # is the founder's evaluator run (golden ≥75% + adversarial 100%);
            # friend-loop 'locked' is the Wave-2 retro.
            status="draft",
        )
        session.add(master)
        await session.flush()

    archetype_ids: list[UUID] = [master.id, *horizontal_ids]

    preset_stmt = select(TeamPreset).where(
        TeamPreset.vertical_slug == VERTICAL_SLUG,
        TeamPreset.slug == PRESET_SLUG,
    )
    preset = (await session.execute(preset_stmt)).scalar_one_or_none()
    if preset is None:
        preset = TeamPreset(
            vertical_slug=VERTICAL_SLUG,
            slug=PRESET_SLUG,
            display_name="Маркетинговое агентство РФ",
            description=(
                "Вертикальный preset Wave 1 с Master-Agent layer (ADR-029). "
                "Master (доменный CEO) → Координатор (COO) → Исследователь, "
                "Аналитик, Копирайтер. Демо-сценарий: план клиентской кампании."
            ),
            archetype_ids=archetype_ids,
            default_workflow_dag_json={
                "nodes": [
                    {"id": "master", "role": "master"},
                    {"id": "coordinator", "role": "coordinator"},
                    {"id": "researcher", "role": "researcher"},
                    {"id": "analyst", "role": "analyzer"},
                    {"id": "writer", "role": "writer"},
                ],
                "edges": [
                    {"from": "master", "to": "coordinator"},
                    {"from": "coordinator", "to": "researcher"},
                    {"from": "coordinator", "to": "analyst"},
                    {"from": "researcher", "to": "writer"},
                    {"from": "analyst", "to": "writer"},
                    {"from": "writer", "to": "coordinator"},
                    {"from": "coordinator", "to": "master"},
                ],
            },
        )
        session.add(preset)
        await session.flush()
    return archetype_ids, preset.id
