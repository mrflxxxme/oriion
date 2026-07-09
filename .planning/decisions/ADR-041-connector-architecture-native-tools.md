# ADR-041 — Connector architecture: native-tool callables (Wave-1), MCP-protocol deferred

- **Status:** Accepted (2026-07-09, `/autonomy:run` phase 01.9b)
- **Context refs:** ADR-013 (MCP + BYOK KMS), ADR-039 (security guardrails), ADR-040 D10 (DLP-before-connectors), grill 2026-07-03 (DECISIONS-LOG `01.9`: connectors are read+draft only)

## Context
Phase 01.9 delivers three first-party connectors (Telegram Bot-API, Yandex Disk, IMAP/SMTP), **read + draft only** (founder grill 2026-07-03: agent reads context + prepares a draft artifact; autonomous outward SEND is deny-until-approval-UI 01.12). The seed-spec says "доступны агентам через существующий MCP-клиент (00.4)". But discovery (2026-07-09) found the **00.4 MCP client is a Wave-0 stub**: `MCPClient.connect()` returns an empty session, "no real MCP protocol traffic happens Wave 0". Real tools reach pydantic-ai agents today as **native `Agent(tools=[...])` callables** — the `WebSearchTool` / `ReadURLTool` pattern (`backend/src/mcp/tools/`, wired via `runtime/web_search_runner.py` → `dispatch.py:build_leaf_runner`).

## Decision
Wave-1 connectors are **native-tool callables**, not MCP-protocol servers:
- Each connector is a client class mirroring `WebSearchTool`/`ReadURLTool` (async methods, rate-limited, typed `MCPError` subclasses, degrade gracefully) under `backend/src/mcp/tools/connectors/`.
- Exposed to agents as `NativeTool` closures via `Agent(tools=[...])`, gated by the capability classifier (`security/capability.py requires_approval()`) + screened by the 01.6 DLP seam on each call.
- Credentials stored **KMS-encrypted at rest**, mirroring BYOK (`llm_gateway/services/kms_provider.py` + `byok_service.py`): a new `mcp.connector_credentials` table (workspace-scoped RLS) + a `connector_credential_service`.
- Registry via the existing `mcp.mcp_connections` table / `MCPConnectionService`.
- **Real MCP-protocol transport (JSON-RPC stdio/http, `tools/list`/`tools/call`) is DEFERRED to Wave-2**, where community + vertical connectors land (01.9 seed out-of-scope). The `MCPClient` stub + `mcp_connections` registry remain the seam for that upgrade.

## Alternatives considered
**A) Build the full MCP-protocol client + run 3 MCP servers now.** *Rejected.* The 00.4 client is a stub — this means building the entire protocol layer (handshake, tool discovery, transport) plus operating three server processes on a single-box VPS pilot. Disproportionate cost/complexity for the Wave-1 value (read+draft), which native tools deliver identically. MCP-protocol infra is a Wave-2 concern (external/community connectors that genuinely need the protocol boundary). Higher blast radius, more moving parts, more attack surface.

**B) Native-tool callables (chosen).**

## Rubric (judge-panel skipped — winner unambiguous, ADR records the weighing)
| Dimension | A (MCP-protocol) | B (native-tool) |
|---|---|---|
| Correctness (delivers read+draft) | ✓ | ✓ (tie) |
| Security (DLP + capability wrap) | ✓ | ✓ (tie) |
| Simplicity | ✗ whole protocol layer + 3 processes | ✓ reuses proven tool pattern |
| Cost (dev + runtime) | ✗ high | ✓ low |
Correctness + security are gates (tie); B wins decisively on simplicity + cost. A judge-panel of N cold approaches would not change this, so it was decided by architect reasoning + this ADR (money discipline, ADR-040 D11) — the founder can veto.

## Consequences
- Wave-2 builds the real MCP-protocol transport when community/vertical connectors arrive; the registry + `MCPClient` stub are the forward seam.
- Wave-1 connectors are internal tool closures, not externally-addressable MCP servers.
- The capability gate (`requires_approval`) gets its first real enforcement call-site here (01.6 substrate activation); `agent_archetypes.tools_allowed` gets its first runtime enforcement.
