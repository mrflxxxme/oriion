# Audit Section 5 — Backend Architect

**Auditor:** Backend Architect subagent
**Date:** 2026-05-19
**Scope:** Phase 00.3 + 00.4 architecture surface (combined PR on `claude/cool-bell-0c74ba`, 8 commits ahead of `main`)

## Verdict

**FLAG** — overall architecture is sound and disciplined (clean DDD layering, repository hygiene, RLS default-deny, partitioned audit log, atomic cost-ledger). One **High**-severity correctness/safety issue (Alembic `depends_on` mostly omitted on cross-context migrations, including for the cross-schema FK on `multitenancy.cell_members`-style references that are intentionally soft-FK but where the LLM-gateway hard-FK to `multitenancy.workspaces` is the lone declared dep), one **High** issue around `LLMUsageLog` lacking an append-only enforcement to match its "append-only audit" docstring, and several **Medium** issues (inconsistent GUC casting style in `billing` / `byok_keys` policies, an absolute `multitenancy → audit` stub coupling, environment-variable bypass of `Settings` in `kms_provider`, no DB-level CHECK forbidding `actor_id IS NULL` for `actor_type='user'`, repository surfaces returning raw ORM rows that escape the session boundary). No **BLOCK**-level findings.

## Bounded-context boundary report

| Context        | Pure self-imports?                                | Cross-context refs                                                                                                                              | Violations                                                                                                                                       |
|----------------|---------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `_shared`      | yes (no cross-context imports)                    | n/a — foundation                                                                                                                                | none                                                                                                                                             |
| `multitenancy` | mostly self + `_shared`                           | `src.iam.middleware` in routers (auth dep); `src._stubs.audit.emit_audit_event` in `cell_service.py`                                            | M1: `cell_service` imports concrete stub path, not abstract `src.audit.services.audit_service.emit_audit_event` (real impl already exists in PR) |
| `rbac`         | yes                                               | none in source code; cross-context FKs (`user_id`, `scope_id`) modelled as plain `uuid` with COMMENTs per ADR-024 — correct                     | none                                                                                                                                             |
| `audit`        | yes                                               | only `_shared`                                                                                                                                  | none                                                                                                                                             |
| `billing`      | yes (only model + `_shared`)                      | none                                                                                                                                            | none                                                                                                                                             |
| `llm_gateway`  | self + `_shared`                                  | **imports `src.billing.models.CreditTransaction` in `billing_service.py`** + **physical FK `byok_keys.workspace_id → multitenancy.workspaces`** | H1: cross-context model import (see Findings); FK is documented and permitted per ADR-024 ("workspace_id is in-context FK = ok" per audit scope) |
| `mcp`          | yes                                               | none                                                                                                                                            | none                                                                                                                                             |

Per the audit charter ("`llm_gateway.byok_keys.workspace_id REFERENCES multitenancy.workspaces(id)` is cross-context — check if implemented as physical FK (likely ok per contract) or rejected"): the migration declares it as a hard FK with `ON DELETE CASCADE` AND correctly sets `depends_on = "multitenancy_0001_workspaces"` so Alembic enforces ordering. That part is sound.

## Migration chain integrity

Visual chain (text-tree, ✓ = present in this PR):

```
_shared_0001_init  (root, no down_revision)
└── _shared_0002_current_user_id_helper
    ├── iam_0001_users                           (PRE-EXISTING, branched off _shared_0001_init — see L1)
    │   └── iam_0002_oauth_links
    │       └── iam_0003_consents
    │           └── iam_0004_sessions_refresh_tokens
    │               └── iam_0005_email_verification_tokens
    │                   └── iam_0006_password_reset_tokens
    ├── multitenancy_0001_workspaces             ✓
    │   └── multitenancy_0002_cells              ✓
    │       └── multitenancy_0003_cell_members   ✓
    │           └── multitenancy_0004_provision_cell_schema_function  ✓
    ├── rbac_0001_system_roles                   ✓
    │   └── rbac_0002_permissions                ✓
    │       └── rbac_0003_role_permissions       ✓
    │           └── rbac_0004_role_assignments   ✓
    │               └── rbac_0005_seed_built_in_roles  ✓
    ├── audit_0001_audit_log_partitioned         ✓
    ├── billing_0001_credit_transactions_skeleton ✓
    ├── llm_gateway_0001_llm_provider_config     ✓
    │   └── llm_gateway_0002_byok_keys           ✓  (depends_on = multitenancy_0001_workspaces — cross-schema FK)
    │       └── llm_gateway_0003_llm_usage_log   ✓
    └── mcp_0001_mcp_connections                 ✓
```

