# Bounded context: `tasks`

**Status:** DRAFT-READY (Milestone B.2, Wave 0)
**Owner:** backend-implementer + reviewer-backend
**ADR refs:** [ADR-024](../../decisions/ADR-024-bounded-context-contracts.md), [ADR-023](../../decisions/ADR-023-ai-team-runtime.md)
**GRILL refs:** DECISION-7

## Purpose

Runtime ledger of agent-team executions inside a cell.

- `tasks` — top-level execution unit (one agent-team run), with status lifecycle and aggregated cost/tokens.
- `task_steps` — ordered atomic operations (LLM call, tool use, user input wait, branch/merge); each carries a snapshot `agent_archetype_id` for historical accuracy.
- `task_artifacts` — outputs produced by a task/step; storage choice (inline / S3 / Yjs document) depends on size and type.

## Ubiquitous language

| Term | Meaning |
|---|---|
| **Task** | One agent-team execution inside a cell. **Not** a `.planning/` phase (the latter is a development-time concept). |
| **TaskStep** | One atomic operation inside a task — `llm_call`, `tool_use`, `user_input`, `wait`, `branch`, `merge`. |
| **TaskArtifact** | One produced output. `storage_kind ∈ {inline, s3, yjs_document}`. |
| **`agent_archetype_id`** | Canonical FK name (ADR-024 §2 / P-AUDIT-2). Snapshot on the step for forensic immutability. |

## Invariants

1. **Archetype snapshot.** `task_steps.agent_archetype_id` is captured at step creation and **never updated**. If the archetype later changes version or is deprecated, step records remain truthful about what actually ran.
2. **Cost reconciliation.** `tasks.total_cost_usd` is periodically reconciled to `SUM(task_steps.cost_usd) WHERE task_id = tasks.id`. Drift > 1¢ raises an internal alert. Cost columns are **technical accounting** — budget caps live in `.claude/agents/_shared/cost-budget.yaml` (**P-AUDIT-1**, mirrors `llm-gateway`).
3. **Status transitions are strict.** No skipping. Allowed transitions:
   - `queued → running → {waiting_input, succeeded, failed, timed_out}`
   - `running ↔ waiting_input` (resume via `/respond`)
   - `* → cancelled` (only from non-terminal states)
   - Terminal states (`succeeded`, `failed`, `cancelled`, `timed_out`) are immutable.
4. **Artifact size routing.** Artifacts > 1 MB **must** use `storage_kind ∈ {'s3', 'yjs_document'}` — never `'inline'`. Enforced by service layer; DDL CHECK ensures XOR of storage fields, but size routing is service-level.
5. **Immutable history on retry.** A failed task can be retried, but retry **creates a new task** (linked via `input_jsonb.retry_of` convention). The original task row is never mutated post-terminal — preserves audit trail.
6. **Cell isolation.** `tasks` is RLS-scoped by `cell_id`; `task_steps` and `task_artifacts` are scoped via their parent task.

## External dependencies (cross-context)

| Context | Reason |
|---|---|
| `multitenancy` | `cell_id` FK; RLS via `app.current_cell_id`. |
| `agents` | `agent_instance_id` and `agent_archetype_id` foreign keys; archetype snapshot for steps. |
| `iam` | `initiated_by_user_id` FK (cross-context, not DB-enforced). |
| `llm-gateway` | Consumes `request.completed.v1` to reconcile step costs; uses `llm_usage_log.task_id` for cost attribution. |
| `artifacts` (Wave 1) | `task_artifacts.yjs_document_id` references `yjs_documents` for collaborative artifacts. |
| `billing` | Consumes `kill_switch.engaged.v1` to cancel queued/running tasks system-wide. |

## Out of scope

- Workflow DAG engine internals (lives in `agents.team_presets.default_workflow_dag_json` + runtime orchestrator).
- Cost policy (lives in `cost-budget.yaml`).
- Artifact retention policy (lives in `artifacts` context, Wave 1).

## Files

- [`schema.sql`](./schema.sql) — PostgreSQL 16 DDL with RLS and CHECK constraints.
- [`api.yaml`](./api.yaml) — OpenAPI 3.1.
- [`events.yaml`](./events.yaml) — CloudEvents 1.0.
