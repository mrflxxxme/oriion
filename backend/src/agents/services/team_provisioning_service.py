"""TeamProvisioningService — provision a team-preset into a cell.

Wave 0 single-team-per-cell happy path:
    1. Ensure productivity-core seed exists (idempotent — uses ON CONFLICT
       DO NOTHING on the unique key for archetypes).
    2. Look up the preset by slug.
    3. Insert one agent_instance per archetype_id under the cell.
    4. Emit team_provisioned.v1 + instance_created.v1 CloudEvents.
    5. Return the AgentInstance rows.

Re-invocation on the same cell is idempotent: if the cell already has an
instance for an archetype, skip insertion (audit-friendly).
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents import events as agents_events
from src.agents.exceptions import TeamPresetNotFound
from src.agents.models import AgentArchetype, AgentInstance, TeamPreset
from src.agents.seed_data.agency_marketing_ru_v1 import (
    PRESET_SLUG as AGENCY_MARKETING_PRESET_SLUG,
)
from src.agents.seed_data.agency_marketing_ru_v1 import ensure_agency_marketing_ru_seed
from src.agents.seed_data.memory_curator_v1 import ensure_memory_curator_archetype
from src.agents.seed_data.productivity_core_v1 import ensure_productivity_core_seed

logger = structlog.get_logger(__name__)


class TeamProvisioning(Protocol):
    """Port for provisioning a team-preset into a cell (AC-W1-7).

    Lets ``AuthService`` depend on the capability rather than the concrete
    service, so the optional-``None`` constructor seam collapses: unit tests
    inject the ``NullTeamProvisioningService`` no-op, production wires the real
    ``TeamProvisioningService`` (``iam/deps.py``).
    """

    async def provision_team(
        self, *, preset_slug: str, cell_id: UUID, user_id: UUID
    ) -> list[AgentInstance]: ...


class TeamProvisioningService:
    """Coordinates archetype seeding + agent_instance creation per cell."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def provision_team(
        self,
        *,
        preset_slug: str,
        cell_id: UUID,
        user_id: UUID,
    ) -> list[AgentInstance]:
        """Provision the requested preset into the cell.

        Idempotent: re-running for an already-provisioned cell is a no-op
        (returns the existing instances).
        """
        # Idempotent seed. AC-W1-3: the Marketing-agency vertical seed adds its
        # Master archetype + preset on top of the horizontal specialists (it
        # ensures the productivity-core base itself); every other preset just
        # needs the horizontal base.
        if preset_slug == AGENCY_MARKETING_PRESET_SLUG:
            await ensure_agency_marketing_ru_seed(self._session)
        else:
            await ensure_productivity_core_seed(self._session)

        # 01.4b: ensure the horizontal memory-curator archetype exists so the
        # worker can bill auto-extraction steps (the NOT-NULL
        # task_steps.agent_archetype_id FK) for any task in this cell. Not a team
        # member → no agent_instance, not in any preset; idempotent like the seeds.
        await ensure_memory_curator_archetype(self._session)

        preset = await self._load_preset(preset_slug)

        # Map archetype_id → existing AgentInstance for this cell.
        existing_stmt = select(AgentInstance).where(
            AgentInstance.cell_id == cell_id,
            AgentInstance.archived_at.is_(None),
        )
        existing_rows = (await self._session.execute(existing_stmt)).scalars().all()
        existing_by_archetype = {row.agent_archetype_id: row for row in existing_rows}

        instances: list[AgentInstance] = []
        newly_created: list[AgentInstance] = []
        for archetype_id in preset.archetype_ids:
            if archetype_id in existing_by_archetype:
                instances.append(existing_by_archetype[archetype_id])
                continue
            instance = AgentInstance(
                cell_id=cell_id,
                agent_archetype_id=archetype_id,
            )
            self._session.add(instance)
            await self._session.flush()  # materialize instance.id
            instances.append(instance)
            newly_created.append(instance)

        # Audit emission — outside the per-row loop to avoid event-spam on
        # idempotent re-runs.
        if newly_created:
            await agents_events.emit_team_provisioned(
                cell_id=cell_id,
                team_preset_id=preset.id,
                preset_slug=preset.slug,
                agent_instance_ids=[inst.id for inst in newly_created],
                provisioned_by_user_id=user_id,
            )
            archetype_slug_map = await self._archetype_slug_map(
                [inst.agent_archetype_id for inst in newly_created]
            )
            for inst in newly_created:
                await agents_events.emit_instance_created(
                    agent_instance_id=inst.id,
                    cell_id=cell_id,
                    agent_archetype_id=inst.agent_archetype_id,
                    archetype_slug=archetype_slug_map.get(inst.agent_archetype_id, "unknown"),
                )

        return instances

    async def _load_preset(self, preset_slug: str) -> TeamPreset:
        stmt = select(TeamPreset).where(TeamPreset.slug == preset_slug)
        preset = (await self._session.execute(stmt)).scalar_one_or_none()
        if preset is None:
            raise TeamPresetNotFound(
                f"team_preset slug={preset_slug!r} not found. Seed runs at "
                "first call to ensure_productivity_core_seed."
            )
        return preset

    async def _archetype_slug_map(self, archetype_ids: list[UUID]) -> dict[UUID, str]:
        if not archetype_ids:
            return {}
        stmt = select(AgentArchetype.id, AgentArchetype.slug).where(
            AgentArchetype.id.in_(archetype_ids)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}


class NullTeamProvisioningService:
    """No-op ``TeamProvisioning`` (AC-W1-7).

    The default collaborator for ``AuthService`` in contexts that do not
    provision a team (unit tests, CLI / admin flows). Mirrors
    ``NoOpEmailSender``: silent, returns the empty result. Production wiring
    (``iam/deps.py``) supplies the real ``TeamProvisioningService``.
    """

    async def provision_team(
        self, *, preset_slug: str, cell_id: UUID, user_id: UUID
    ) -> list[AgentInstance]:
        logger.debug(
            "NullTeamProvisioningService — provisioning skipped (no-op default)",
            preset_slug=preset_slug,
            cell_id=str(cell_id),
            user_id=str(user_id),
        )
        return []


# Stateless no-op → safe to share one module-level instance as the AuthService
# default (collapses the optional-`None` constructor seam — AC-W1-7).
NULL_TEAM_PROVISIONING: TeamProvisioning = NullTeamProvisioningService()
