"""mcp.mcp_connections — Wave 0 minimal MCP server connection registry.

Per Phase 00.4 § Task 14-15 the `mcp` context owns third-party tool
integration via the Model Context Protocol (ADR-013). Wave 0 ships
**framework-only** (AC8): the table reserves the schema target, holds
workspace + optional cell scoping, and lets the in-process `MCPClient`
wrapper persist registered endpoints. Production MCP servers + per-tool
rows + health log are deferred to Milestone D / Wave 2 (per
contracts/mcp/schema.sql SKELETON note).

Schema deviation from contracts/mcp/schema.sql (SKELETON)
---------------------------------------------------------
The SKELETON file is intentionally placeholder (per ADR-024) and inlines
``organization_id``. Per the multitenancy naming-bridge amendment
(2026-05-19) the term is now ``workspace_id``; we materialise that
canonical name here so the table lines up with multitenancy.workspaces.
Detailed columns from the SKELETON TODO list (auth_config_jsonb,
last_health_check_at, etc.) are deferred to Wave 2.

RLS
---
``workspace_id`` isolation via ``_shared.current_workspace_id()`` GUC,
matching the 3-GUC layered model (ADR-009 amendment 2026-05-19). Missing
GUC → NULL → policy evaluates FALSE → default-deny.

Revision ID: mcp_0001_mcp_connections
Down revision: _shared_0002_current_user_id_helper
Branch label: mcp
"""

from __future__ import annotations

from alembic import op

revision: str = "mcp_0001_mcp_connections"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("mcp",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE mcp.mcp_connections (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL,
            cell_id         uuid,
            name            text NOT NULL,
            server_type     text NOT NULL
                CHECK (server_type IN ('stdio','http')),
            endpoint        text NOT NULL,
            capabilities    jsonb NOT NULL DEFAULT '{}'::jsonb,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE INDEX mcp_connections_workspace_name_idx
            ON mcp.mcp_connections (workspace_id, name);
        """
    )
    op.execute(
        """
        CREATE INDEX mcp_connections_workspace_active_idx
            ON mcp.mcp_connections (workspace_id)
            WHERE is_active = true;
        """
    )

    op.execute(
        "COMMENT ON TABLE mcp.mcp_connections IS "
        "'Wave 0 minimal MCP server endpoint registry. "
        "Workspace-scoped; cell_id NULL means workspace-wide. "
        "Production MCP infra (tools rows, health log) deferred Wave 2.';"
    )
    op.execute(
        "COMMENT ON COLUMN mcp.mcp_connections.endpoint IS "
        "'URL (http transport) or shell command line (stdio transport).';"
    )

    op.execute(
        """
        CREATE TRIGGER mcp_connections_set_updated_at
            BEFORE UPDATE ON mcp.mcp_connections
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # RLS — workspace_id isolation via _shared.current_workspace_id() GUC.
    op.execute("ALTER TABLE mcp.mcp_connections ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE mcp.mcp_connections FORCE  ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY mcp_connections_workspace_isolation
            ON mcp.mcp_connections
            USING (workspace_id = _shared.current_workspace_id());
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON mcp.mcp_connections TO oriion_app;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS mcp_connections_workspace_isolation ON mcp.mcp_connections;")
    op.execute("DROP TRIGGER IF EXISTS mcp_connections_set_updated_at ON mcp.mcp_connections;")
    op.execute("DROP TABLE IF EXISTS mcp.mcp_connections;")
