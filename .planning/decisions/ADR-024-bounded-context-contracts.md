# ADR-024: Bounded-context contracts — 10 контекстов в `contracts/` + CloudEvents 1.0 + naming corrections

- **Status:** Accepted (amendments 2026-05-19: «Naming bridge: organization → workspace» + «Sanctioned cross-context exceptions»; re-confirmed 2026-05-21 by Phase 00.5b audit; amended 2026-05-26 by Phase 00.6 PR-B audit (F-ARC-1) — Exception #2 records a new file `runtime/dispatch.py` on the existing `runtime → tasks` edge; no new edge introduced)

## Naming bridge: organization → workspace (2026-05-19)

> Adopted in pre-Phase-00.3 contract extension. Resolves the mismatch between
> the `multitenancy.organizations` DDL (pre-rename) and the `workspace_id`
> public API surface that the architect-PR introduced.

| Layer | Before (deprecated) | After (canonical) |
|---|---|---|
| `multitenancy` table | `multitenancy.organizations` | `multitenancy.workspaces` |
| `multitenancy.cells.*` FK | `organization_id` | `workspace_id` |
| `llm_gateway.byok_keys.*` FK | `organization_id` | `workspace_id` |
| `llm_gateway.llm_usage_log.*` FK | `organization_id` | `workspace_id` |
| `rbac.role_assignments.scope_type` enum | `'organization'` | `'workspace'` |
| RLS Postgres GUC | `app.current_organization_id` | `app.current_workspace_id` |
| API path | `/organizations/...` | `/workspaces/...` |
| CloudEvent type | `oriion.multitenancy.organization.*` | `oriion.multitenancy.workspace.*` |
| Pydantic class | `Organization` | `Workspace` |

Implementers MUST use the canonical names in new code. Legacy term appears only
in archived `_session-context/*.md` files (immutable historical record).



## Decision

Покрывает [ADR-028 policies registry](./ADR-028-policies-registry.md) DECISION-7. Фиксирует структуру контрактов через bounded-context split. Phase-spec'ы перестают дублировать DDL/API — они ссылаются на authoritative spec в `contracts/<context>/`.

### 1. Folder layout — 10 bounded contexts

```
.planning/contracts/
├── README.md             # entry-point + bounded-context map
├── iam/                  # users, sessions, refresh_tokens, oauth_links
│   ├── schema.sql        # DDL (CREATE TABLE + индексы + RLS)
│   ├── api.yaml          # OpenAPI 3.1
│   ├── events.yaml       # CloudEvents 1.0 spec
│   └── README.md         # invariants + ubiquitous language + ADR/phase refs
├── multitenancy/         # organizations, cells, cell_members, RLS policies
├── rbac/                 # system_roles, permissions, role_assignments
├── billing/              # credit_balances, credit_transactions, pricing_table, tariff_plans
├── llm-gateway/          # byok_keys, llm_provider_config, llm_usage_log
├── mcp/                  # mcp_connections, mcp_tools, mcp_health_log
├── agents/               # agent_archetypes, team_presets, agent_instances
├── tasks/                # tasks, task_steps, task_artifacts
├── artifacts/            # yjs_documents, s3_assets (Wave 1)
└── memory/               # cell_memory, role_memory, embeddings (Wave 1)
```

Wave 0 deliverables full: `iam`, `multitenancy`, `rbac`, `llm-gateway`, `agents`, `tasks`. Wave 0 stubs (со скелетом README + minimal schema): `billing`, `mcp`. Wave 1 deliverables: `artifacts`, `memory`. Конкретное наполнение — Milestone B.

### 2. Naming corrections

| Старый термин (deprecated) | Канонический термин | Используется в |
|---|---|---|
| `roles_rbac` | `system_roles` | `contracts/rbac/schema.sql` |
| `roles_agent` | `agent_archetypes` | `contracts/agents/schema.sql` |
| `sprite-ID`, `ui_sprite_archetype` (Phase 00.5 stale terms) | `agent_archetype_id` (FK к `agent_archetypes`) | sprite-таблица в ADR-021 |

Старые термины удаляются из новой документации. Существующие phase-spec'ы обновляются в Milestone C.

### 3. Events format — CloudEvents 1.0

Все domain events используют [CloudEvents 1.0 spec](https://github.com/cloudevents/spec). Причины:
- Python SDK (`cloudevents`) — production-ready.
- Future-proof для миграции на NATS / Kafka в Wave 4 (текущий transport — in-process EventBus + Redis streams).
- Совместимо с `handoff-schema.json` в `.claude/agents/_shared/` (см. ADR-023) — внутри-agent коммуникация и domain events используют один envelope.

Каждый `contracts/<context>/events.yaml` описывает emitted/consumed events для своего bounded context.

### 4. Alembic migrations layout

```
backend/migrations/versions/
├── iam/
│   ├── 0001_users.py
│   └── 0002_refresh_tokens.py
├── multitenancy/
│   └── 0001_cells.py
├── rbac/
└── ...
```

Один Alembic env с несколькими migration directories per bounded context (multi-version approach). Phase-spec задаёт DDL в `contracts/<context>/schema.sql`, backend-implementer переносит в Alembic migration в соответствующем под-каталоге.

### 5. Phase-files referencing rule

Phase-spec'ы **импортируют** нужные contexts через cross-link:

```markdown
## Dependencies
- Contracts: [iam](../contracts/iam/), [multitenancy](../contracts/multitenancy/)
- ADRs: ADR-007, ADR-009
```

Phase-spec **не дублирует** DDL/OpenAPI. Если phase добавляет новые таблицы — они идут в `contracts/<context>/schema.sql` (с pull request review), а phase-spec лишь упоминает имена endpoint'ов и rows-added.

## Consequences

- **Authoritative source:** `contracts/` — единственное место, где живёт DB schema, API spec, events. Backend код (`backend/src/<context>/`) — implementation layer, должен conform контракту.
- **Изоляция на уровне файлов:** изменение one bounded context не зацепляет другие через diff-noise. Reviewer-backend ловит cross-context coupling.
- **Naming drift устранён:** `agent_archetypes` / `agent_archetype_id` / `system_roles` фиксируются раз и навсегда. ADR-001 (revised), ADR-021 (revised), ADR-010 (revised) cross-ref сюда.
- **Bounded-context coupling explicit:** если backend service A читает таблицу из context B — это видно в `contracts/<A>/README.md` секции «External dependencies». RBAC и cross-cutting concerns не размазываются.
- **Migration ownership:** каждый `migrations/versions/<context>/` — domain-specific. При extract-to-microservice (Wave 5+) контекст переезжает целиком.

## Sanctioned cross-context exceptions (amendment 2026-05-19)

The strict "no cross-context model imports" rule has **one explicit, narrow
exception** discovered during Phase 00.4 implementation and ratified by the
PR #30 architecture audit:

### Exception #1 — `llm_gateway → billing.models.CreditTransaction`

- **Importing file:** `backend/src/llm_gateway/services/billing_service.py:26`
- **Imported symbol:** `from src.billing.models import CreditTransaction`
- **Justification:** llm-gateway invariant #7 (per
  `contracts/llm-gateway/README.md:59`) requires **atomic 3-currency write**
  across `llm_gateway.llm_usage_log` (cost_usd + cost_rub + fx_rate) **and**
  `billing.credit_transactions` (amount_rub + amount_credits +
  balance_after_credits) in a single transaction. Splitting the write via
  an outbox / port boundary would either lose atomicity (eventual
  consistency on the cost ledger — unacceptable for prod billing) or
  require a distributed transaction (out of Wave 0 scope).
- **Audit history:** flagged as architecture H1 by the PR #30 audit;
  re-confirmed as sanctioned by the PR #32 architecture audit + the
  cross-phase pre-Phase-05 architecture audit + the Phase 00.5b 5-agent
  audit (2026-05-21, AUDIT-2026-05-20-PHASE-00-5/section-04). Phase 00.5b
  Commit 2 router wiring re-touched the import surface (lifespan
  provider DI + llm_gateway/deps.py) without introducing any new
  cross-context model imports — verified via
  `git grep "^from src\.[a-z_]+\.models" backend/src/` returning only
  the pre-sanctioned line at `llm_gateway/services/billing_service.py:26`.
  This amendment makes it explicit so future agents don't re-litigate
  the same trade-off.
- **Wave-1 follow-up candidates** (when extracting llm_gateway to a
  microservice or splitting billing/credits into a separate context):
  1. Move `CreditTransaction` write into `llm_gateway.repositories.cost_ledger`
     as a private symbol; `billing` reads from the same row but doesn't own
     the write path
  2. Adopt an outbox pattern with a "credit_consumption_requested" event
     + idempotent processor in billing
  3. Distributed transaction via 2PC (only if/when the contexts physically
     split across services)

### Exception #2 — `runtime → tasks.{models.Task, events, exceptions}` (2026-05-21)

- **Importing files:**
  - `backend/src/runtime/orchestrator.py`: `from src.tasks.models import Task`
  - `backend/src/runtime/orchestrator.py`: `from src.tasks import events as tasks_events`
  - `backend/src/runtime/orchestrator.py`: `from src.tasks.exceptions import BudgetExceeded` (via budget_guard)
  - `backend/src/runtime/dispatch.py`: `from src.tasks.models import Task` (Phase 00.6 PR-B — inline-dispatch leaf-runner creates child `Task` rows; same blessed edge as orchestrator.py, no new justification needed — recorded per the §3 file:line rule, F-ARC-1)
  - `backend/src/runtime/queue/actor.py`: `from src.tasks.models import Task` (Phase 01.1 infra-PR / ADR-034 — Dramatiq worker loads the Task; same blessed runtime→tasks edge, no new justification)
- **Reverse edge (sanctioned-by-default, recorded for transparency):**
  `tasks/routers/tasks.py` → `runtime.dispatch` + `runtime.sse_publisher`
  (function/factory imports, not model imports) — the `/tasks/{id}/run`
  endpoint invokes the execution layer. Mirrors the pre-existing
  `tasks/routers/stream.py` → `runtime.sse_publisher` import; no new exception
  required (service/function-call edges are sanctioned-by-default per §3).
- **Justification:** the `runtime` bounded context is by design the
  **execution layer** for `tasks`. Per Phase 00.5 phase-spec the runtime
  drives the Task state machine (queued → running → succeeded/failed/
  cancelled) and persists per-step rows. The two contexts have separate
  surfaces (tasks owns "what to record", runtime owns "how it runs") but
  share a single physical schema. Pure event-driven decoupling would
  require an outbox + idempotent processor for every state transition —
  out of Wave-0 scope.
- **Audit history:** flagged + re-approved by the Phase 00.5b 5-agent
  audit (F-ARC-H1 in
  `_session-context/AUDIT-2026-05-20-PHASE-00-5/section-04-architecture.md`).
- **Wave-1 follow-up candidates:**
  1. Move `Task` mutations behind a `TaskRepository` port in
     `src/tasks/repositories/`; runtime depends on the port, not the
     model directly
  2. Adopt an outbox pattern with `task.state_changed` events for state
     transitions
  3. Promote `runtime` to a sibling top-level bounded context with its
     own `contracts/runtime/` if it grows beyond the orchestrator
     (currently ~250 LoC across 5 files)

### Exception #3 — `runtime → mcp.tools.web_search` (2026-06-07)

- **Importing files:**
  - `backend/src/runtime/dispatch.py`: `from src.mcp.tools.web_search import WebSearchTool`
  - `backend/src/runtime/dispatch.py`: `from src.mcp.exceptions import MCPError`
- **Justification:** Phase 00.6 PR-B (founder decision 2026-06-07) feeds the
  Researcher leaf REAL market data via a scripted `web_search` pre-fetch (the
  LLM tool-call path is AC14/AC-W1-16). `web_search` is a first-party **built-in
  tool utility** (not an MCP server), function-level import — analogous to the
  sanctioned-by-default service/factory edges (`iam → agents`,
  `agents → llm_gateway`). No model/schema import; no DB coupling.
- **Wave-1 follow-up:** when the real LLM-driven Coordinator + tool-call path
  lands (AC-W1-16), the Researcher Agent calls `web_search` as a Pydantic-AI
  tool through the gateway, and this direct `runtime → mcp.tools` edge is
  replaced by the tool-registry seam.

### Service-call edges (sanctioned by default — NOT model imports)

The following cross-context dependencies are **service-class imports**,
not model imports, so they fall outside the strict "no cross-context
model imports" rule. Listed here for transparency only; no amendment is
required to add them:

| Importing file | Imported class | Purpose |
|---|---|---|
| `backend/src/iam/services/auth_service.py` | `agents.services.TeamProvisioningService` | AC1 — auto-spawn productivity-core team at register |
| `backend/src/iam/deps.py` | `agents.services.TeamProvisioningService` | DI wiring for `AuthService` |
| `backend/src/agents/{coordinator,researcher,writer,analyst}.py` | `llm_gateway.pydantic_ai_model.LLMGatewayModel` | Pydantic-AI Model adapter (T3) |

These edges are DAG (no cycles — verified by Phase 00.5b Backend
Architect audit).

### Adding new sanctioned exceptions

Any new cross-context **model** import must:
1. Be approved by an audit (PR-scoped or cross-phase) with explicit
   architectural justification
2. Be added to this amendment list with importing-file:line + Wave-1
   refactor candidates
3. Have the corresponding `contracts/<importing-context>/README.md`
   updated to mention the dependency in its "External dependencies" section

The default remains **no cross-context model imports**. The exception list is
narrow on purpose.

## Links

- [ADR-028 policies registry](./ADR-028-policies-registry.md) — DECISION-7
- [ADR-001](./ADR-001-modular-monolith.md) — repository structure (revised: ссылка на `contracts/`)
- [ADR-009](./ADR-009-multitenancy-3-levels.md) — multitenancy (use `contracts/multitenancy/`)
- [ADR-021](./ADR-021-ai-generated-pixel-pipeline.md) — `agent_archetype_id` FK (revised: ссылка сюда)
- [ADR-010](./ADR-010-role-versioning.md) — prompt-versioning vs archetype-versioning split (revised: scope clarification)
- CloudEvents 1.0 spec: https://github.com/cloudevents/spec
