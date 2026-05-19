"""CellService — cell provisioning + member operations.

Per ADR-009 amendment 2026-05-19: per-cell schema (`cell_<uuid>`) and its
`memory_entries` table + HNSW index are materialized eagerly in the same TX
as the `cells` INSERT, via SQL function `multitenancy.provision_cell_schema`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src._stubs.audit import emit_audit_event  # 00.2.5 integration swaps to src.audit.services.audit_service.emit_audit_event
from src.multitenancy.events import (
    emit_cell_archived,
    emit_cell_created,
    emit_member_invited,
    emit_member_joined,
    emit_member_removed,
    emit_member_role_changed,
)
from src.multitenancy.exceptions import (
    CellNotFound,
    CellProvisioningError,
    MemberAlreadyExists,
    MemberNotFound,
)
from src.multitenancy.models import Cell, CellMember
from src.multitenancy.repositories.cell_member_repository import CellMemberRepository
from src.multitenancy.repositories.cell_repository import CellRepository

logger = structlog.get_logger(__name__)


class CellService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cell_repo = CellRepository(session)
        self._member_repo = CellMemberRepository(session)

    # ── cell lifecycle ────────────────────────────────────────────────────

    async def provision_cell(
        self,
        *,
        workspace_id: UUID,
        slug: str,
        display_name: str,
        vertical_template_slug: str | None,
        requested_by_user_id: UUID,
        settings: dict[str, Any] | None = None,
    ) -> Cell:
        """Create a cell + eager schema provision + audit emit.

        Single TX (caller's outer transaction): cells INSERT,
        provision_cell_schema(uuid) call, CloudEvent + audit emission. If
        provision_cell_schema fails we raise CellProvisioningError and let
        the session rollback unwind the cells INSERT.
        """
        cell = await self._cell_repo.create(
            workspace_id=workspace_id,
            slug=slug,
            display_name=display_name,
            vertical_template_slug=vertical_template_slug,
            settings=settings,
        )

        await self._call_provision_cell_schema(cell)

        await emit_cell_created(
            cell_id=cell.id,
            workspace_id=cell.workspace_id,
            created_at=cell.created_at,
            vertical_template_slug=cell.vertical_template_slug,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=requested_by_user_id,
            action="multitenancy.cell.created",
            resource_type="cell",
            resource_id=cell.id,
            payload={
                "workspace_id": str(cell.workspace_id),
                "slug": cell.slug,
                "vertical_template_slug": cell.vertical_template_slug,
            },
        )

        logger.info(
            "multitenancy.cell.provisioned",
            cell_id=str(cell.id),
            workspace_id=str(cell.workspace_id),
            requested_by=str(requested_by_user_id),
        )
        return cell

    async def archive_cell(self, *, cell_id: UUID, archived_by: UUID) -> None:
        cell = await self._cell_repo.find_by_id(cell_id)
        if cell is None:
            raise CellNotFound()
        await self._cell_repo.archive(cell_id)
        archived_at = datetime.now(UTC)
        await emit_cell_archived(
            cell_id=cell_id,
            archived_by=archived_by,
            archived_at=archived_at,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=archived_by,
            action="multitenancy.cell.archived",
            resource_type="cell",
            resource_id=cell_id,
            payload={"archived_at": archived_at.isoformat()},
        )

    # ── member operations ────────────────────────────────────────────────

    async def add_creator_as_owner(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        owner_role_id: UUID,
    ) -> CellMember:
        """Add the user who created the cell as an owner-role member.

        Called by provision flows that need the creator to immediately have
        visibility (RLS membership EXISTS) over the new cell.
        """
        existing = await self._member_repo.find_by_cell_user(cell_id, user_id)
        if existing is not None:
            return existing
        member = await self._member_repo.add_member(
            cell_id=cell_id,
            user_id=user_id,
            role_id=owner_role_id,
            invited_by=None,
        )
        await emit_member_joined(
            cell_id=cell_id,
            user_id=user_id,
            role_id=owner_role_id,
            joined_at=member.joined_at,
        )
        return member

    async def invite_member(
        self,
        *,
        cell_id: UUID,
        email: str,
        role_id: UUID,
        invited_by: UUID,
    ) -> tuple[UUID, datetime]:
        """Wave-0 simplification: emit member.invited.v1 + audit. The
        sibling invitations table per api.yaml is forward-declared (see
        contract README — "not modelled in this schema.sql to keep the W0
        surface tight"). Returns (invitation_id, expires_at_placeholder).
        """
        # Confirm the cell exists so the router can map to 404 cleanly.
        cell = await self._cell_repo.find_by_id(cell_id)
        if cell is None:
            raise CellNotFound()
        # The sibling invitations table doesn't exist in W0, so we synthesize
        # a deterministic invitation_id keyed off (cell_id, email) for audit
        # de-dup. 7-day expiry placeholder (matches the Wave-1 default).
        from uuid import NAMESPACE_OID, uuid5

        invitation_id = uuid5(NAMESPACE_OID, f"invite:{cell_id}:{email}")
        expires_at = datetime.now(UTC).replace(microsecond=0)
        await emit_member_invited(
            invitation_id=invitation_id,
            cell_id=cell_id,
            email=email,
            role_id=role_id,
            invited_by=invited_by,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=invited_by,
            action="multitenancy.member.invited",
            resource_type="cell",
            resource_id=cell_id,
            payload={"email": email, "role_id": str(role_id)},
        )
        return (invitation_id, expires_at)

    async def change_role(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        new_role_id: UUID,
        changed_by: UUID,
    ) -> CellMember:
        member = await self._member_repo.find_by_cell_user(cell_id, user_id)
        if member is None:
            raise MemberNotFound()
        if member.role_id == new_role_id:
            return member
        old_role_id = member.role_id
        await self._member_repo.update_role(
            cell_id=cell_id, user_id=user_id, new_role_id=new_role_id
        )
        await emit_member_role_changed(
            cell_id=cell_id,
            user_id=user_id,
            old_role_id=old_role_id,
            new_role_id=new_role_id,
            changed_by=changed_by,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=changed_by,
            action="multitenancy.member.role_changed",
            resource_type="cell",
            resource_id=cell_id,
            payload={
                "user_id": str(user_id),
                "old_role_id": str(old_role_id),
                "new_role_id": str(new_role_id),
            },
        )
        # Refresh the row so the caller sees the new role_id on the returned
        # ORM instance.
        member.role_id = new_role_id
        return member

    async def remove_member(
        self,
        *,
        cell_id: UUID,
        user_id: UUID,
        removed_by: UUID,
    ) -> None:
        member = await self._member_repo.find_by_cell_user(cell_id, user_id)
        if member is None:
            raise MemberNotFound()
        await self._member_repo.remove(cell_id=cell_id, user_id=user_id)
        removed_at = datetime.now(UTC)
        await emit_member_removed(
            cell_id=cell_id,
            user_id=user_id,
            removed_by=removed_by,
            removed_at=removed_at,
        )
        await emit_audit_event(
            actor_type="user",
            actor_id=removed_by,
            action="multitenancy.member.removed",
            resource_type="cell",
            resource_id=cell_id,
            payload={"user_id": str(user_id), "removed_at": removed_at.isoformat()},
        )

    async def list_members(self, *, cell_id: UUID) -> list[CellMember]:
        return await self._member_repo.list_by_cell(cell_id)

    async def assert_member_unique(self, *, cell_id: UUID, user_id: UUID) -> None:
        """Pre-check to surface a 409 before invite emit.

        Note: the DB-level unique index `cell_members_cell_user_uidx` is the
        authoritative guard against duplicate rows; this helper exists so
        routers can return a clean 409 before a costly side-effect (emit).
        """
        if await self._member_repo.find_by_cell_user(cell_id, user_id) is not None:
            raise MemberAlreadyExists()

    # ── internals ────────────────────────────────────────────────────────

    async def _call_provision_cell_schema(self, cell: Cell) -> None:
        expected = f"cell_{str(cell.id).replace('-', '_')}"
        result = await self._session.execute(
            text("SELECT multitenancy.provision_cell_schema(:cell_id)"),
            {"cell_id": str(cell.id)},
        )
        schema_name = result.scalar()
        if schema_name != expected:
            raise CellProvisioningError(
                f"provision_cell_schema returned {schema_name!r}, expected {expected!r}"
            )
