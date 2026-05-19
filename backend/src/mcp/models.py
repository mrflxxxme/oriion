"""SQLAlchemy 2.x models for mcp bounded context.

Schema is authoritative per contracts/mcp/schema.sql (SKELETON in Wave 0
per ADR-024). Tables live under PostgreSQL schema `mcp`. Migrations:
  backend/migrations/versions/mcp/0001_mcp_connections.py

Wave 0 ships a single table — `mcp.mcp_connections`. The mcp_tools +
mcp_health_log SKELETON tables from contracts/mcp/schema.sql remain
unmaterialized (deferred to Milestone D / Wave 2 — production MCP infra).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src._shared.db.base import Base


def _uuid_pk() -> Mapped[UUID]:
    """uuid primary key with DB-side gen_random_uuid() default."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _ts_default_now() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"), nullable=False)


class MCPConnection(Base):
    """Wave 0 minimal MCP server connection record.

    Workspace-scoped (workspace_id) with optional cell-scoping (cell_id).
    `server_type` constrained to ``stdio`` | ``http`` (Wave 0 supported
    transports; ``sse`` / ``websocket`` deferred to Wave 2 per ADR-013).
    `capabilities` is provider-advertised JSON (tool list, supported
    features) — opaque to Wave 0 storage; Wave 1+ adds schema validation.
    """

    __tablename__ = "mcp_connections"
    __table_args__ = (
        CheckConstraint(
            "server_type IN ('stdio','http')",
            name="mcp_connections_server_type_check",
        ),
        Index(
            "mcp_connections_workspace_name_idx",
            "workspace_id",
            "name",
        ),
        Index(
            "mcp_connections_workspace_active_idx",
            "workspace_id",
            postgresql_where=text("is_active = true"),
        ),
        {"schema": "mcp"},
    )

    id: Mapped[UUID] = _uuid_pk()
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    cell_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    server_type: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
