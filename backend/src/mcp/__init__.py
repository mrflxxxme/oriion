"""MCP (Model Context Protocol) bounded context.

Wave 0 scope per Phase 00.4 § Tasks 14-15:
    * **Framework only**: `MCPClient` wrapper + `MCPConnection` persistence.
      No production MCP servers ship in Wave 0 (AC8) — a real Pydantic-AI /
      mcp-sdk integration lands in Wave 1+.
    * **Built-in tools** (`read_url`, `web_search`): not MCP servers,
      first-party utilities that share the rate-limit + exception surface
      MCP tools will use.

Bounded-context contract: contracts/mcp/schema.sql (SKELETON status — full
DDL deferred Milestone D / Wave 2 per ADR-024). The Wave 0 minimal table
``mcp.mcp_connections`` is owned by this module's migration:
``backend/migrations/versions/mcp/0001_mcp_connections.py``.

Cross-context dependencies:
    * multitenancy — connections scoped by ``workspace_id`` (+ optional cell_id).
    * agents (Wave 1+) — consumers of MCP tools at execution time.
    * rbac (Wave 1+) — per-tool permission scopes.

ADR references:
    * ADR-013 (mcp-protocol) — framework intent.
    * ADR-024 (bounded-context-contracts) — schema authority.
"""
