---
title: "Oriion Tool Registry — Single Source of Truth"
version: 0.1.0
status: living-document
last-updated: 2026-05-13
last-updated-context: "Session 3 audit, Milestone B.5"
owners: [architect, reviewer-backend]
---

# Oriion Tool Registry — Single Source of Truth

## Purpose

Любой `.claude/agents/<role>/tools-allowlist.md` ИЛИ `_meta/verticals/<slug>/prompts/<role>.md`
`tools_allowed:` frontmatter field MUST reference только slugs из этого registry.

**Reviewer-backend** проверяет conformance перед approval любого PR содержащего role-prompt
изменения или новые vertical prompts.

Resolves: Session 3 audit C2 (coordinator.md `tools_allowed` не соответствовали API operationIds).
Enforces: P-AUDIT-2 (naming compliance).

---

## 1. AgentDB MCP tools

Через claude-flow MCP server per ADR-023 §6-7. Slugs map к реальным MCP tool names — runtime
hooks-route layer переводит slug→tool на момент invocation.

| Slug | MCP tool name | Purpose | Used by roles |
|---|---|---|---|
| `memory.cells_search` | `mcp__claude-flow__memory_search` (namespace=`cell-memory:<id>`) | Semantic search в cell memory namespace | wb-coordinator, wb-researcher, wb-listing-writer |
| `memory.cells_upsert` | `mcp__claude-flow__memory_store` (namespace=`cell-memory:<id>`) | Store entry в cell memory | wb-coordinator |
| `memory.cells_delete` | `mcp__claude-flow__memory_delete` (namespace=`cell-memory:<id>`) | Delete entry from cell memory (PII purge, user request) | wb-coordinator, memory-curator |
| `memory.roles_search` | `mcp__claude-flow__memory_search` (namespace=`role-memory:<slug>`) | Semantic search в role-memory namespace | all 11 system roles |
| `memory.roles_upsert` | `mcp__claude-flow__memory_store` (namespace=`role-memory:<slug>`) | Store pattern в role-memory | architect, planner, reviewer-frontend, reviewer-backend, reviewer-security, evaluator |
| `memory.adr_search` | `mcp__claude-flow__memory_search` (namespace=`adr-patterns`) | Search ADR knowledge base | architect, planner, reviewer-* |
| `memory.adr_upsert` | `mcp__claude-flow__memory_store` (namespace=`adr-patterns`) | Index new/updated ADR | memory-curator |
| `swarm.spawn_agent` | `mcp__claude-flow__agent_spawn` | Spawn subordinate agent (non-persistent) | planner, architect |
| `swarm.list_agents` | `mcp__claude-flow__agent_list` | List active agent instances | memory-curator (audit) |
| `swarm.agent_status` | `mcp__claude-flow__agent_status` | Inspect agent state (stagnation check) | memory-curator |
| `hooks.task_route` | `mcp__claude-flow__hooks_route` | Smart task routing | planner |
| `hooks.post_task` | `mcp__claude-flow__hooks_post-task` | Emit checkpoint event after task | implementers, reviewers, verifier |

---

## 2. REST API contract operations

Mapped из `.planning/_meta/contracts/<context>/api.yaml` operationIds. Каждый slug —
canonical name для cross-context referencing. Backend implementations expose эти endpoints
per OpenAPI spec.

### 2.1 Tasks context (`_meta/contracts/tasks/api.yaml`)

| Slug | REST endpoint | operationId | Used by |
|---|---|---|---|
| `tasks.create` | `POST /cells/{cell_id}/tasks` | `createTask` | wb-coordinator |
| `tasks.get` | `GET /tasks/{task_id}` | `getTask` | wb-coordinator, verifier |
| `tasks.list` | `GET /cells/{cell_id}/tasks` | `listTasks` | wb-coordinator |
| `tasks.cancel` | `POST /tasks/{task_id}/cancel` | `cancelTask` | wb-coordinator (escalation), verifier |
| `tasks.step_respond` | `POST /tasks/{task_id}/steps/{step_id}/respond` | `respondToStep` | wb-coordinator (user-input handling) |
| `tasks.step_get` | `GET /tasks/{task_id}/steps/{step_id}` | `getStep` | wb-coordinator |

### 2.2 LLM-gateway context (`_meta/contracts/llm-gateway/api.yaml`)

| Slug | REST endpoint | operationId | Used by |
|---|---|---|---|
| `llm.chat_completions` | `POST /llm/chat/completions` | `createChatCompletion` | all implementer + vertical roles |
| `llm.embeddings` | `POST /llm/embeddings` | `createEmbedding` | wb-researcher, memory-curator |
| `llm.usage_get` | `GET /llm/usage` | `getUsage` | memory-curator (cost telemetry) |

### 2.3 IAM context (`_meta/contracts/iam/api.yaml`)

| Slug | REST endpoint | operationId | Used by |
|---|---|---|---|
| `iam.session_revoke` | `DELETE /auth/sessions/{session_id}` | `revokeSession` | reviewer-security (incident response) |
| `iam.session_list` | `GET /auth/sessions` | `listSessions` | reviewer-security (audit) |
| `iam.user_get` | `GET /users/{user_id}` | `getUser` | wb-coordinator (read-only profile) |

