# ADR-024: Bounded-context contracts — 10 контекстов в `contracts/` + CloudEvents 1.0 + naming corrections

- **Status:** Accepted (amendments 2026-05-19: «Naming bridge: organization → workspace» + «Sanctioned cross-context exceptions»)

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
backend/alembic/versions/
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
- **Migration ownership:** каждый `alembic/versions/<context>/` — domain-specific. При extract-to-microservice (Wave 5+) контекст переезжает целиком.

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
  cross-phase pre-Phase-05 architecture audit. This amendment makes it
  explicit so future agents don't re-litigate the same trade-off.
- **Wave-1 follow-up candidates** (when extracting llm_gateway to a
  microservice or splitting billing/credits into a separate context):
  1. Move `CreditTransaction` write into `llm_gateway.repositories.cost_ledger`
     as a private symbol; `billing` reads from the same row but doesn't own
     the write path
  2. Adopt an outbox pattern with a "credit_consumption_requested" event
     + idempotent processor in billing
  3. Distributed transaction via 2PC (only if/when the contexts physically
     split across services)

### Adding new sanctioned exceptions

Any new cross-context model import must:
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
