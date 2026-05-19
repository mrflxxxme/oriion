"""WorkspaceService + provision_initial_workspace.

The public free function ``provision_initial_workspace`` is the symbol
consumed by ``iam.auth_service.register()`` (wired here as of Phase 00.2.5
integration, PR #32).

Signature: ``(session, user_id, email_localpart) -> WorkspaceProvisionResult``.
Needs a live DB session to insert rows and the email-localpart to derive
the workspace slug. ``AuthService.register`` passes its request-scoped
``AsyncSession`` through so the workspace + cell INSERTs commit atomically
with the user row.

Logic per contracts/multitenancy/README.md "Service contract":
  1. INSERT workspace (slug=email_localpart sanitized, display_name=email_localpart,
     plan_tier='free').
  2. INSERT cell (slug='default', display_name='Default cell',
     vertical_template_slug=None).
  3. CALL multitenancy.provision_cell_schema(cell.id) via raw SQL.
  4. emit workspace.created.v1 + cell.created.v1 CloudEvents.
  5. Idempotent on user_id — re-invocation returns existing IDs by slug lookup.

This service intentionally does NOT add the user as a cell_member —
``CellService.add_creator_as_owner`` handles that during normal cell
provisioning (W0 auth flow has no concept of "owner role" yet; the
00.4 onboarding wizard sets up RBAC assignments).
"""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.multitenancy.events import emit_cell_created, emit_workspace_created
from src.multitenancy.exceptions import CellProvisioningError
from src.multitenancy.models import Cell, Workspace
from src.multitenancy.repositories.cell_repository import CellRepository
from src.multitenancy.repositories.workspace_repository import (
    PlanTier,
    WorkspaceRepository,
)

logger = structlog.get_logger(__name__)


class WorkspaceProvisionResult(BaseModel):
    """Returned by provision_initial_workspace.

    Result shape: workspace_id + cell_id. Consumed by
    ``AuthService.register`` to populate the ``RegisterResult`` response.
    """

    workspace_id: UUID
    cell_id: UUID


# ── slug helpers ──────────────────────────────────────────────────────────


_SLUG_RE = re.compile(r"[^a-z0-9-]+")
_MULTI_DASH_RE = re.compile(r"-+")


def _sanitize_slug(raw: str) -> str:
    """Lowercase, replace non-[a-z0-9-] with '-', collapse repeats, strip ends.

    Empty input falls back to 'workspace' so we never INSERT an empty slug.
    """
    lowered = raw.lower()
    safe = _SLUG_RE.sub("-", lowered)
    collapsed = _MULTI_DASH_RE.sub("-", safe).strip("-")
    return collapsed or "workspace"


# ── service class (used by routers) ──────────────────────────────────────