### 2.4 Multitenancy context (`_meta/contracts/multitenancy/api.yaml`)

| Slug | REST endpoint | operationId | Used by |
|---|---|---|---|
| `multitenancy.cell_get` | `GET /cells/{cell_id}` | `getCell` | wb-coordinator, all vertical roles |
| `multitenancy.cell_list` | `GET /organizations/{org_id}/cells` | `listCells` | wb-coordinator |
| `multitenancy.org_get` | `GET /organizations/{org_id}` | `getOrganization` | wb-coordinator |

### 2.5 Agents context (`_meta/contracts/agents/api.yaml`)

| Slug | REST endpoint | operationId | Used by |
|---|---|---|---|
| `agents.archetype_list` | `GET /agent-archetypes` | `listArchetypes` | wb-coordinator (team setup) |
| `agents.archetype_get` | `GET /agent-archetypes/{archetype_slug}` | `getArchetype` | wb-coordinator |
| `agents.instance_create` | `POST /cells/{cell_id}/agent-instances` | `createAgentInstance` | wb-coordinator (apply preset) |
| `agents.instance_list` | `GET /cells/{cell_id}/agent-instances` | `listAgentInstances` | wb-coordinator |
| `agents.instance_update` | `PATCH /cells/{cell_id}/agent-instances/{instance_id}` | `updateAgentInstance` | wb-coordinator |

---

## 3. Built-in Claude Code tools

Доступны всем agents без extra registration. Per-role restrictions enforced через
`tools-allowlist.md`.

| Slug | Purpose | Restrictions |
|---|---|---|
| `Read` | File read | any path within workspace |
| `Write` | File create | excluding `_meta/contracts/*` (architect-only escalation) and `.claude/agents/_shared/*` (architect/memory-curator-only) |
| `Edit` | File edit | per role tools-allowlist (which paths/extensions allowed) |
| `Glob` | File pattern search | universal |
| `Grep` | Content search | universal |
| `Bash` | Shell execution | per role allowlist; read-ops (ls, git status) vs write-ops (npm install, git commit) split |
| `Task` | Spawn subagent | architect / planner only (others escalate to planner) |
| `WebFetch` | External URL fetch | architect / researcher / planner (vertical-roles только domain-allowlist per vertical config) |
| `WebSearch` | Web search | architect / researcher / planner |
| `TodoWrite` | Local task list | universal (per-agent ephemeral) |
| `NotebookEdit` | Jupyter cell edit | data/analytics roles only |

---

## Naming conventions

- All slugs lowercase, dot-separated: `<namespace>.<verb>[_<noun>]`
- Namespaces:
  - **MCP**: `memory`, `swarm`, `hooks`
  - **REST contracts**: `tasks`, `llm`, `iam`, `multitenancy`, `rbac`, `agents`, `billing`, `mcp` (MCP-server-management context)
  - **Built-in tools**: original PascalCase (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `Task`, `WebFetch`, `WebSearch`, `TodoWrite`, `NotebookEdit`)
- Verbs: prefer canonical action words. Approved: `list`, `get`, `search`, `create`, `upsert`, `update`, `delete`, `cancel`, `revoke`, `respond`, `route`. Avoid synonyms (use `search` not `find`/`query`; use `delete` not `remove`/`destroy`).
- Versioning: tools_allowed entries reference slugs (unversioned). The REST contract version
  (semver) is governed по api.yaml `info.version` — agents bind к latest compatible major.

---

## Validation

- **Reviewer-backend** MUST grep all `tools_allowed:` references против этого registry перед PR approval.
- **CI check** (future Phase 00.1 deliverable): `scripts/validate-tools.py` parses all `.md` files с `tools_allowed:` frontmatter, asserts each entry exists в registry.
- **New tool addition**: vertical-prompt-author or implementer создаёт PR-update этого registry с:
  - Justification (why this slug needed)
  - Role-allowlist (who can call it)
  - Cross-link к contract operationId OR MCP tool doc

---

## Cross-refs

- `_meta/contracts/*/api.yaml` — REST operationIds (mapped в category 2)
- `.claude/agents/*/tools-allowlist.md` — per-role granted slugs
- `_meta/verticals/<slug>/prompts/*.md` `tools_allowed:` frontmatter — must reference registry slugs
- `.claude/agents/_shared/handoff-schema.json` — CloudEvent schemas emitted by these tools (где applicable)

---

## References

- **ADR-023** §6-7 — AgentDB MCP runtime (defines `mcp__claude-flow__*` namespace)
- **ADR-024** — Contracts naming convention (defines REST operationId style)
- **Session 3 audit** — finding C2 (tools_allowed misalignment)
- **P-AUDIT-2** — naming compliance enforcement (this registry = single source-of-truth)

---

## Changelog

- **0.1.0** (2026-05-13) — Initial registry, Milestone B.5 audit fix. Covers MCP + 5 REST contexts + built-ins. Bootstrap entries ~35 slugs.
