"""Seed: `telegram-creator` v1 — second Wave-1 vertical with a Master-Agent.

Second Wave-1 vertical per ADR-029, ADR-017 catalog entry #2 ("Telegram-крейтор
/ Курс-автор"). Adds a Master archetype + ONE vertical-specific specialist
(`community-manager` — reads channel activity and prepares platform-native
Telegram drafts) on top of the horizontal `productivity-core` specialists
(reused verbatim — mirrors ``seed_data.agency_marketing_ru_v1``, the first
Wave-1 vertical).

Idempotent — re-running is a no-op via the natural-key conflict check
(vertical_slug + slug + prompt_version), mirroring
``seed_data.agency_marketing_ru_v1`` / ``seed_data.productivity_core_v1``.

Canonical vertical token = ``telegram_creator`` (underscore): matches
``Cell.vertical_template_slug``, the master archetype's ``vertical_slug``, and
the master-prompt filename ``masters/telegram_creator.md``. The human preset
slug is ``telegram-creator`` (hyphen), like ``agency-marketing-ru``.

``community-manager`` is the only archetype in this preset carrying the
Telegram-bot connector tools (01.9b, ADR-041) in ``tools_allowed`` —
``telegram_read_updates`` (READ_ONLY) + ``telegram_draft_message`` (INTERNAL),
per ``src.security.capability.TOOL_RISK``. The paired ``send_telegram`` tool
is DANGEROUS (deny-until-approval-UI, 01.12) and intentionally NOT listed —
this vertical is read+draft only this phase.

Domain grounding: ``.planning/verticals/telegram-creator/domain-brief.md``
(cited research on RU Telegram content-creator ICP, monetization, ad-law).

Known gap (by design, out of scope this phase): ``team_provisioning_service.py``
does not yet special-case ``PRESET_SLUG`` the way it does for
``agency_marketing_ru_v1.PRESET_SLUG`` — the evaluator run does not need that
wiring (it calls ``load_master_prompt`` + the Master agent factories directly,
per ``scripts/live_golden_master.py``'s pattern), but the product-UI
provisioning path needs it before this preset is user-selectable end-to-end.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import AgentArchetype, TeamPreset
from src.agents.seed_data.productivity_core_v1 import ensure_productivity_core_seed

VERTICAL_SLUG = "telegram_creator"
PRESET_SLUG = "telegram-creator"
PROMPT_VERSION = "0.1.0"
MASTER_SLUG = "master"
COMMUNITY_MANAGER_SLUG = "community-manager"


async def ensure_telegram_creator_seed(session: AsyncSession) -> tuple[list[UUID], UUID]:
    """Insert (or load) the Telegram-creator Master + community-manager + preset.

    Returns (archetype_ids_in_canonical_order, team_preset_id). Canonical
    order: master, community-manager, coordinator, researcher, writer, analyst.
    """
    # Horizontal specialists (+ coordinator) are reused verbatim.
    horizontal_ids, _ = await ensure_productivity_core_seed(session)

    # The Master archetype — role_category='master' (CHECK extended in
    # agents_0004, same migration agency_marketing_ru_v1 relies on).
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
            display_name="Master «Telegram-крейтор»",
            role_category="master",
            prompt_version=PROMPT_VERSION,
            model_provider_slug="deepseek",
            model_name="deepseek-chat",
            tools_allowed=[],
            is_active=True,
            # AI-baseline draft (ADR-026 Pattern-D step 1 + §7 research-first).
            # Promotion to 'reviewed' is the founder's evaluator run (golden
            # ≥75% + adversarial 100%); friend-loop 'locked' is Wave-2 retro.
            status="draft",
        )
        session.add(master)
        await session.flush()

    # The vertical-specific Community-manager — role_category='communicator'
    # (an existing CHECK value, added alongside 'master' in agents_0004 but
    # unused until now; reused here so no new migration is needed, mirroring
    # how memory_curator_v1 reuses role_category='analyzer'). This is the
    # ONLY archetype in this preset carrying the connector tools_allowed.
    cm_stmt = select(AgentArchetype).where(
        AgentArchetype.vertical_slug == VERTICAL_SLUG,
        AgentArchetype.slug == COMMUNITY_MANAGER_SLUG,
        AgentArchetype.prompt_version == PROMPT_VERSION,
    )
    community_manager = (await session.execute(cm_stmt)).scalar_one_or_none()
    if community_manager is None:
        community_manager = AgentArchetype(
            slug=COMMUNITY_MANAGER_SLUG,
            vertical_slug=VERTICAL_SLUG,
            display_name="Комьюнити-менеджер «Telegram-крейтор»",
            role_category="communicator",
            prompt_version=PROMPT_VERSION,
            model_provider_slug="deepseek",
            model_name="deepseek-chat",
            # 01.9b connector tools (READ + DRAFT only). `send_telegram` is
            # DANGEROUS and intentionally excluded — see module docstring.
            tools_allowed=["telegram_read_updates", "telegram_draft_message"],
            is_active=True,
            status="draft",
        )
        session.add(community_manager)
        await session.flush()

    archetype_ids: list[UUID] = [master.id, community_manager.id, *horizontal_ids]

    preset_stmt = select(TeamPreset).where(
        TeamPreset.vertical_slug == VERTICAL_SLUG,
        TeamPreset.slug == PRESET_SLUG,
    )
    preset = (await session.execute(preset_stmt)).scalar_one_or_none()
    if preset is None:
        preset = TeamPreset(
            vertical_slug=VERTICAL_SLUG,
            slug=PRESET_SLUG,
            display_name="Telegram-крейтор",
            description=(
                "Вертикальный preset Wave 1 с Master-Agent layer (ADR-029). "
                "Master (доменный CEO) → Координатор (COO) → Исследователь, "
                "Аналитик, Копирайтер, Комьюнити-менеджер (read+draft "
                "Telegram-connector). Демо-сценарий: контент-план + "
                "комплаенс-аудит спонсорского поста."
            ),
            archetype_ids=archetype_ids,
            default_workflow_dag_json={
                "nodes": [
                    {"id": "master", "role": "master"},
                    {"id": "coordinator", "role": "coordinator"},
                    {"id": "researcher", "role": "researcher"},
                    {"id": "analyst", "role": "analyzer"},
                    {"id": "writer", "role": "writer"},
                    {"id": "community_manager", "role": "communicator"},
                ],
                "edges": [
                    {"from": "master", "to": "coordinator"},
                    {"from": "coordinator", "to": "researcher"},
                    {"from": "coordinator", "to": "analyst"},
                    {"from": "coordinator", "to": "community_manager"},
                    {"from": "researcher", "to": "writer"},
                    {"from": "analyst", "to": "writer"},
                    {"from": "community_manager", "to": "writer"},
                    {"from": "writer", "to": "community_manager"},
                    {"from": "community_manager", "to": "coordinator"},
                    {"from": "coordinator", "to": "master"},
                ],
            },
        )
        session.add(preset)
        await session.flush()
    return archetype_ids, preset.id
