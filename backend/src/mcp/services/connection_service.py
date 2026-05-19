"""CRUD service for mcp.mcp_connections.

Wave 0 surface — Phase 00.4 § Task 14:
    * `create` — register a connection (rejects soft-validation errors).
    * `get` — fetch by id.
    * `list_by_workspace` — workspace-scoped list (RLS enforces isolation
      via GUC; service does NOT inject workspace_id into the WHERE clause).
    * `deactivate` — flip is_active=False (Wave 0 soft-delete proxy; no
      tombstone column yet — added Wave 2 with full DDL).

RLS contract
------------
This service assumes `set_tenant_context` was already called by the
upstream FastAPI dependency. Queries do not filter on workspace_id —
PostgreSQL RLS does. The `list_by_workspace` parameter is therefore a
caller-side sanity check + filter (cells/workspaces span), not the
security boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.models import MCPConnection
from src.mcp.schemas import MCPConnectionCreate

logger = structlog.get_logger(__name__)


class MCPConnectionService:
    """Async CRUD over `mcp.mcp_connections`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, cmd: MCPConnectionCreate) -> MCPConnection:
        """Insert a new MCP connection.

        Caller is responsible for unique-name enforcement at the business
        layer (Wave 0 DDL has no unique index — additive change Wave 2).
        """
        row = MCPConnection(
            workspace_id=cmd.workspace_id,
            cell_id=cmd.cell_id,
            name=cmd.name,
            server_type=cmd.server_type,
            endpoint=cmd.endpoint,
            capabilities=cmd.capabilities,
            is_active=cmd.is_active,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        logger.info(
            "mcp.connection.created",
            connection_id=str(row.id),
            workspace_id=str(row.workspace_id),
            server_type=row.server_type,
        )
        return row

    async def get(self, connection_id: UUID) -> MCPConnection | None:
        """Fetch by id. Returns None if missing (or filtered by RLS)."""
        stmt = select(MCPConnection).where(MCPConnection.id == connection_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        only_active: bool = True,
    ) -> Sequence[MCPConnection]:
        """List connections for the given workspace.

        RLS handles cross-workspace isolation; the `workspace_id` filter is
        a defence-in-depth narrowing for code paths that bypass RLS (e.g.
        an admin role with bypassrls — none in Wave 0). Wave 1+ APIs should
        still pass workspace_id explicitly for clarity.
        """
        stmt = select(MCPConnection).where(MCPConnection.workspace_id == workspace_id)
        if only_active:
            stmt = stmt.where(MCPConnection.is_active.is_(True))
        stmt = stmt.order_by(MCPConnection.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def deactivate(self, connection_id: UUID) -> bool:
        """Flip `is_active` to False. Returns True if a row was updated."""
        stmt = (
            update(MCPConnection).where(MCPConnection.id == connection_id).values(is_active=False)
        )
        result = await self._session.execute(stmt)
        # `Result.rowcount` is declared on CursorResult (returned by DML
        # statements). Type-narrow via getattr so mypy --strict is happy
        # without coercing the whole call site to CursorResult.
        rowcount_attr: int = getattr(result, "rowcount", 0) or 0
        if rowcount_attr:
            logger.info(
                "mcp.connection.deactivated",
                connection_id=str(connection_id),
            )
        return bool(rowcount_attr)
