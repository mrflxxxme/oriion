# AUDIT REPORT — Phase 00.2.5 integration PR

> Consolidated 5-agent independent audit of branch
> `claude/heuristic-rhodes-f7a3ef` (7 commits ahead of `main`),
> executed 2026-05-19 per the Phase 00.2.5 launch checklist §Step 7.

## Top-level verdict: **PASS-WITH-FIXES**

| Section | Auditor | Verdict | Critical / High / Med / Low |
|---|---|---|---|
| 01 Code review | Code Reviewer | **FLAG → PASS** after fix | 0 / 1 / 4 / 5 |
| 02 Security | Security Engineer | **FLAG** (1 deferred) | 0 / 1 / 5 / 5 |
| 03 Test adequacy | Test Results Analyzer | **FLAG → PASS** after fix | 0 / 2 / 5 / 7 |
| 04 Architecture | Backend Architect | **FLAG** (1 deferred) | 0 / 1 / 4 / 5 |
| 05 Compliance | Compliance Auditor | **PASS** | 0 / 0 / 0 / 3 |

Total BLOCK-class findings: **0**.
Total HIGH findings: **6 distinct issues across 5 sections** (Code-Reviewer H-1 + Test F-01 are the same bug counted once → 4 unique issues).
HIGH findings **fixed in-loop**: **2** (E2E cleanup, llm_gateway coverage margin).
HIGH findings **deferred**: **2** (slug-based cross-tenant linkage, RLS-on-register requires superuser) — both have explicit follow-up tracking in HANDOFF.md + this report.

## Caveat — Section 01 delivered (vs PR #30)

The PR #30 audit's Section 01 (Code Reviewer) paused mid-run and was
not delivered. This audit explicitly required + delivered it. Report at
`.planning/_session-context/AUDIT-2026-05-19-PR-00-2-5/section-01-code-review.md`.

## Fixes applied during this audit cycle

### F-1 (Code Reviewer H-1 + Test F-01) — E2E test isolation

**Issue:** `tests/integration/test_e2e_auth_flow.py` was marked
`commit_required` but no test consumed the `db_session_committed`
fixture, so TRUNCATE cleanup never fired. The 5 E2E tests accumulated
audit_log rows across each other within a single pytest session; the
`count == 1` assertions only passed because of pytest's deterministic
file-order collection. Under `pytest-randomly`, `-k` filtering, or a
repeat-on-fail loop, the assertion would have failed.

**Fix applied:**
1. Added `db_session_committed: AsyncSession` to the `app` fixture
   signature so its teardown TRUNCATE actually runs (commit 7).
2. Made `_count_audit_rows` accept an `actor_id` kwarg and scoped
   every count assertion in the suite to the test's specific user_id
   for defence-in-depth.
3. Excluded `rbac.{permissions, system_roles, role_permissions}` from
   the TRUNCATE filter — they're seed data populated by
   `migrations/versions/rbac/0005_seed_built_in_roles.py` and the
   `test_seed_data.py` integration tests + cross-context FKs from
   `cell_members.role_id` depend on them. Without the exclusion the 5
   E2E tests would TRUNCATE the seed and break 5 unrelated integration
   tests when run in the same session.

**Verification:** `uv run pytest tests/ -q -m integration` →
**21/21 pass** (was: 16 pre-fix, 21 with H-1 reverted on a fresh
container, 16 on a re-run).

### F-2 (Test F-02) — llm_gateway coverage margin

**Issue:** Per-module coverage at 85.70 % unit-only — only 0.70 pp
above the new uniform ≥85 % gate. Provider HTTP-layer paths in
`yandex.py` + `gigachat.py` were uncovered. The next provider
refactor would red CI.

**Fix applied:** New file `tests/llm_gateway/test_provider_health_checks.py`
(4 tests using respx) covering yandex + gigachat health_check
reachable + ConnectError branches.

**Verification:** `uv run pytest tests/llm_gateway --cov=src/llm_gateway
--cov-fail-under=85 -q -m "not live and not integration"` → **88.22 %
coverage** (margin +3.22 pp; comfortable buffer for the next refactor).

### F-3 (Code Reviewer M-1) — logout actor_id

**Issue:** `AuthService.logout` emitted audit row with
`actor_id=UUID(int=0)` despite `session_repo.find_by_id(row.session_id)`
giving the real user_id — internally contradictory
(`actor_type="user"` + zero UUID).

**Fix applied:** `auth_service.logout` now looks up `session.user_id`
**before** the revoke + uses that as the audit `actor_id`. Falls back
to `UUID(int=0)` only if the session row is missing (defensive — the
refresh-token row already proves it exists at this point).

