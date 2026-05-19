-- SKELETON — Wave 0 stub (per ADR-024)
-- Detailed DDL deferred to Milestone D / Wave 2 (third-party tool ecosystem)
-- Status: structural placeholder for cross-context references
--
-- Context: mcp (Model Context Protocol)
-- Intent: MCP server connections, tool registrations, health logs
-- Cross-context dependencies:
--   * multitenancy.workspaces (workspace_id is connection scope)
--   * multitenancy.cells (optional cell_id for per-cell connections)
--   * agents.agent_instances (consumers of MCP tools)
--   * rbac.* (per-tool permissions)

-- =============================================================================
-- mcp_connections — registered MCP server endpoints
-- =============================================================================
CREATE TABLE mcp_connections (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    workspace_id uuid        NOT NULL,
    -- TODO: columns в Milestone D / Wave 2
    --   cell_id uuid NULL — optional per-cell scope
    --   connection_name text — human-readable
    --   transport text — 'stdio' | 'http' | 'sse' | 'websocket'
    --   endpoint_url text — connection target
    --   auth_config_jsonb — credentials (encrypted at rest)
    --   status text — 'active' | 'disabled' | 'error'
    --   last_health_check_at timestamptz
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
    -- TODO: FOREIGN KEY (workspace_id) REFERENCES multitenancy.workspaces(id)
);

-- =============================================================================
-- mcp_tools — tools exposed by each MCP connection
-- =============================================================================
CREATE TABLE mcp_tools (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    workspace_id uuid        NOT NULL,
    -- TODO: columns в Milestone D / Wave 2
    --   connection_id uuid FK -> mcp_connections.id
    --   tool_name text — MCP-advertised tool identifier
    --   input_schema_jsonb — JSON Schema from MCP discovery
    --   description text
    --   is_enabled boolean
    --   permission_scope text — RBAC tag (per ADR-024 rbac context)
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- =============================================================================
-- mcp_health_log — append-only health probe results
-- =============================================================================
CREATE TABLE mcp_health_log (
    id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    workspace_id uuid        NOT NULL,
    -- TODO: columns в Milestone D / Wave 2
    --   connection_id uuid FK -> mcp_connections.id
    --   probed_at timestamptz
    --   status text — 'healthy' | 'degraded' | 'unreachable'
    --   latency_ms int
    --   error_message text NULL
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- TODO (Milestone D / Wave 2):
--   * indexes on (workspace_id, connection_id), (probed_at) for time-series
--   * partitioning of mcp_health_log by month (append-heavy)
--   * RLS policies tied to multitenancy
