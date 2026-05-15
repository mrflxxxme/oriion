# ADR-024: Bounded-context contracts — 10 контекстов в `contracts/` + CloudEvents 1.0 + naming corrections

- **Status:** Accepted

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

## Links

- [ADR-028 policies registry](./ADR-028-policies-registry.md) — DECISION-7
- [ADR-001](./ADR-001-modular-monolith.md) — repository structure (revised: ссылка на `contracts/`)
- [ADR-009](./ADR-009-multitenancy-3-levels.md) — multitenancy (use `contracts/multitenancy/`)
- [ADR-021](./ADR-021-ai-generated-pixel-pipeline.md) — `agent_archetype_id` FK (revised: ссылка сюда)
- [ADR-010](./ADR-010-role-versioning.md) — prompt-versioning vs archetype-versioning split (revised: scope clarification)
- CloudEvents 1.0 spec: https://github.com/cloudevents/spec