**Verification:** E2E test assertion updated to expect
`actor_id=user_id` (real); test passes.

### F-4 (Code Reviewer M-4) — archive_cell workspace_id snapshot

**Issue:** `cell_service.archive_cell` read `cell.workspace_id` after
the archive UPDATE — fine today, but fragile under future ORM-state
changes.

**Fix applied:** Snapshot `cell_workspace_id = cell.workspace_id`
**before** the archive call, pass the snapshot to the audit emit.

## Findings deferred to Phase 00.5 / Wave 1

### H-DEFER-1 (Security S-HIGH-1) — slug-based cross-tenant linkage

**File:** `src/multitenancy/services/workspace_service.py:160-179`

**Issue:** Real `provision_initial_workspace` is idempotent on
`slug = _sanitize_slug(email_localpart)`, NOT on `user_id`. So
`alice@example.com` registers → workspace slug `alice`. Then
`alice@evil.com` registers → same slug → idempotency path returns the
EXISTING workspace_id + cell_id belonging to the first alice.

**Why deferred:** Founder grilled this at Round 2 Q6 and explicitly
accepted "Naive `cmd.email.split("@",1)[0]` + trust idempotency-on-slug
in real `provision_initial_workspace`" as Wave-0 acceptable
("alice@x.com and alice@y.com would land in same workspace — Wave-1
user-testing risk"). The Security audit reframes the same behaviour as
silent cross-tenant linkage rather than user-testing inconvenience.

**Mitigation:** Documented as known Wave-0 issue in:
* `src/iam/services/auth_service.py:151-155` (comment on the call site)
* `HANDOFF.md` "Known caveats" section
* This audit report

**Wave-1 fix candidates:**
1. Append a `uuid4().hex[:6]` suffix to the slug on collision
2. Raise `WorkspaceSlugConflict` instead of returning existing
3. Per-user provisioning UUID key inside `provision_initial_workspace`

**Tracking:** Add to Wave-1 backlog in `roadmap/wave-1-core/`.

### H-DEFER-2 (Architecture H1) — RLS-on-register requires superuser

**Files:**
* `src/multitenancy/services/workspace_service.py:181-194`
* `migrations/versions/multitenancy/0003_cell_members.py` (write policies)
* `tests/integration/test_e2e_auth_flow.py:122-126` (fixture connects
  as DB owner, not oriion_app)

**Issue:** `register()` writes to `multitenancy.{workspaces, cells,
cell_members}` which all have `FORCE ROW LEVEL SECURITY` with INSERT
policies gated on `_shared.current_user_id() IS NOT NULL`. At
registration time there's no user context yet (the user row was just
created); `current_setting('app.current_user_id', true)` is empty;
`_shared.current_user_id()` returns NULL; the INSERT is denied by RLS
unless the connecting role bypasses RLS. **testcontainers connects as
`oriion` (DB owner, bypasses FORCE RLS), so the E2E suite passes.
Production connects as `oriion_app` (NOLOGIN role per PR #27), which
does NOT bypass — the production `register()` flow will fail RLS
gate.**

**Why deferred:** The fix has 3 reasonable shapes (SECURITY DEFINER
function for the bootstrap path; loosen INSERT policy to allow
unauthenticated tenant creation; set tenant context to the
just-created user_id before the writes). Each is a non-trivial
architecture decision that should land with Phase 00.5's main.py
wiring of multitenancy routes — at which point all 3 paths can be
considered together against the routing layer's RLS-context middleware
design.

**Mitigation:** Test fixture sets DATABASE_URL to the
testcontainers-issued `oriion` superuser DSN, so the test does not
mask the issue from a security review (this audit caught it) — it
masks the issue from CI as an unintended side-effect. Phase 00.5 will
**either** add `SET LOCAL ROLE oriion_app` in the test's
`override_get_db` (forcing the test to surface the prod failure) or
restructure the bootstrap path to make register-as-oriion_app work.

**Tracking:** This is now Phase 00.5's first acceptance criterion
(documented in HANDOFF.md "Founder action" block — add to the brief
that Phase 00.5 must replace `override_get_db` with `SET LOCAL ROLE
oriion_app` AND make register work under that role).

### Other deferrals

**M-DEFER-1 (Code Reviewer M-2) — Audit assertion absent in unit
tests**: `tests/iam/unit/conftest.py` autouse-patches
`emit_audit_event` to a bare `AsyncMock()`, so unit tests cannot
verify audit emits actually happen. Future refactor that drops one
emit call passes silently. **Mitigation**: the E2E suite asserts on
`audit_log` row counts per action; that's the regression net. Phase
00.5 can tighten unit tests with `AsyncMock(spec=emit_audit_event)`
+ `.assert_awaited` checks.

**M-DEFER-2 (Code Reviewer M-3) — `change_role` + `remove_member`
omit workspace_id from audit emits**: Cheap to fix (`cell_repo.find_by_id`
lookup) but adds 1 DB round-trip per call. Acceptable defer to Wave 1.

**M-DEFER-3 (Security S-MED-1) — `audit.audit_log` has no RLS**:
Intentional (per Architecture audit Q6 finding — audit_log is a
cross-tenant compliance artefact by design, append-only via trigger
+ retention partitioning per ADR-014 amendment 2026-05-19). NOT a
defect; documented here so future review doesn't re-raise it.

**M-DEFER-4 (Security S-MED-2) — JWT dev-default secret in Settings**:
Pre-existing Phase 00.2 issue. Wave-1 hardening adds a prod-startup
validator that refuses to boot if `jwt_secret_access_v1` equals the
default `changeme-*` literal.

**M-DEFER-5 (Security S-MED-3) — E2E fixture docstring claims
"oriion_app credentials"**: Couples to H-DEFER-2 fix; both land
together in Phase 00.5.

**M-DEFER-6 (Security S-MED-4) — `os.environ["DATABASE_URL"]`
mutation in `_alembic_upgrade_heads`**: Not xdist-safe. Wave 1 swaps
to `alembic.config.Config` instance-scoped env injection.

**M-DEFER-7 (Security S-MED-5) — `MultitenancyError` handler not
registered in production main.py**: Phase 00.5 wiring task; the test
mini-app already shows the shape (`tests/multitenancy/test_workspaces_router.py:_install_multitenancy_handler`).

**M-DEFER-8 (Architecture M2-M4)** + **L1-L5 across all sections** —
collected in section reports; all non-blocking.

**L-DEFER-9 (Compliance L1) — 6 stale `src/_stubs/` references in
source docstrings**: `workspace_service.py:4-5,55`,
`audit/__init__.py:9`, `audit/services/__init__.py:6`,
`audit/services/audit_service.py:4-30,185-186`. Single follow-up
docs commit before or after PR merge; non-blocking.

**L-DEFER-10/11 (Compliance L2/L3) — `OPEN-QUESTIONS.md:11,66` OQ-04
deadline phrasing "До Phase 00.2"**: Now historical (Phase 00.2 long
shipped). Cosmetic.

## Audit verdicts after fixes

| Section | Pre-fix verdict | Post-fix verdict |
|---|---|---|
| 01 Code review | FLAG (1 High, 4 Med) | **PASS** (H-1 fixed; M-1 + M-4 fixed; M-2 + M-3 deferred Wave-1) |
| 02 Compliance | PASS | **PASS** (no fixes needed; 3 L doc drift deferred) |
| 03 Security | FLAG (1 High, 5 Med) | **FLAG** (S-HIGH-1 sanctioned by founder grill Q6 + documented) |
| 04 Test adequacy | FLAG (2 High) | **PASS** (F-01 fixed; F-02 fixed) |
| 05 Architecture | FLAG (1 High, 4 Med) | **FLAG** (H1 deferred Phase 00.5 with explicit Phase-05 AC pin) |

**Net:** all merge-blocking findings are either fixed in-loop or
explicitly deferred with named tracking (Phase 00.5 / Wave 1). No
regressions introduced (full unit + integration suite re-run after
fixes: 370 unit pass, 21 integration pass).

## Test re-run after fixes

```
uv run ruff check src tests                       → All checks passed
uv run ruff format --check src tests              → 180 files unchanged
uv run mypy --strict src                          → Success on 100 source files
uv run bandit -r src -c pyproject.toml            → 0/0/0
uv run pytest tests/ -q                           → 370 passed, 21 deselected
uv run pytest tests/ -q -m integration            → 21 passed, 370 deselected
uv run pytest tests/<MOD> --cov=src/<MOD> --cov-fail-under=85 -q
                                                  → iam 86.74, multi 88.39,
                                                    rbac 100, audit 100,
                                                    llm_gateway 88.22, mcp 92.98
```

## References

- Sections 01-05 in this directory (`section-01-code-review.md` etc.)
- Plan: `C:\Users\KUklonskiy\.claude\plans\phase-00-2-5-integration-squishy-llama.md`
- Phase 00.2.5 launch checklist:
  `.planning/_session-context/PHASE-00-2-5-LAUNCH-CHECKLIST.md`
- Post-merge consistency audit (basis for this PR):
  `.planning/_session-context/POST-MERGE-AUDIT-2026-05-19.md`
- Prior PR #30 audit:
  `.planning/_session-context/AUDIT-2026-05-19/AUDIT-REPORT.md`
