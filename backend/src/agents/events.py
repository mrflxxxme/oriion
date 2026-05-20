"""CloudEvents emitters for agents bounded context.

Per contracts/agents/events.yaml. Wave 0 transport is structlog via
src._shared.cloudevents.emit_cloudevent.
"""

from __future__ import annotations

from uuid import UUID

from src._shared.cloudevents import emit_cloudevent

_SOURCE = "oriion://contexts/agents"


async def emit_team_provisioned(
    cell_id: UUID,
    team_preset_id: UUID,
    preset_slug: str,
    agent_instance_ids: list[UUID],
    provisioned_by_user_id: UUID,
    correlation_id: str | None = None,
) -> None:
    """oriion.agents.team_provisioned.v1."""
    await emit_cloudevent(
        ce_type="oriion.agents.team_provisioned.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "team_preset_id": str(team_preset_id),
            "preset_slug": preset_slug,
            "agent_instance_ids": [str(x) for x in agent_instance_ids],
            "provisioned_by_user_id": str(provisioned_by_user_id),
        },
        correlation_id=correlation_id,
    )


async def emit_instance_created(
    agent_instance_id: UUID,
    cell_id: UUID,
    agent_archetype_id: UUID,
    archetype_slug: str,
    correlation_id: str | None = None,
) -> None:
    """oriion.agents.instance_created.v1."""
    await emit_cloudevent(
        ce_type="oriion.agents.instance_created.v1",
        source=_SOURCE,
        data={
            "agent_instance_id": str(agent_instance_id),
            "cell_id": str(cell_id),
            "agent_archetype_id": str(agent_archetype_id),
            "archetype_slug": archetype_slug,
        },
        correlation_id=correlation_id,
    )
