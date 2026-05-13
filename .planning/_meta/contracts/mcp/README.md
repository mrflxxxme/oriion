<!-- SKELETON — Wave 0 stub (per ADR-024). Draft quality README; SQL/YAML files are placeholders. -->

# Bounded Context: `mcp`

> **Status:** SKELETON (Wave 0 stub per ADR-024). Real DDL/API/events deferred to Milestone D, Wave 2.

## Purpose

The `mcp` context owns **third-party tool integration** via the Model Context Protocol.
It tracks registered MCP server connections, the tools each server exposes, per-tool
permission scopes, and operational health.

This context is the bridge between Oriion's agent runtime and the external ecosystem
of MCP-compliant tool providers (databases, SaaS APIs, internal services, etc.).

## Ubiquitous Language (stub)

| Term             | Meaning                                                                          |
|------------------|----------------------------------------------------------------------------------|
| **Connection**   | A configured MCP server endpoint (URL/stdio binary + auth) for an organization.  |
| **Tool**         | A single capability advertised by a connection (e.g. `query_postgres`).          |
| **HealthStatus** | Time-stamped probe result: `healthy` / `degraded` / `unreachable`.               |
| **Permission**   | RBAC scope binding a tool to a role/cell — controls who/what may invoke it.      |
| **Transport**    | The wire protocol — `stdio`, `http`, `sse`, `websocket`.                         |

## Invariants (placeholder — TODO in Milestone D)

- TODO: every `mcp_tools` row belongs to exactly one active `mcp_connections` row.
- TODO: tool invocations require an explicit `rbac` permission match (no implicit allow).
- TODO: health log is append-only; current status derived from latest probe.
- TODO: connection credentials encrypted at rest (secrets management TBD).

## Cross-Context Dependencies

- **multitenancy** — connections scoped by `organization_id` (and optionally `cell_id`).
- **agents** — `agents.agent_instances` are the consumers of MCP tools at execution time.
- **rbac** — per-tool permission scopes evaluated on every invocation.
- **llm-gateway** — if a provider mediates tool routing via MCP, the gateway forwards through here.
- **billing** — `oriion.mcp.tool.invoked.v1` events contribute to consumption attribution (Wave 2+).

## Why SKELETON (not full Wave 0)

MCP integration is **out of scope for Wave 0 / Wave 1**:

1. Wave 0 internal demo uses **built-in tools only** (no third-party MCP servers).
2. The third-party MCP ecosystem is still maturing — protocol stability + security model.
3. Real implementation lands in **Wave 2**, once the core agent loop is proven and the
   ecosystem story is needed for adoption.

This skeleton reserves the schema namespace, documents intent, and gives cross-context
references (e.g. RBAC permission tags) a stable target ahead of time.

## ADR References

- **ADR-024** — Bounded Context Contracts (this context schema, §1).
- TODO: future ADR on MCP security model (credential storage, sandbox, network egress).
- TODO: future ADR on per-tool quota/throttling.

## Open Questions (defer to Milestone D)

- Per-cell vs per-organization connection scope — both? primary axis?
- How are MCP tool schemas versioned when the upstream server updates?
- Sandbox model for `stdio` transports (containerized? same host?).
- Cost attribution model for tool invocations (flat fee? pass-through provider cost?).
- Discovery cache TTL and refresh policy.
