"""Seed: memory-curator archetype (Phase 01.4b).

A single horizontal archetype that backs the auto-extraction filter + the
conversation summarizer ``task_steps``. It is NOT a team member (no
agent_instance, not bundled into any team_preset) — it exists only so the
NOT-NULL ``tasks.task_steps.agent_archetype_id`` FK resolves when the runtime
bills a memory-extraction step (``_resolve_archetype_id('memory_curator')``).

``role_category='analyzer'`` reuses an existing CHECK value (grill Q1,
2026-06-24) — no role_category migration. ``vertical_slug='horizontal'`` matches
the productivity-core base so one row serves every cell. Idempotent via the
natural key (vertical_slug, slug, prompt_version), like
``ensure_productivity_core_seed``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import AgentArchetype

SLUG = "memory_curator"
VERTICAL_SLUG = "horizontal"
PROMPT_VERSION = "0.1.0"
ROLE_CATEGORY = "analyzer"  # reuse existing CHECK value (grill Q1) — no migration
MODEL_PROVIDER_SLUG = "deepseek"
MODEL_NAME = "deepseek-chat"
DISPLAY_NAME = "Куратор памяти"


async def ensure_memory_curator_archetype(session: AsyncSession) -> UUID:
    """Insert (or load) the horizontal memory-curator archetype. Idempotent.

    Returns the archetype id. Natural key: (vertical_slug, slug, prompt_version).
    """
    existing_stmt = select(AgentArchetype).where(
        AgentArchetype.vertical_slug == VERTICAL_SLUG,
        AgentArchetype.slug == SLUG,
        AgentArchetype.prompt_version == PROMPT_VERSION,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return existing.id

    archetype = AgentArchetype(
        slug=SLUG,
        vertical_slug=VERTICAL_SLUG,
        display_name=DISPLAY_NAME,
        role_category=ROLE_CATEGORY,
        prompt_version=PROMPT_VERSION,
        model_provider_slug=MODEL_PROVIDER_SLUG,
        model_name=MODEL_NAME,
        tools_allowed=[],
        is_active=True,
        status="draft",
    )
    session.add(archetype)
    await session.flush()
    return archetype.id


__all__ = ["ensure_memory_curator_archetype"]