- All revision IDs unique (24 total).
- All `down_revision` strings point at existing revisions (no broken edges).
- Six bounded-context branches converge at `_shared_0002_current_user_id_helper` — chain is a DAG, no cycles.
- All seven new context-roots correctly branch off `_shared_0002_current_user_id_helper` (NOT `_shared_0001_init`) as charter required, except `iam_0001_users` (pre-existing — L1, informational only).
- Idempotency: every migration uses `IF NOT EXISTS` on CREATE and `IF EXISTS` on DROP; `CREATE OR REPLACE FUNCTION` used for helpers/triggers; no bare DROP-without-IF-EXISTS found in any reversed migration.
- Downgrades reverse cleanly: triggers before functions, policies before tables, partitions before parent.
- `depends_on` is only declared for `llm_gateway_0002_byok_keys` (→ `multitenancy_0001_workspaces`). Several other places likely need it too — see H2.

## Findings by severity

### Critical
*(none)*

### High

**H1. `llm_gateway.services.billing_service` imports `CreditTransaction` model from `billing` context — direct cross-context coupling at the source layer.**
- File: `backend/src/llm_gateway/services/billing_service.py:26` — `from src.billing.models import CreditTransaction`.
- ADR-024 §2 prescribes that bounded-context source modules must import their own models or `_shared`. Cross-context coupling should be via published events, cross-context API calls, or an injected port — not direct ORM access.
- The atomic 3-currency write requires both rows in one TX, so an event-driven decoupling is not free here. Acceptable short-term resolutions:
  - Move `record_llm_cost` to a coordinator under `_shared/` (or a new top-level `billing_orchestration` module) and have both contexts depend on it inward.
  - Or, expose a `billing.services.ledger.record_debit(session, ...)` port that `llm_gateway` calls; that port owns the `CreditTransaction` ORM. Keeps llm_gateway oblivious to the schema.
- Suggested fix: extract a `src/billing/services/ledger_service.py::record_debit(...)` taking the rich payload, and have `billing_service.record_llm_cost` call it. This restores the contract that llm_gateway owns `llm_usage_log` and billing owns `credit_transactions`, with a thin published port between them.

**H2. `depends_on` (Alembic) only set on `llm_gateway_0002_byok_keys` despite multiple migrations referencing cross-schema objects.**
- Files: every migration except `llm_gateway/0002_byok_keys.py` has `depends_on = None`.
- `_shared.set_updated_at()` and `_shared.current_user_id()` are correctly enforced through `down_revision = "_shared_0002_current_user_id_helper"`, so they are fine.
- But several DDL bodies execute SQL that depends on *runtime* cross-schema state that is not enforced by chain (cross-schema RLS policy ALTER):
  - `multitenancy/0001_workspaces.py` `workspaces_select_own` policy references `multitenancy.cells` and `multitenancy.cell_members` — these don't exist yet when `0001` runs (they're created in 0002/0003 of the same context, so order within the branch protects this — but only at policy-CREATE time. Postgres evaluates policy bodies lazily so this is technically safe, but the policy temporarily references nonexistent tables; first SELECT after `0001` and before `0002` would error.).
  - `audit/0001_audit_log_partitioned.py` is standalone — fine.
- Suggested fix: defer creation of cross-table RLS policies to the migration that introduces both ends (move `workspaces_select_own` policy creation into `multitenancy/0003_cell_members.py`), or add `depends_on = ("multitenancy_0003_cell_members",)` to whatever migration is the *first* application user of the policy. Document policy-references-nonexistent-table as deliberate.

