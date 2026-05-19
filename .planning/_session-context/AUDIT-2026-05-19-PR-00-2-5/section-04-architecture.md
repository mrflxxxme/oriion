# Audit Section 4 — Backend Architect (PR for Phase 00.2.5)

**Auditor:** Backend Architect subagent
**Date:** 2026-05-19
**Scope:** Phase 00.2.5 integration PR on `claude/heuristic-rhodes-f7a3ef` — 6 commits ahead of `b3837f0` (PR #30 merge into main).
**Diff surface (vs merge base):** 36 files, +2,325 / −422; the architecturally-load-bearing files are `backend/src/iam/services/{auth_service,consent_service}.py`, `backend/src/iam/deps.py`, `backend/src/_shared/db/base.py`, `backend/src/multitenancy/services/cell_service.py`, `backend/tests/conftest.py`, `backend/tests/integration/test_e2e_auth_flow.py`, and the deletion of `backend/src/_stubs/`.

## Top-level verdict: **FLAG**

The integration is structurally sound and the prior PR #30 audit findings (H1 / H2 / H3 / M1) did not regress. The stub→real swap is implemented correctly with session threading, the testcontainers fixture is well-reasoned, and the `Base.type_annotation_map` fix is the right level of intervention. **However, one HIGH-severity correctness gap is introduced by this PR** (RLS write-policy violation on unauthenticated `register()` against the production `oriion_app` role), plus three MEDIUM findings tied to ADR-024 boundary discipline and one MEDIUM around the audit-event coupling pattern.

No BLOCK-level issues. The HIGH item is masked in the E2E suite because the testcontainers DSN connects as a Postgres superuser (which bypasses `FORCE ROW LEVEL SECURITY`), so the failure mode will first surface in staging — important to fix before Phase 00.5 wires the multitenancy routers behind real auth.

---

## Findings by severity

### BLOCK
*(none)*

### HIGH

**H1. `register()` flow inserts into RLS-FORCEd `multitenancy.{workspaces, cells, cell_members}` with no tenant context — green in tests only because the testcontainers user is a Postgres superuser.**

- Files:
  - `backend/src/iam/services/auth_service.py:156-160` — `provision_initial_workspace(session=self._session, user_id=user.id, email_localpart=...)` invocation from inside `register()`, which executes **before** any auth/login has happened.
  - `backend/src/multitenancy/services/workspace_service.py:181-194` — INSERT into `multitenancy.workspaces` then `multitenancy.cells` via repositories. No `set_tenant_context` call anywhere in this codepath.
  - `backend/migrations/versions/multitenancy/0001_workspaces.py:74-75` — `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on workspaces.
  - `backend/migrations/versions/multitenancy/0002_cells.py` — same pattern for cells.
  - `backend/migrations/versions/multitenancy/0003_cell_members.py:145-161` — per-command write policies (`*_write_insert_with_context`) gated by `_shared.current_user_id() IS NOT NULL`. With `app.current_user_id` GUC unset → helper returns NULL → INSERT WITH CHECK fails.
- Architectural concern: there is no path in `register()` where `set_tenant_context` could meaningfully be called — the user does not yet exist as a row when the INSERT into `iam.users` runs, and even after the row exists, the registration session never sets `app.current_workspace_id` / `app.current_cell_id` because those IDs are precisely what `provision_initial_workspace` is producing. So the operation is intrinsically a "bootstrap" write that must escape RLS.
- Why the E2E test is green: `backend/tests/conftest.py:96-100` boots testcontainers as `username="oriion"` which is the cluster superuser (testcontainers' default). PostgreSQL superusers bypass RLS even with `FORCE ROW LEVEL SECURITY` (only `ALTER ROLE … BYPASSRLS` granted users do; superusers have it implicitly). `test_e2e_auth_flow.py` therefore exercises the happy path without RLS in the loop. The existing `tests/multitenancy/test_rls_isolation.py:96` already documented this trap explicitly (`SET LOCAL ROLE oriion_app` is required to engage RLS) — `test_e2e_auth_flow.py` does **not** do this.
- Suggested fix (in increasing fidelity):
  1. **Cheap, immediate (Phase 00.2.5 fix):** add `await session.execute(text("SET LOCAL ROLE oriion_app"))` to the `override_get_db` fixture in `test_e2e_auth_flow.py:117-126`. The test must turn red. Once it's red, decide between (2) and (3).
  2. **Architecturally correct (Phase 00.5 prerequisite):** wrap `provision_initial_workspace` in a `SECURITY DEFINER` SQL function or invoke it under a one-shot bootstrap role with `BYPASSRLS` (e.g. `oriion_provisioner`). This is the same pattern the `multitenancy.provision_cell_schema(uuid)` SQL helper already uses (see `_call_provision_cell_schema`); the workspaces/cells insert just hasn't followed suit.
  3. **Wave-1 alternative:** keep `register()` writing as `oriion_app` but expand the `*_write_insert_with_context` policy to: `WITH CHECK (_shared.current_user_id() IS NOT NULL OR pg_has_role(current_user, 'oriion_provisioner', 'MEMBER'))`. Documented in `contracts/multitenancy/README.md` "Service contract" section.
- Tracking: this finding intersects launch-checklist Section 9 Risk #3 ("RLS context not set on register's INSERT chain") which was dismissed as safe because "if register runs as superuser, RLS is bypassed anyway". That assumption holds for the test container but **does not hold in production** (`oriion_app` is the documented production role per `_shared/0001_init.py:111-128`). The risk is real; the test fixture is hiding it.

---

### MEDIUM

**M1. `iam.auth_service` directly imports a free function from `multitenancy.services.workspace_service` — first cross-context functional dependency on multitenancy from iam outside the previously-sanctioned audit stub call.**

- File: `backend/src/iam/services/auth_service.py:59` — `from src.multitenancy.services.workspace_service import provision_initial_workspace`
- Architectural concern: ADR-024 §4 ("Bounded-context coupling explicit") states cross-context dependencies must be visible in `contracts/<A>/README.md`'s "Service contract" section. The dependency IS documented in `contracts/multitenancy/README.md:124-150` ("Service contract — symbols consumed by other contexts"), so this is a **sanctioned exception** rather than a violation. Per the audit charter question: this is **OK per ADR-024 as currently amended**.
- However, the import shape couples `iam` to `multitenancy`'s service-layer module path. If `multitenancy` ever refactors `workspace_service.py` → `services/provisioning/workspace_service.py`, `iam` breaks. The pre-PR architecture used `src._stubs/multitenancy.py` precisely to insulate this surface — that insulation is gone now.
- Suggested fix (deferrable to Wave 1): re-export `provision_initial_workspace` and `WorkspaceProvisionResult` at `src/multitenancy/__init__.py`, then have `iam.auth_service` import from the package root. This restores the "stable cross-context surface" property that ADR-024 §4 implies without re-introducing a stub layer.
- No other new cross-context model imports are introduced by this PR. The pre-existing `llm_gateway/services/billing_service.py:26 → src.billing.models.CreditTransaction` (sanctioned per HANDOFF.md:123) is unchanged and not re-litigated here.

**M2. Audit emission with `self._session` participates in the outer TX, but the audit row is never gated by RLS — the cell_id / workspace_id columns on `audit.audit_log` are stamped from arguments, not from GUCs, with no consistency check.**

- Files:
  - `backend/src/iam/services/auth_service.py:184-196` — `emit_audit_event(..., session=self._session, workspace_id=provision.workspace_id, cell_id=provision.cell_id)` for register.
  - `backend/src/iam/services/auth_service.py:257-267` — login: `session=self._session` but `workspace_id`/`cell_id` **omitted** (defaults to None).
  - `backend/src/iam/services/auth_service.py:292-300`, `:322-332`, `:356-366`, `:384-392`, `:474-482`, `:496-504` — every other audit emit in iam: `workspace_id`/`cell_id` defaulted to None.
  - `backend/migrations/versions/audit/0001_audit_log_partitioned.py` — **no RLS** on `audit_log`; only triggers + GRANTs.
- Architectural concern (this PR-specific): `audit.audit_log` deliberately has **no RLS** (per ADR-014 amendment 2026-05-19 audit log is a cross-tenant compliance artefact; integrity comes from append-only triggers + retention partitioning, not row-level visibility). So `set_tenant_context` is **not required** for the audit write itself — this answers the audit charter Q6 directly: **no, RLS context propagation is NOT needed before the audit write.**
- However: the per-event call sites are inconsistent about whether they stamp `workspace_id` / `cell_id`. The login/refresh/logout/verify-email/forgot/reset events all leave both NULL even though the user (post-register) is associated with exactly one workspace + cell. This degrades the partial-index utility (`audit_log_cell_id_ts_idx`, `audit_log_workspace_id_ts_idx`) for per-tenant audit queries — the partial index `WHERE cell_id IS NOT NULL` skips ~95% of iam events because they don't carry the context.
- Suggested fix: extend `AuthService` to resolve `(workspace_id, cell_id)` from the user_id once at session-issue time (e.g. via `WorkspaceRepository.find_by_user_id` returning the single Wave-0 workspace) and stamp both on every iam audit event. Wave 1 (multi-workspace) will require the caller to pass the active workspace anyway.
- Deferrable: this is observability hygiene, not correctness. Tracked but not blocking.

**M3. Per-event `AuditRepository(session)` instantiation in `emit_audit_event` creates one repo object per audit event — fine for cost but loses the "repo is the unit-of-work owner" pattern used elsewhere.**

- File: `backend/src/audit/services/audit_service.py:207-220` — every `emit_audit_event` call constructs `AuditRepository(session)`, calls `insert`, throws the repo away.
- Architectural concern: every other context in this codebase (`iam`, `multitenancy`, `rbac`, `llm_gateway`) instantiates repositories once at service-construction time (via `__init__`) and holds them as `self._<thing>_repo`. The free-function `emit_audit_event` is the odd one out, which signals it's living at the wrong abstraction level: it pretends to be a side-effect-free module-level helper but actually owns a write to a partitioned table. The Phase 00.2.5 swap doubles down on this by passing the session through every callsite (10+ in iam + multitenancy services), which is exactly what an injected `AuditService` collaborator would solve in one place.
- Trade-off vs alternatives (per audit charter Q1):
  - **Pass session per call (current state)**: works, but every cross-context service now physically depends on the iam request's session lifecycle. Worse, the function signature (10 parameters, 4 kwonly defaults) screams "I should be a method on a service."
  - **Separate transactional emitter (DI'd `AuditService`)**: best for testability — the current per-test conftest hack (`tests/iam/unit/conftest.py:25-38` — autouse patch of `emit_audit_event` at both iam import sites to dodge unit-test session mocking) would disappear entirely. The collaborator would just be replaced with a mock at construction time. This is the right Wave-1 refactor.
  - **Outbox pattern**: correct for cross-service delivery (Redis Streams / Kafka in Wave 4+), but overkill for Wave 0 where audit_log is a same-DB write. Adopt when CloudEvents stops being log-only.
- Suggested fix: convert callers to take an injected `AuditService` (already exists as a class at `audit/services/audit_service.py:83-132` — just not used anywhere). Delete the free function once all 10+ callsites are migrated. Defer to Phase 00.5 (it's not blocking 00.2.5).

**M4. `db_session_committed` fixture for `commit_required` marker — sound carve-out but the cleanup TRUNCATE is dangerous if the application schema set grows.**

- File: `backend/tests/conftest.py:274-315`.
- Architectural concern (audit charter Q3, second part): the fixture is **the correct architectural choice** for tests that need cross-TX semantics (E2E TestClient flows reading rows committed by a previous request). The pattern — committed writes + post-test TRUNCATE — is the canonical alternative to SAVEPOINT-rollback for tests that can't use the rollback trick. Not an anti-pattern.
- However, the TRUNCATE schema list is hardcoded: `('iam','multitenancy','rbac','audit','llm_gateway','billing','mcp')`. When Wave-1 introduces `agents`, `tasks`, `artifacts`, `memory` (per ADR-024 §1), the next test author has to remember to update this list or face dirty-state bleed between tests. The 12 schemas declared in `_shared/0001_init.py:49-61` are the source of truth.
- Suggested fix: derive the schema list from `_shared.SCHEMAS` (or query `information_schema.schemata WHERE schema_owner = 'oriion'` at fixture start). Catches schema drift automatically. 2-line change.

---

### LOW

**L1. `Base.type_annotation_map` global `Mapped[datetime] → DateTime(timezone=True)` is the right level of fix.**

- File: `backend/src/_shared/db/base.py:30-32`.
- Audit charter Q4: yes, this is the right level. The alternative — column-level `DateTime(timezone=True)` on every `Mapped[datetime]` — would scatter the same annotation across ~50 model columns and create a "forget to add it" bug class. The cluster-wide invariant per ADR-009 + ADR-014 is **all timestamps are timestamptz** (TZ-aware UTC); naive datetimes are a bug in this codebase, not a feature. A future model wanting naive datetime is a smell; if it ever happens, it can opt out via explicit `mapped_column(DateTime(timezone=False))` which overrides the type_annotation_map.
- The docstring is exemplary — clearly explains why the override exists (asyncpg's "can't subtract offset-naive and offset-aware datetimes" failure), what the underlying DDL already had, and that the change is "type-level correctness" not a behavioural change. No fix needed.

**L2. Session-scoped sync `pg_container` + function-scoped async `db_engine` is the right pattern given asyncpg's loop-binding constraint.**

- File: `backend/tests/conftest.py:79-119, 219-242`.
- Audit charter Q3, first part: yes, this is the correct architectural decomposition. The launch-checklist initially proposed "Revert `asyncio_default_fixture_loop_scope` back to `'session'`" (Section 4 bullet 5) which the conftest docstring explicitly rejects on technical grounds — asyncpg connections can't cross event loops, and pytest-asyncio installs a fresh loop per test by default. Keeping function-scoped engine + session-scoped container is the cleanest split. Engine create/dispose is ~10ms; the container boot is the expensive bit and IS amortized once per session.
- Alternative considered but correctly rejected: switching to `psycopg` (sync, no loop binding) in tests would let us go session-scoped engine — but then prod (`asyncpg`) and tests (`psycopg`) would have different connection semantics, masking transaction-isolation bugs. Current design is correct.

**L3. Phase 00.5 boundary is cleanly drawn.**

- Audit charter Q5: the deferral is explicit and well-documented in `tests/integration/test_e2e_auth_flow.py:425-454` (`test_llm_chat_endpoint_is_not_yet_wired`). The test asserts 404 on `/api/v1/llm/{chat/completions, embeddings, byok-keys}` — anyone wiring those routers in 00.5 will see the assertion flip and know they must extend the E2E suite. The `HANDOFF.md:102-118` Phase 00.5 brief is precise about what's inherited (router code exists, handlers return 501, provider DI lifespan assembly is the missing piece).
- What Phase 00.5 inherits from this PR:
  1. A working `AuthService` that already threads the session for downstream audit emission — Phase 00.5's new routers can rely on the same `get_db` → real-commit-per-request semantics.
  2. The `db_session_committed` fixture pattern is now established — Phase 00.5's E2E expansion can reuse it for the LLM chat happy path (cost-ledger SUM assertion already covered in `tests/llm_gateway/test_cost_ledger_sum_match.py` per the E2E docstring).
  3. `Base.type_annotation_map` is global — Phase 00.5's new models (vertical-template-derived agent archetypes per ADR-029) don't need to repeat the boilerplate.
  4. The `MultitenancyError` handler is **not** yet installed in main.py (the launch brief mentions it as Phase 00.5 work). Phase 00.5 must replicate the `IamError` handler pattern in `main.py:59-80` for the multitenancy router exceptions.
- Clean boundary: no half-wired routers, no dead code paths, no "ghost" dependencies dangling in main.py. The 5-test E2E suite is a complete picture of what works today.

**L4. Unit-test conftest autouse-patches `emit_audit_event` at the import sites — clean workaround for the session-coupling mismatch but signals the M3 abstraction problem.**

- File: `backend/tests/iam/unit/conftest.py:25-38`.
- This fixture exists because the Phase 00.2.5 swap forced every unit test that touches `AuthService` to provide a session-shaped mock that can `await session.flush()` cleanly. The autouse patch dodges that by replacing `emit_audit_event` with `AsyncMock()` at both import sites (`src.iam.services.auth_service` and `src.iam.services.consent_service`).
- This is the correct fix given the current free-function design — patching at the import-site (not the source) is name-bound and correct Python practice. The docstring is excellent at explaining why.
- However, if M3's `AuditService` collaborator refactor lands, this fixture becomes obsolete and can be deleted — the mock would just be passed into `AuthService.__init__` like every other repo.

**L5. `ConsentService` is constructed with `session=db` as a kwonly arg in `iam/deps.py:48-56` — the parameter ordering forces `session` last; defensive but slightly verbose.**

- File: `backend/src/iam/services/consent_service.py:24-37` — `def __init__(self, consent_repo, consent_version, *, session: AsyncSession)`.
- The kwonly `session` makes it impossible to accidentally pass the session positionally (good defence against argument-swap bugs). The pattern is consistent with `set_tenant_context`'s kwonly args in `_shared/db/rls.py:37-43`. Keep.

---

## ADR compliance summary (audit charter Q7)

| ADR | Compliance | Notes |
|---|---|---|
| **ADR-024 (bounded contexts)** | ✅ COMPLIANT (sanctioned exceptions documented) | The two cross-context functional imports introduced by this PR (`iam → audit.emit_audit_event`, `iam → multitenancy.provision_initial_workspace`) are both pre-declared in `contracts/multitenancy/README.md:124-150` ("Service contract") and `contracts/audit/` (implicit via `emit_audit_event` being the only public API of the audit context). No surprise couplings. M1 + M3 are post-merge polish, not violations. |
| **ADR-014 (security)** | ⚠️ PARTIAL | Audit-log append-only via trigger + `oriion_app` lacking UPDATE/DELETE grants — unchanged from PR #30, still correct. **However, H1's RLS-bypass-via-superuser-in-tests fails the spirit of "3-GUC default-deny RLS posture" (Wave 0 security decision #1) — the E2E test certifies a behaviour the production role cannot replicate.** |
| **ADR-009 (RLS / 3-GUC model)** | ⚠️ PARTIAL | The 3-GUC helper (`set_tenant_context`) and `_shared.current_user_id()` are correctly designed (see L1 of PR #30 audit) and not touched here. But the `register()` bootstrap flow is the first real-world callsite that has no GUC to set, and the design does not yet provide an answer. ADR-009 amendment 2026-05-19 #2 says "missing GUC → NULL → default-deny" — H1 is the consequence biting back. |
| **ADR-018 (RU-billing)** | ✅ NO IMPACT | This PR does not touch llm_gateway billing pathways; the cost-ledger atomic write contract is unchanged. |

---

## Cross-context import graph after `_stubs/` deletion (audit charter Q2)

Full inventory of `src.<ctx_A>.* → src.<ctx_B>.*` edges where `A ≠ B`:

| From context | To context | Symbol | Verdict |
|---|---|---|---|
| `iam.services.auth_service` | `audit.services.audit_service` | `emit_audit_event` (NEW) | Sanctioned per `contracts/audit/` — audit is the explicit "consumed by everyone" context. |
| `iam.services.consent_service` | `audit.services.audit_service` | `emit_audit_event` (NEW) | Same as above. |
| `iam.services.auth_service` | `multitenancy.services.workspace_service` | `provision_initial_workspace` (NEW) | Sanctioned per `contracts/multitenancy/README.md:124-150`. See M1 for import-shape concern. |
| `multitenancy.services.cell_service` | `audit.services.audit_service` | `emit_audit_event` (pre-existing, fixed-up in PR #30) | Sanctioned. |
| `multitenancy.routers.workspaces` | `iam.middleware` | `AuthenticatedUser`, `get_current_user` (pre-existing) | Per FastAPI norms — auth dependency is a published port, not an ORM coupling. |
| `multitenancy.routers.cells` | `iam.middleware` | same | same |
| `llm_gateway.services.billing_service` | `billing.models` | `CreditTransaction` (pre-existing, sanctioned per HANDOFF.md:123) | Architecturally-sanctioned per llm-gateway invariant #7. **No new cross-context model imports in this PR.** |
| `main.py` | `iam.routers.{auth,me}`, `iam.exceptions` | router includes + exception types | Composition root — expected. |

The graph is acyclic (no `audit → iam` or `multitenancy → iam` service-layer imports — only router-layer auth dependencies, which is the canonical FastAPI shape). The deletion of `_stubs/` does not introduce any cycle.

---

## Summary

The Phase 00.2.5 integration PR delivers exactly what the launch checklist promised: stub deletion, real-impl rewiring, testcontainers session pattern, and an E2E happy-path smoke. The architectural decisions (session-threaded auth service, function-scoped async engine vs session-scoped sync container, type_annotation_map at the Base level, deferring llm_gateway router DI to Phase 00.5) are all sound and well-documented in code.

The single HIGH finding (**H1**) is a real Wave-0-to-prod risk: the E2E test certifies the register flow against a superuser DSN, but production (`oriion_app`, no `BYPASSRLS`) will fail the write-policy check on the workspaces/cells INSERTs. The fix is small (option 1: add `SET LOCAL ROLE oriion_app` to the E2E fixture's `override_get_db` and watch it fail; then choose between SECURITY DEFINER provisioner function or expanded write policy). Strongly recommended to land in 00.2.5 since Phase 00.5 wires multitenancy routers behind real auth — the bootstrap RLS path will be the very first thing exercised under prod credentials.

The four MEDIUM findings are all deferrable to Phase 00.5 or Wave 1 (M1, M3) or are observability hygiene (M2, M4). The five LOW findings are commentary on choices that are already correct.

**Finding count:** 0 BLOCK, 1 HIGH, 4 MEDIUM, 5 LOW = 10 total. Recommend FLAG-resolve H1 before merge; defer the rest.
