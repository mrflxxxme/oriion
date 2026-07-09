"""SQLAlchemy 2.x models for mcp bounded context.

Schema is authoritative per contracts/mcp/schema.sql (SKELETON in Wave 0
per ADR-024). Tables live under PostgreSQL schema `mcp`. Migrations:
  backend/migrations/versions/mcp/0001_mcp_connections.py

Wave 0 shipped a single table — `mcp.mcp_connections`. Phase 01.9b adds
`mcp.connector_credentials` (KMS-encrypted per-workspace connector credential
custody; migration 0002). The mcp_tools + mcp_health_log SKELETON tables from
contracts/mcp/schema.sql remain unmaterialized (deferred to Milestone D /
Wave 2 — production MCP infra).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
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


class ConnectorCredential(Base):
    """KMS-encrypted per-workspace connector credential custody (Phase 01.9b).

    Connector security core, PASS A. Mirrors ``llm_gateway.byok_keys``: only the
    AES-256-GCM ciphertext (``cred_encrypted``) + a public-safe fingerprint
    (``cred_fingerprint = sha256(plaintext)[:8]``) are persisted — the plaintext
    connector secret (a bot token, an OAuth token, an SMTP password) is discarded
    right after encryption and is never stored or logged. Decrypt is on-demand via
    ``services.connector_credential_service``.

    ``connector_slug`` is CHECK-constrained to the Wave-1 connector set; pass B
    adds the connector clients that consume these credentials through the runtime
    capability gate. Workspace-scoped RLS via ``_shared.current_workspace_id()``
    (migration ``mcp/0002_connector_credentials``). Partial index on
    active + non-revoked rows for the owner-config listing path.
    """

    __tablename__ = "connector_credentials"
    __table_args__ = (
        CheckConstraint(
            "connector_slug IN ('telegram-bot','yandex-disk','imap-smtp')",
            name="connector_credentials_connector_slug_check",
        ),
        UniqueConstraint(
            "workspace_id",
            "connector_slug",
            "label",
            name="connector_credentials_unique_label",
        ),
        Index(
            "connector_credentials_workspace_active_idx",
            "workspace_id",
            postgresql_where=text("is_active = true AND revoked_at IS NULL"),
        ),
        {"schema": "mcp"},
    )

    id: Mapped[UUID] = _uuid_pk()
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("multitenancy.workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    connector_slug: Mapped[str] = mapped_column(Text, nullable=False)
    cred_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cred_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