**H3. `llm_gateway.llm_usage_log` is documented as "append-only audit" but has no DB-level UPDATE/DELETE block, unlike `audit.audit_log`.**
- File: `backend/migrations/versions/llm_gateway/0003_llm_usage_log.py:109` grants `SELECT, INSERT, UPDATE, DELETE` to `oriion_app`; no `deny_update_delete` trigger.
- The model docstring (`models.py:115`) and migration comment (`0003:78`) call it "append-only" — runtime tampering by app role is fully permitted.
- Suggested fix: either (a) add the same `audit.deny_update_delete()` trigger pattern to `llm_gateway.llm_usage_log` and revoke `UPDATE, DELETE` from `oriion_app`; or (b) downgrade the docstring claim to "logically append-only by convention". The cost-ledger invariant (`SUM(credit_tx.amount_rub) == SUM(llm_usage_log.cost_rub)` per cell) is silently corruptible without enforcement.

### Medium

**M1. `multitenancy.services.cell_service` hard-codes import from `src._stubs.audit` instead of the real `src.audit.services.audit_service`.**
- File: `backend/src/multitenancy/services/cell_service.py:18` — `from src._stubs.audit import emit_audit_event  # 00.3-audit-subagent will swap`
- The real `emit_audit_event` IS present in this same PR (`src/audit/services/audit_service.py:169`). The comment promises a swap that never happened.
- Result: every `cell_service` audit emit goes only to structlog, never to the partitioned audit table — `multitenancy.cell.created`, `member.invited`, etc. are not persisted.
- Suggested fix: replace import to `from src.audit.services.audit_service import emit_audit_event` and pass `session=self._session` to each call so the row lands in `audit.audit_log`.

**M2. RLS policy GUC casting inconsistent — `billing` / `byok_keys` / `llm_usage_log` use inline `current_setting(...)::uuid`, while `multitenancy` uses `_shared.current_workspace_id()` helper.**
- Files:
  - `migrations/versions/billing/0001_credit_transactions_skeleton.py:77` — `cell_id = current_setting('app.current_cell_id', true)::uuid`
  - `migrations/versions/llm_gateway/0002_byok_keys.py:84` — `workspace_id = current_setting('app.current_workspace_id', true)::uuid`
  - `migrations/versions/llm_gateway/0003_llm_usage_log.py:103` — same
  - `migrations/versions/mcp/0001_mcp_connections.py:100` — uses helper `_shared.current_workspace_id()` (correct pattern)
- The helper `_shared.current_workspace_id()` swallows invalid-cast errors and returns NULL (default-deny). The inline `::uuid` cast raises `invalid_text_representation` on a malformed GUC, which manifests as a 500-class error from a perfectly-RLS-defendable code path.
- ADR-009 amendment specifically introduced the helper for this reason; the helpers should be used uniformly.
- Suggested fix: in `billing` / `byok_keys` / `llm_usage_log` migrations, replace inline `current_setting(...)::uuid` with the `_shared.current_<…>_id()` helper.

**M3. `kms_provider.get_kms_provider()` reads `os.environ['KMS_BACKEND']` directly, bypassing `Settings.kms_backend`.**
- File: `backend/src/llm_gateway/services/kms_provider.py:105`
- `LocalAESKMS.__init__` similarly reads `BYOK_MASTER_KEY_B64` directly from `os.environ`.
- `Settings` already defines both (`config.py:84`, `:92`) with proper `SecretStr` typing for the master key.
- Two consequences:
  - The cached `Settings` and the un-cached env reads can drift if a process mutates env after `Settings()` is constructed (legal in tests; surprising in code review).
  - `SecretStr` protections (no accidental `__repr__` leakage) are bypassed.
- Suggested fix: factory should take an injected `Settings` (FastAPI Depends) and `LocalAESKMS` should accept `master_key_b64: SecretStr` so `Settings` is the only env-reader.