class WorkspaceService:
    """Wave-0 workspace orchestration.

    Wraps repositories + events. The router layer constructs an instance
    via FastAPI Depends(); see src.multitenancy.routers.workspaces.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._workspace_repo = WorkspaceRepository(session)
        self._cell_repo = CellRepository(session)

    async def create_workspace(
        self,
        *,
        display_name: str,
        slug: str | None,
        billing_email: str | None,
        plan_tier: PlanTier,
        created_by_user_id: UUID,
    ) -> Workspace:
        """Create a new workspace + emit oriion.multitenancy.workspace.created.v1.

        Slug collision raises WorkspaceSlugConflict at the DB layer (unique
        partial index); the router maps that to 409.
        """
        effective_slug = _sanitize_slug(slug or display_name)
        workspace = await self._workspace_repo.create(
            slug=effective_slug,
            display_name=display_name,
            billing_email=billing_email,
            plan_tier=plan_tier,
        )
        await emit_workspace_created(
            workspace_id=workspace.id,
            slug=workspace.slug,
            plan_tier=_narrow_plan_tier(workspace.plan_tier),
            created_by_user_id=created_by_user_id,
        )
        return workspace

    async def find_by_id(self, workspace_id: UUID) -> Workspace | None:
        return await self._workspace_repo.find_by_id(workspace_id)

    async def list_for_user(self, user_id: UUID) -> list[Workspace]:
        return await self._workspace_repo.find_by_user_id(user_id)


# ── public service contract ──────────────────────────────────────────────


async def provision_initial_workspace(
    session: AsyncSession,
    user_id: UUID,
    email_localpart: str,
) -> WorkspaceProvisionResult:
    """Seed the user's first workspace + initial cell.

    Called synchronously by iam.auth_service.register() AFTER the user row
    is persisted and BEFORE the email-verification token is issued (so the
    user has a valid {workspace_id, cell_id} on first login).

    Invariants:
      * Exactly one workspace + one cell per user from this call.
      * Workspace slug + display_name derived from email_localpart
        (sanitized via _sanitize_slug; user can rename via PATCH later).
      * plan_tier = 'free' (W0 — paid tiers gated behind ЮKassa flow).
      * Idempotent on (user_id) — re-invocation looks up the existing rows
        by slug and returns those IDs.

    The cell's per-schema `cell_<uuid>.memory_entries` table + HNSW index
    are materialized in the same TX via multitenancy.provision_cell_schema().
    """
    workspace_repo = WorkspaceRepository(session)
    cell_repo = CellRepository(session)

    slug = _sanitize_slug(email_localpart)

    # Idempotent path: if a workspace with this slug already exists, treat
    # the registration as a replay and return the existing IDs. The slug is
    # globally unique among active workspaces (partial unique index) so the
    # lookup is safe.
    existing_workspace = await workspace_repo.find_by_slug_active(slug)
    if existing_workspace is not None:
        existing_cell = await cell_repo.find_by_workspace_slug(existing_workspace.id, "default")
        if existing_cell is not None:
            logger.info(
                "multitenancy.provision_initial_workspace.replay",
                user_id=str(user_id),
                workspace_id=str(existing_workspace.id),
                cell_id=str(existing_cell.id),
            )
            return WorkspaceProvisionResult(
                workspace_id=existing_workspace.id,
                cell_id=existing_cell.id,
            )

    workspace = await workspace_repo.create(
        slug=slug,
        display_name=email_localpart,
        billing_email=None,
        plan_tier="free",
    )

    cell = await cell_repo.create(
        workspace_id=workspace.id,
        slug="default",
        display_name="Default cell",
        vertical_template_slug=None,
        settings=None,
    )

    # Eager per-cell schema provisioning (ADR-009 amendment 2026-05-19).
    await _call_provision_cell_schema(session, cell)

    correlation = f"provision_initial:{user_id}"
    await emit_workspace_created(
        workspace_id=workspace.id,
        slug=workspace.slug,
        plan_tier="free",
        created_by_user_id=user_id,
        correlation_id=correlation,
    )
    await emit_cell_created(
        cell_id=cell.id,
        workspace_id=workspace.id,
        created_at=cell.created_at,
        vertical_template_slug=cell.vertical_template_slug,
        correlation_id=correlation,
    )

    logger.info(
        "multitenancy.provision_initial_workspace.created",
        user_id=str(user_id),
        workspace_id=str(workspace.id),
        cell_id=str(cell.id),
    )

    return WorkspaceProvisionResult(
        workspace_id=workspace.id,
        cell_id=cell.id,
    )


async def _call_provision_cell_schema(session: AsyncSession, cell: Cell) -> None:
    """Invoke the SQL function and validate the returned schema name."""
    expected = f"cell_{str(cell.id).replace('-', '_')}"
    result = await session.execute(
        text("SELECT multitenancy.provision_cell_schema(:cell_id)"),
        {"cell_id": str(cell.id)},
    )
    schema_name = result.scalar()
    if schema_name != expected:
        raise CellProvisioningError(
            f"provision_cell_schema returned {schema_name!r}, expected {expected!r}"
        )


def _narrow_plan_tier(value: str) -> Literal["free", "starter", "pro", "enterprise"]:
    """mypy --strict needs the Literal narrowing; the CHECK constraint at the
    DB layer guarantees one of these four values."""
    if value not in ("free", "starter", "pro", "enterprise"):
        # Should be unreachable; the DB CHECK constraint guarantees this.
        raise CellProvisioningError(f"invalid plan_tier from DB: {value!r}")
    return value  # type: ignore[return-value]
