"""CloudEvents emitters for the multitenancy bounded context.

Each function wraps src._shared.cloudevents.emit_cloudevent with the
correct ce_type per contracts/multitenancy/events.yaml. Wave 0 transport
is structlog — emit_cloudevent's swap to Redis Streams in Wave 1+ will
not change call-sites.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from src._shared.cloudevents import emit_cloudevent

_SOURCE = "oriion://contexts/multitenancy"


async def emit_workspace_created(
    workspace_id: UUID,
    slug: str,
    plan_tier: Literal["free", "starter", "pro", "enterprise"],
    created_by_user_id: UUID,
    correlation_id: str | None = None,
) -> None:
    """oriion.multitenancy.workspace.created.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.workspace.created.v1",
        source=_SOURCE,
        data={
            "workspace_id": str(workspace_id),
            "slug": slug,
            "plan_tier": plan_tier,
            "created_by_user_id": str(created_by_user_id),
        },
        correlation_id=correlation_id,
    )


async def emit_workspace_plan_changed(
    workspace_id: UUID,
    old_plan: Literal["free", "starter", "pro", "enterprise"],
    new_plan: Literal["free", "starter", "pro", "enterprise"],
    changed_at: datetime,
) -> None:
    """oriion.multitenancy.workspace.plan_changed.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.workspace.plan_changed.v1",
        source=_SOURCE,
        data={
            "workspace_id": str(workspace_id),
            "old_plan": old_plan,
            "new_plan": new_plan,
            "changed_at": changed_at.isoformat(),
        },
    )


async def emit_cell_created(
    cell_id: UUID,
    workspace_id: UUID,
    created_at: datetime,
    vertical_template_slug: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """oriion.multitenancy.cell.created.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.cell.created.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "workspace_id": str(workspace_id),
            "vertical_template_slug": vertical_template_slug,
            "created_at": created_at.isoformat(),
        },
        correlation_id=correlation_id,
    )


async def emit_cell_archived(
    cell_id: UUID,
    archived_by: UUID,
    archived_at: datetime,
) -> None:
    """oriion.multitenancy.cell.archived.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.cell.archived.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "archived_by": str(archived_by),
            "archived_at": archived_at.isoformat(),
        },
    )


async def emit_member_invited(
    invitation_id: UUID,
    cell_id: UUID,
    email: str,
    role_id: UUID,
    invited_by: UUID,
) -> None:
    """oriion.multitenancy.member.invited.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.member.invited.v1",
        source=_SOURCE,
        data={
            "invitation_id": str(invitation_id),
            "cell_id": str(cell_id),
            "email": email,
            "role_id": str(role_id),
            "invited_by": str(invited_by),
        },
    )


async def emit_member_joined(
    cell_id: UUID,
    user_id: UUID,
    role_id: UUID,
    joined_at: datetime,
) -> None:
    """oriion.multitenancy.member.joined.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.member.joined.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "user_id": str(user_id),
            "role_id": str(role_id),
            "joined_at": joined_at.isoformat(),
        },
    )


async def emit_member_role_changed(
    cell_id: UUID,
    user_id: UUID,
    old_role_id: UUID,
    new_role_id: UUID,
    changed_by: UUID,
) -> None:
    """oriion.multitenancy.member.role_changed.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.member.role_changed.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "user_id": str(user_id),
            "old_role_id": str(old_role_id),
            "new_role_id": str(new_role_id),
            "changed_by": str(changed_by),
        },
    )


async def emit_member_removed(
    cell_id: UUID,
    user_id: UUID,
    removed_by: UUID,
    removed_at: datetime,
) -> None:
    """oriion.multitenancy.member.removed.v1."""
    await emit_cloudevent(
        ce_type="oriion.multitenancy.member.removed.v1",
        source=_SOURCE,
        data={
            "cell_id": str(cell_id),
            "user_id": str(user_id),
            "removed_by": str(removed_by),
            "removed_at": removed_at.isoformat(),
        },
    )