**M4. `audit.audit_log` has no DB-level invariant that `actor_id IS NULL` only when `actor_type = 'system'`.**
- File: `backend/migrations/versions/audit/0001_audit_log_partitioned.py:54-72`
- The model and DDL both allow `actor_id` NULL for any `actor_type`, including `'user'` / `'agent'` where an actor identifier is mandatory.
- Application-side `emit_audit_event` requires a UUID for `actor_id` (signature is `actor_id: UUID`) but the DB column is nullable — a future caller could bypass.
- Suggested fix: add `CHECK ((actor_type = 'system') OR (actor_id IS NOT NULL))` to the parent partitioned table.

**M5. Repositories return raw SQLAlchemy ORM instances escaping the session boundary; downstream code can lazy-load and trigger a `MissingGreenlet` error at runtime.**
- Files: every `*_repository.py` returns `Workspace`, `Cell`, `CellMember`, `BYOKKey`, `AuditLog`.
- `get_db()` uses `expire_on_commit=False, autoflush=False` (mitigates expire after commit), but `selectinload`/eager strategies are nowhere applied, so any attribute access on a relationship after the session is closed will async-load and crash.
- Concrete risk: `WorkspaceRepository.find_by_user_id` returns `Workspace` ORM instances; the router then maps `Workspace.cells` indirectly via `WorkspaceOut.model_validate` — if `WorkspaceOut` references `cells`, this lazy-loads after `get_db()` already closed.
- Suggested fix: (a) define explicit DTO mappers per service that materialise needed fields before returning; OR (b) document that all ORM-returning repository methods MUST be called while session is open and consumers must not touch unloaded relationships. Add a `MappedAsDataclass` or pydantic-from-attributes contract test.

**M6. `multitenancy_0001_workspaces` policy `workspaces_select_own` references tables that do not yet exist when the migration runs.**
- File: `backend/migrations/versions/multitenancy/0001_workspaces.py:75-87`
- The policy references `multitenancy.cells` and `multitenancy.cell_members`, both created in `0002` and `0003` respectively. Postgres parses-only at CREATE POLICY time (no name resolution), so the migration succeeds, but the policy body resolves names only on first SELECT — any read of `multitenancy.workspaces` between migrations would error.
- In practice the migrations are applied as a block, so this is latent only — but `alembic upgrade --sql` / single-step migrations would break.
- Suggested fix: move the `workspaces_select_own` policy creation to `multitenancy/0003_cell_members.py` (after both reference tables exist).

### Low

**L1. `iam_0001_users` is a pre-existing migration that branches off `_shared_0001_init`, not `_shared_0002_current_user_id_helper`.**
- This is consistent with the chain root note in `_shared/0001_init.py` (the IAM branch predates the helper migration).
- No fix required — informational only. Audit charter explicitly asked about new contexts using `_shared_0002` as their root; iam predates that rule.

