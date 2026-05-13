# Checklist — Alembic migration

Прогоняется перед каждым commit при Workflow 2 (new/updated migration). All items checked
or explicit N/A с rationale.

## Spec conformance

- [ ] `_meta/contracts/<context>/schema.sql` прочитан полностью для целевой таблицы
- [ ] Migration columns ↔ schema.sql 1:1: имена, типы, nullability, defaults, server_default
- [ ] Indices ↔ schema.sql 1:1 (CREATE INDEX statements)
- [ ] Constraints ↔ schema.sql: UNIQUE, CHECK, FOREIGN KEY
- [ ] RLS policies ↔ schema.sql: ENABLE ROW LEVEL SECURITY + CREATE POLICY statements
- [ ] Никакая правка `_meta/contracts/<context>/schema.sql` НЕ сделана. Если есть divergence — escalation, не silent fix.

## Location & naming

- [ ] Migration в `backend/alembic/versions/<context>/` (per DECISION-7 / ADR-024 §4)
      НЕ в root `backend/alembic/versions/`
- [ ] Filename `NNNN_<descriptive-slug>.py` где NNNN — sequence в context folder
- [ ] Docstring header содержит: revision ID, revises (previous), create date, descriptive
      title

## Upgrade / downgrade pair

- [ ] `upgrade()` implemented
- [ ] `downgrade()` implemented (NOT `pass` или `raise`)
- [ ] `downgrade()` reverses everything `upgrade()` did, в reverse order
- [ ] RLS policies dropped в downgrade BEFORE table drop (иначе FK violation на pg_policies)
- [ ] Indices dropped в downgrade BEFORE table drop

## Backwards compatibility

- [ ] Migration backwards-compatible: deploy migration → старый код всё ещё работает → новый код deploys
  - Adding nullable column = OK
  - Adding column с default = OK
  - Renaming column = breaking (split: add new → backfill → cutover → drop old)
  - Dropping column = breaking (deprecate first)
- [ ] Если breaking — task explicitly marked `breaking: true` в PLAN.md, founder approved
- [ ] Если breaking — accompanying deprecation note в `_meta/contracts/<context>/README.md` через separate task

## Indices

- [ ] All FK columns have index (если cardinality > low)
- [ ] All columns used в WHERE clauses (per typical query patterns) — indexed
- [ ] UNIQUE constraints — `op.create_index(... unique=True)` или встроены в `create_table`
- [ ] Composite indices ordered по selectivity (most selective first)

## RLS (если multi-tenant table)

- [ ] `op.execute(text("ALTER TABLE <table> ENABLE ROW LEVEL SECURITY"))`
- [ ] CREATE POLICY statements использует `current_setting('app.current_tenant')::uuid`
- [ ] Policy covers SELECT, INSERT, UPDATE, DELETE (или explicit per-operation policies)
- [ ] FORCE ROW LEVEL SECURITY для tables где superusers shouldn't bypass (если applicable)

## Rollback tested

- [ ] `alembic upgrade head` → success
- [ ] `alembic downgrade -1` → success (no FK violations, no orphan policies)
- [ ] `alembic upgrade head` re-run → success (idempotent if needed OR clearly one-shot)
- [ ] Verified в test database, not production-like

## Tests

- [ ] `test_migrations.py::test_<table>_exists` — verifies upgrade creates table
- [ ] `test_migrations.py::test_<table>_columns_match_schema` — column-by-column check
- [ ] `test_migrations.py::test_<table>_rls_active` — query `pg_policies` to verify (если RLS table)
- [ ] `test_migrations.py::test_<table>_indices_exist` — query `pg_indexes`
- [ ] `test_migrations.py::test_<table>_downgrade_cleans` — downgrade leaves no leftover
- [ ] All tests pass

## Naming

- [ ] Canonical names: `agent_archetype_id`, `system_roles`, `agent_archetypes`
- [ ] No deprecated terms: `roles_rbac`, `roles_agent`, `sprite_id`, `ui_sprite_archetype`
- [ ] Snake_case columns
- [ ] FK columns named `<other_table>_id` (singular)

## Bounded context isolation

- [ ] Migration в правильном context subfolder
- [ ] Если table создаёт FK на другой context (e.g. `iam.users` FK from `billing.credit_balances`) — verified, что other context's table уже migrated (sequence dependency)
- [ ] Cross-context FK — escalate к architect если cross-cutting (может надо event-based вместо FK)

## Lint / type

- [ ] `ruff check backend/alembic/versions/<context>/` — clean
- [ ] No `Any`-typed imports
- [ ] Migration imports — only `alembic`, `sqlalchemy`, project's enums (no business logic imports)

## Commit

- [ ] Atomic — single migration в single commit (не batch миграций)
- [ ] Conventional Commits format: `feat(<context>): <description>` или `fix(<context>):` если fixes existing
- [ ] Commit message includes ADR-027 §4 fields
- [ ] No secrets в diff

## Memory

- [ ] Pattern stored в `agent-memory:backend-implementer` (migration pattern, RLS pattern если applicable)
- [ ] Task complete entry в `phase-state:<phase-id>`
- [ ] If pitfall encountered — stored в `agent-memory:backend-implementer` pitfall pattern для future

## CloudEvent emit

- [ ] `tech.oriion.code.commit.v1` payload prepared
- [ ] Validated against `_shared/handoff-schema.json`
- [ ] Emitted к `reviewer-backend` AND `reviewer-security` (parallel)
- [ ] Только ПОСЛЕ successful `git commit` (sha captured)
