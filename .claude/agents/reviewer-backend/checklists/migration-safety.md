# Checklist — Alembic migration safety

Run for every PR that touches `backend/alembic/versions/`. Any `must` =
`severity: block`.

## 1. Reversibility (must)

- [ ] `upgrade()` defined and idempotent against fresh DB.
- [ ] `downgrade()` defined and **not** `pass`.
- [ ] `downgrade()` restores the structural state (drop column, drop index,
      revert constraint). For data, downgrade may default to no-op only if
      explicitly documented with a comment `# DATA: forward-only; see
      <reason>`.
- [ ] Round-trip test possible: `alembic upgrade head && alembic downgrade -1`
      executes without error on the canonical fixture DB.

## 2. Linearity (must)

- [ ] `alembic history` shows a single head after applying this revision.
- [ ] `down_revision` points to the prior head, not a stale branch.
- [ ] No silent merge revisions auto-generated — if merge, must have
      explicit reviewer note.

## 3. Concurrent writes (must)

- [ ] No `ALTER TABLE ... ADD COLUMN NOT NULL` without `DEFAULT` on a
      table flagged as hot in `agent-memory:reviewer-backend / hot-tables`.
      For hot tables, use the two-step pattern: add nullable → backfill →
      add NOT NULL constraint.
- [ ] No `ALTER TABLE` that takes `ACCESS EXCLUSIVE` lock on a hot table
      without justification.
- [ ] Long-running data migrations chunked (batch size documented).

## 4. Index online creation (must)

- [ ] All `op.create_index` on production tables use
      `postgresql_concurrently=True` AND the revision's
      `transactional_ddl = False`.
- [ ] Unique indexes that may fail validation backfilled or pre-checked
      before creation.

## 5. RLS migration (must — if iam / multitenancy / billing)

- [ ] New table in iam/multitenancy/billing context has RLS policy
      created **in the same revision** as the table.
- [ ] Policy matches the `_meta/contracts/<context>/schema.sql` declared
      policy (predicate, command, role).
- [ ] `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` issued.
- [ ] Existing data passes the policy (or migration explicitly grants
      service-role bypass during backfill, with `RESET` at end).

## 6. Data destruction guard (must)

- [ ] No `op.drop_table` without explicit founder approval in PR comment
      AND an ADR reference for the deprecation.
- [ ] No `op.drop_column` without 2-step deprecation cycle (release N
      stops writing, release N+1 drops).
- [ ] No `TRUNCATE`.

## 7. Performance (should)

- [ ] EXPLAIN plan validated for new heavy queries against staging-like
      data (linked in PR description).
- [ ] No N+1 introduced by new query helpers (verify via integration test
      log count).
