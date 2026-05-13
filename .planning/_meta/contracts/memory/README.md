<!-- SKELETON — Wave 1 deliverable (per ADR-024). Draft quality README; SQL/YAML files are placeholders. -->

# Bounded Context: `memory`

> **Status:** SKELETON (Wave 1 deliverable per ADR-024). Real DDL/API/events land in Milestone D, Wave 1 phase.

## Purpose

The `memory` context owns **persistent long-term memory** for AI-driven workflows.
It is the foundation for cross-session continuity, pattern recall, decision history,
and golden-dataset-driven agent improvement.

Two memory scopes coexist:

- **Cell memory** — facts and context bound to a single workspace (`cell_id`).
  Use cases: project background, user preferences, prior task outputs as context.
- **Role memory** — patterns bound to an `agent_archetype_id` and shared across all
  cells/organizations where that archetype runs. Use cases: success patterns,
  failure modes, distilled best practices for that role.

Underneath, semantic recall is powered by **AgentDB MCP** with HNSW vector search
on **ONNX all-MiniLM-L6-v2 (384-dim)** embeddings (per ADR-023 §6-7).

## Ubiquitous Language

| Term                  | Meaning                                                                                       |
|-----------------------|-----------------------------------------------------------------------------------------------|
| **Cell memory**       | Workspace-scoped fact / context entry. Lives inside one `cell_id`.                            |
| **Role memory**       | Global pattern bound to `agent_archetype_id` (per P-AUDIT-2 naming).                          |
| **Namespace**         | Partition string within a memory scope (e.g. `decisions`, `preferences`, `patterns/success`). |
| **Key**               | Stable identifier within a `(scope, namespace)` pair. `(scope, namespace, key)` is unique.    |
| **Embedding**         | 384-dim ONNX vector (`all-MiniLM-L6-v2`) attached to each entry for semantic search.          |
| **TTL**               | Optional `ttl_seconds`; entries beyond TTL are pruned by an expiry sweeper.                   |
| **Distilled memory**  | An entry derived from analyzing many trajectories (e.g. ReasoningBank consolidation pass).    |

## Invariants (placeholder — TODO in Milestone D, Wave 1)

- TODO: `(cell_id, namespace, key)` is unique in `cell_memory`.
- TODO: `(agent_archetype_id, namespace, key)` is unique in `role_memory`.
- TODO: **always** use `agent_archetype_id` — never the deprecated `ui_sprite_archetype` naming.
- TODO: FK target in `role_memory` is `agents.agent_archetypes` — never `roles_agent`.
- TODO: every entry with a non-NULL `embedding` has matching `embedding_index_metadata` (model + dim + metric).
- TODO: cell memory is fully isolated by `multitenancy.cells` RLS; cross-cell read goes through explicit RBAC.
- TODO: role memory is read-mostly; writes are gated by archetype-owner permission.

## Cross-Context Dependencies

- **multitenancy** — `cell_id` scopes `cell_memory`; transitively `organization_id` for isolation.
- **agents** — `agent_archetype_id` (FK target: `agents.agent_archetypes`) scopes `role_memory`.
- **AgentDB MCP** (runtime) — actual HNSW vector index and search execution
  (per **ADR-023 §6-7**: ONNX 384-dim embeddings, HNSW index).
- **tasks** — task executions are the primary source of new memory entries
  (success/failure trajectories → distilled patterns into `role_memory`).
- **rbac** — gates read/write to memory entries; particularly important for `role_memory`
  since archetypes are typically organization-spanning.

## Why Wave 1 (not Wave 0)

Agent memory is **not required for Wave 0**:

1. Wave 0 task volume is small; in-context recall is sufficient.
2. ReasoningBank-style distillation pipelines need a population of trajectories first.
3. AgentDB MCP integration as runtime store needs hardening for production use.

Memory becomes **critical** when:

- Multiple agents hand off work and need shared context across sessions.
- Cross-session continuity (resume work where left off) is a UX requirement.
- Vertical knowledge persistence (per **R-29** in risk register) requires
  durable, queryable patterns.

## ADR References

- **ADR-024** — Bounded Context Contracts (this context schema, §1).
- **ADR-023 §6-7** — Runtime AgentDB choice, ONNX 384-dim embeddings, HNSW index.
- **R-29** (in risk register) — vertical knowledge persistence.

## Naming Compliance Note (per P-AUDIT-2)

This context is the **canonical reference site** for the agent-archetype naming convention:

- Column: `agent_archetype_id` — **never** `ui_sprite_archetype`, `ui_sprite_id`, etc.
- FK target: `agents.agent_archetypes` — **never** `roles_agent` or any legacy synonym.

Downstream contexts referencing role-scoped memory must use these identifiers verbatim.

## Open Questions (defer to Milestone D, Wave 1)

- Memory distillation cadence (per-task? batch nightly? on idle?).
- TTL defaults per namespace (some namespaces should never expire).
- Conflict resolution when two trajectories produce contradictory patterns.
- Privacy: should `cell_memory` ever be readable by archetype maintainers for tuning?
- Index rebuild policy when embedding model version changes.
- ReasoningBank-style EWC++ importance weighting integration.