**L2. `multitenancy.provision_cell_schema(uuid)` runs as `SECURITY DEFINER` but the function body uses `format(..., quote_ident(schema_name))` — schema name is fully internal (`cell_<uuid_underscored>`) so SP injection is impossible, but the search_path mitigation should also include the target schema, not just `pg_catalog, public`.**
- File: `migrations/versions/multitenancy/0004_provision_cell_schema_function.py:44`
- Suggested fix: drop `public` from `search_path` (it's unused inside the function) so a malicious extension in `public` can't shadow `gen_random_uuid` etc.

**L3. `LLMUsageLog.id` is `bigserial` while every other table in the codebase uses `uuid PRIMARY KEY DEFAULT gen_random_uuid()`.**
- File: `migrations/versions/llm_gateway/0003_llm_usage_log.py:31`
- Two distinct ID schemes within one schema is mildly inconsistent and complicates `payload.llm_usage_log_id` correlation in `credit_transactions` (mixing int and uuid). Acceptable choice for very-high-volume tables, but worth a comment explaining the deviation.
- Suggested fix: either standardise on uuid (cost: slightly larger PKs), or COMMENT on the column explaining bigserial choice.

**L4. `audit.audit_log` indexes are created `ON audit.audit_log` (parent) — Postgres propagates correctly to partitions, but the SEED partitions (`audit_log_2026_05`, `audit_log_2026_06`, `audit_log_default`) inherit them by partition-pruning semantics.**
- This is fine; flagged because the migration comment says indexes "propagate to every partition", which is true *for partitioned indexes*, but is only correct since Postgres 11+ and only because we `CREATE INDEX` on the parent (correct).
- No fix required — verify in integration test that future-created partitions inherit the index (looks correct given `INHERITS` behaviour for partitioned tables).

**L5. `WorkspaceRepository.find_by_user_id` does a 3-way join (`workspaces`-`cells`-`cell_members`) but `cells.archived_at` is not filtered.**
- File: `backend/src/multitenancy/repositories/workspace_repository.py:32-49`
- A user whose only membership is in an archived cell still sees that workspace in `list_workspaces`. The cell row is still present (archive is soft), so `EXISTS(member→cell→workspace)` returns true.
- Suggested fix: add `Cell.archived_at.is_(None)` to the join predicate, OR document that archived-cell-only memberships still count for workspace visibility.

**L6. `BYOKKey` model exposes `key_encrypted: bytes` as a public attribute with no `repr=False` / `init=False` guard.**
- File: `backend/src/llm_gateway/models.py:101`
- A stray `repr(byok_key_instance)` will print the ciphertext blob to logs. Not a secret leak (it's already encrypted), but it's noisy and unexpected.
- Suggested fix: SQLAlchemy 2.x supports `mapped_column(LargeBinary, ..., info={"repr": False})` patterns; add a `__repr__` override on `BYOKKey` that excludes the encrypted blob.

**L7. `cells_workspace_slug_uidx` is a UNIQUE index NOT a partial index — cells.archived_at is ignored.**
- File: `migrations/versions/multitenancy/0002_cells.py:42-47`
- Re-creating a cell with the same slug after archive (= soft-delete) is impossible because the unique index doesn't filter on `archived_at IS NULL`.
- Compare `workspaces_slug_active_uidx` which IS partial (`WHERE deleted_at IS NULL`).
- Suggested fix: change `cells_workspace_slug_uidx` to `WHERE archived_at IS NULL`.

**L8. `BYOKKey.workspace_id` ON DELETE CASCADE on the FK to `multitenancy.workspaces` — workspace delete will silently destroy BYOK keys.**
- File: `migrations/versions/llm_gateway/0002_byok_keys.py:30`
- Workspaces are soft-deleted (`deleted_at`), so `ON DELETE CASCADE` only fires on a hard delete which presumably is admin-only. Still, hard-delete cascade through a key-management table is opinionated; `ON DELETE RESTRICT` would force the admin to explicitly revoke keys.
- Suggested fix: switch to `ON DELETE RESTRICT` to align with the `multitenancy.cells.workspace_id → workspaces.id` RESTRICT semantic used elsewhere.

**L9. `mcp_connections.workspace_id` declared `NOT NULL` but no FK constraint, with no in-context table referencing.**
- File: `migrations/versions/mcp/0001_mcp_connections.py:46`
- The schema deliberately treats this as a soft-FK (cross-context per ADR-024). Acceptable, but the COMMENT block omits explicit "cross-context FK → multitenancy.workspaces.id" callout that other contexts include (e.g. `cell_members.user_id`).
- Suggested fix: add a `COMMENT ON COLUMN mcp.mcp_connections.workspace_id IS 'Cross-context FK → multitenancy.workspaces.id (not enforced as DB constraint).'` for searchability and audit clarity.

**L10. `record_llm_cost` does two `await session.flush()` calls (one per row) — could be a single flush at the end.**
- File: `backend/src/llm_gateway/services/billing_service.py:120, 147`
- The first flush is needed because `tx_row.payload` references `usage_row.id`. The second is gratuitous (caller's commit will flush). Net: one extra DB roundtrip per LLM call.
- Suggested fix: drop the second `flush()`. The 90th-percentile LLM call already eats hundreds of ms; one roundtrip won't tank latency, but at scale this matters.

**L11. `_shared.current_user_id()` is `STABLE` but `current_setting('…', true)` is technically `VOLATILE` from PG's planner perspective when the setting can change mid-tx.**
- File: `migrations/versions/_shared/0002_current_user_id_helper.py:42`
- The function is marked `STABLE` so PG can cache results across an RLS policy plan. For RLS this is fine because `SET LOCAL` is set once per tx and unset on commit/rollback. But if someone calls `SET LOCAL` mid-tx, the planner may use the cached value.
- Suggested fix: document the constraint that `set_tenant_context` MUST be called before any RLS-protected query (already true), and add a `set_tenant_context` invariant test that exercises mid-tx `SET LOCAL`.

## Architectural observations (informational)

- 3-GUC RLS model is cleanly implemented in `_shared/db/rls.py` with `asynccontextmanager` + keyword-only args, defeating positional misuse. Excellent.
- Atomic 3-currency cost ledger (`billing_service.record_llm_cost`) correctly uses single-session-flush pattern with caller-owned commit (the FastAPI request dependency `get_db` is the single commit point). One service-layer call, two row writes, one CloudEvent emit, all inside the same TX. Matches llm-gateway invariant #7.
- Append-only enforcement on `audit.audit_log` via `BEFORE UPDATE/DELETE` trigger is defence-in-depth: even a DBA connection without `BYPASSRLS` cannot mutate rows. Combined with no-GRANT-of-UPDATE/DELETE on `oriion_app`, retention drops by partition DROP. Solid pattern.
- Partitioned audit log is correctly designed: monthly RANGE, composite `(id, ts)` PK, indexes on parent (propagate), default partition catches misses. Two seed months + maintenance job for rolling forward — well-scoped Wave 0.
- Repository pattern is consistently used; services compose repositories; routers compose services via FastAPI Depends. No business logic found in repos (only CRUD + cursored queries). Good.
- All public service / repository methods are `async def`. No `asyncio.run` or `loop.run_until_complete` found in src — clean async discipline.
- `get_db` correctly creates one AsyncSession per request, commits on happy path, rolls back on exception. Single source of session lifetime. Good.
- Cross-context FK soft-refs (e.g. `multitenancy.cell_members.user_id → iam.users.id`) are correctly modelled as plain `uuid` columns with COMMENT ON COLUMN documentation — exactly per ADR-024. The lone hard FK `llm_gateway.byok_keys.workspace_id → multitenancy.workspaces.id` is documented and `depends_on` is set — acceptable per audit charter.
- `LocalAESKMS` vs `YandexKMS` swap is correctly behind a `Protocol`; factory selects via env. Good separation. (See M3 for the env-vs-Settings concern.)
- `LLMRouter` is properly stateless, takes immutable providers + mutable circuits, and is per-request — consistent with the broader async-correctness story.
- HNSW index in `provision_cell_schema` (`m=16, ef_construction=64`) matches pgvector defaults validated by Wave 0 smoke benchmarks (per docstring).
- DDL→ORM model parity is high (workspaces, cells, cell_members, llm_provider_config, byok_keys, llm_usage_log, audit_log, credit_transactions, system_roles, permissions, role_permissions, role_assignments, mcp_connections all have matching CHECK constraints + indexes on both sides).
- RBAC seed migration is idempotent (`ON CONFLICT DO NOTHING`) and the `_ROLES` / `_PERMISSIONS` / `_ROLE_PERMS` constants are correctly version-pinned inside the migration (good — migration is the source of truth, not a stray YAML).

## Summary

The Phase 00.3 + 00.4 architecture surface is **largely well-executed and consistent with ADR-024 boundaries, ADR-009 RLS model, and ADR-014 audit-log invariants**. The migration chain is a clean DAG with idempotent up/down halves and correct branching off `_shared_0002`. The atomic cost-ledger and partitioned audit log are textbook patterns. The 3-GUC RLS context-setter is exactly the right shape.

**Recommended action before merge:** address H1 (cross-context model import in llm_gateway), H2 (broaden `depends_on` declarations or document the policy-on-not-yet-extant-tables pattern), H3 (either enforce or de-claim append-only on `llm_usage_log`), and M1 (swap the audit stub in `cell_service`). M2 through M6 are improvement candidates but not blockers for Wave 0. All Low-severity items are post-merge cleanup.

Finding count: 3 High, 6 Medium, 11 Low = 20 total (under 25 cap).
