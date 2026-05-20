"""WorkspaceService + provision_initial_workspace.

The public free function ``provision_initial_workspace`` is the symbol
consumed by ``iam.auth_service.register()`` (wired here as of Phase 00.2.5
integration, PR #32).

Signature: ``(session, user_id, email_localpart) -> WorkspaceProvisionResult``.
Needs a live DB session to call the SECURITY DEFINER bootstrap function and
the email-localpart to derive the workspace slug. ``AuthService.register``
passes its request-scoped ``AsyncSession`` through so the workspace + cell +
cell_member INSERTs commit atomically with the user row.

Per Phase 00.5 Topic 1 (RLS Option A, 2026-05-20): provisioning is now
delegated to ``multitenancy.bootstrap_first_workspace(...)`` — a SECURITY
DEFINER SQL function introduced in migration
``multitenancy/0005_bootstrap_first_workspace_function.py``. The function
bypasses the FORCE-RLS INSERT WITH CHECK policies on
multitenancy.{workspaces, cells, cell_members} because at register-time
the user has no tenant GUC set yet (chicken-and-egg).

The function:
  1. Idempotent slug lookup → on replay returns existing IDs.
  2. INSERT workspace (slug, display_name=email_localpart, plan_tier='free').
  3. INSERT cell (slug='default', display_name='Default cell').
  4. INSERT cell_member (user → cell with rbac.system_roles 'owner').
  5. CALL multitenancy.provision_cell_schema(cell.id) — per-cell schema.

The application layer (this module) emits the CloudEvents (workspace.created.v1
+ cell.created.v1) so event-side semantics are unchanged from the pre-refactor
flow.
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
from src.multitenancy.models import Workspace
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

    Implementation note (Phase 00.5 Topic 1, RLS Option A, 2026-05-20):
    delegates to the SECURITY DEFINER SQL function
    ``multitenancy.bootstrap_first_workspace(p_user_id, p_workspace_slug,
    p_display_name)`` rather than issuing direct ORM INSERTs. Reason: the
    register-flow runs without any tenant GUC set, so direct INSERTs against
    multitenancy.{workspaces, cells, cell_members} would hit the FORCE-RLS
    INSERT WITH CHECK policies (current_user_id IS NOT NULL → fails). The
    SECURITY DEFINER function runs as the migration owner (BYPASSRLS), so
    the bootstrap escapes the RLS chicken-and-egg cleanly.

    Invariants (unchanged from pre-refactor):
      * Exactly one workspace + one cell + one cell_member per user.
      * Workspace slug + display_name derived from email_localpart.
      * plan_tier = 'free' (W0).
      * Idempotent on slug → returns existing IDs as a replay path.

    The function also materializes the per-cell ``cell_<uuid>.memory_entries``
    table + HNSW index via ``multitenancy.provision_cell_schema()``.
    """
    slug = _sanitize_slug(email_localpart)

    result = await session.execute(
        text(
            "SELECT workspace_id, cell_id, schema_name, was_replay "
            "FROM multitenancy.bootstrap_first_workspace(:user_id, :slug, :display_name)"
        ),
        {
            "user_id": str(user_id),
            "slug": slug,
            "display_name": email_localpart,
        },
    )
    row = result.first()
    if row is None:
        raise CellProvisioningError(
            "multitenancy.bootstrap_first_workspace returned no row " "(expected exactly 1)."
        )
    workspace_id_str, cell_id_str, schema_name, was_replay = row
    workspace_id = UUID(str(workspace_id_str))
    cell_id = UUID(str(cell_id_str))

    expected_schema = f"cell_{str(cell_id).replace('-', '_')}"
    if schema_name != expected_schema:
        raise CellProvisioningError(
            f"bootstrap_first_workspace returned schema {schema_name!r}, "
            f"expected {expected_schema!r}"
        )

    # Replay path: no CloudEvents (already emitted on first registration).
    if was_replay:
        logger.info(
            "multitenancy.provision_initial_workspace.replay",
            user_id=str(user_id),
            workspace_id=str(workspace_id),
            cell_id=str(cell_id),
        )
        return WorkspaceProvisionResult(workspace_id=workspace_id, cell_id=cell_id)

    # Fresh-create path: emit the two CloudEvents.
    # NOTE: SECURITY DEFINER bypasses RLS for the INSERTs but does not write
    # CloudEvents (which live in the application layer per ADR-024). We
    # issue them here so event semantics are unchanged from the pre-refactor
    # implementation.
    #
    # We avoid a follow-up SELECT against multitenancy.cells because the
    # session still has no tenant GUC set (the bootstrap is exactly what
    # makes the GUC possible). The cell's created_at is "moments ago" by
    # construction; vertical_template_slug is always NULL for the Wave-0
    # productivity-core preset. Application-clock timestamp matches what
    # the database wrote within tens of microseconds — acceptable for an
    # event that downstream consumers treat as wall-clock approximate.
    from datetime import UTC, datetime

    correlation = f"provision_initial:{user_id}"
    bootstrap_ts = datetime.now(UTC)
    await emit_workspace_created(
        workspace_id=workspace_id,
        slug=slug,
        plan_tier="free",
        created_by_user_id=user_id,
        correlation_id=correlation,
    )
    await emit_cell_created(
        cell_id=cell_id,
        workspace_id=workspace_id,
        created_at=bootstrap_ts,
        vertical_template_slug=None,
        correlation_id=correlation,
    )

    logger.info(
        "multitenancy.provision_initial_workspace.created",
        user_id=str(user_id),
        workspace_id=str(workspace_id),
        cell_id=str(cell_id),
    )

    return WorkspaceProvisionResult(
        workspace_id=workspace_id,
        cell_id=cell_id,
    )


def _narrow_plan_tier(value: str) -> Literal["free", "starter", "pro", "enterprise"]:
    """mypy --strict needs the Literal narrowing; the CHECK constraint at the
    DB layer guarantees one of these four values."""
    if value not in ("free", "starter", "pro", "enterprise"):
        # Should be unreachable; the DB CHECK constraint guarantees this.
        raise CellProvisioningError(f"invalid plan_tier from DB: {value!r}")
    return value  # type: ignore[return-value]
