# Audit Section 02 — Security Engineer (PR 00.2.5 integration)

**Auditor:** Security Engineer subagent
**Date:** 2026-05-19
**Scope:** PR `claude/heuristic-rhodes-f7a3ef` — 6 commits on top of `main` (`cdde94f..a0e0aed`). Stub→real swap (`src/_stubs/` deleted, `AuthService` now holds `AsyncSession`), session-scoped testcontainers PG fixture, E2E auth-flow integration test, `Base.type_annotation_map` fix, router unit tests.
**Reference:** prior security audit `section-03-security.md` (Phase 00.3+00.4 baseline, 3 High + 9 Medium + 7 Low findings)

---

## Verdict

**FLAG** — no critical block-the-PR vulnerabilities, but **one HIGH-severity tenant-isolation defect** in the new register-time provisioning path that wasn't visible in the prior audit (stub returned synthetic UUIDs; real impl exposes the bug). Plus 5 carry-over MEDIUM findings that this PR materially expands the blast radius of (audit-log now writes real PII to a table without RLS; JWT dev-default secret still ships with no prod-startup gate; testcontainers fixture runs as DB owner so the E2E "validates RLS" docstring is misleading).

Two BLOCK-class findings from the previous audit (H-1 `::uuid` cast → exception, H-2 missing INSERT/UPDATE/DELETE policies on multitenancy.*) appear to have been addressed by intervening commits (`ee507bc fix(rls): split FOR ALL write policy into per-command` and `2bcaef6 fix(rls,audit-log): apply 4 HIGH-severity findings`). H-3 (SSRF DNS-rebinding in `read_url`) is unchanged but out of this PR's scope — `mcp` is not wired into `main.py` yet.

The PR is safe to merge after fixing **S-HIGH-1** (slug-derived workspace cross-tenant linkage) and **S-MED-1** (audit_log RLS gap). The remaining findings should be tracked as Phase 00.5 / Wave-1 issues.

---

## Threat model delta vs prior audit

What changed in this PR:

1. **Audit emission is now persisted.** Pre-PR, `emit_audit_event` (stub) wrote to `structlog` only. Post-PR, it INSERTs into `audit.audit_log` inside the request's outer TX. This is the right architecture, but it expands the data-at-rest surface: PII (email, IP, user-agent) now lives in a partitioned table with **3-year retention** and **no RLS policy**. The append-only trigger + revoked UPDATE/DELETE grants protect against tampering, but not against cross-tenant reads.

2. **`AuthService.session` field is new.** The session is shared between `user_repo.create`, `consent_service.record`, `provision_initial_workspace`, `email_verif_repo.create`, and the new `emit_audit_event(session=self._session)`. This gives clean atomicity (any failure rolls the whole register back, including audit rows), but it also means **a failing audit insert aborts user creation** — which is the desired behaviour only if you treat audit as a write-availability gate. Document this trade-off.

3. **`provision_initial_workspace` is now called on every register.** The Wave-0 stub returned synthetic UUIDs and did nothing. The real impl persists workspace + cell rows AND materializes a per-cell schema via `multitenancy.provision_cell_schema(cell_id)`. Idempotency is on **`workspace.slug`** (not on `user_id`). The slug is derived from `cmd.email.split("@", 1)[0]` — so **two distinct registrations with the same email-localpart silently share a tenant**. See S-HIGH-1.

4. **Testcontainers PG fixture is session-scoped and runs as the `oriion` DB owner.** Production runs as `oriion_app` (FORCE RLS, no BYPASSRLS). The E2E test docstring claims "under real RLS-aware oriion_app credentials" but the fixture never `SET ROLE oriion_app`. Test fidelity gap — see S-MED-3.

---

## Findings by severity

### BLOCK

*None.*

### HIGH

#### S-HIGH-1 — Cross-tenant linkage via email-localpart slug derivation
**File:** `backend/src/iam/services/auth_service.py:152-160` + `backend/src/multitenancy/services/workspace_service.py:160-179`

```python
# auth_service.py:156-160
provision = await provision_initial_workspace(
    session=self._session,
    user_id=user.id,
    email_localpart=cmd.email.split("@", 1)[0],
)
```

```python
# workspace_service.py:160-179
slug = _sanitize_slug(email_localpart)
existing_workspace = await workspace_repo.find_by_slug_active(slug)
if existing_workspace is not None:
    existing_cell = await cell_repo.find_by_workspace_slug(existing_workspace.id, "default")
    if existing_cell is not None:
        ...
        return WorkspaceProvisionResult(
            workspace_id=existing_workspace.id,
            cell_id=existing_cell.id,
        )
```

**Threat model:**
The provisioning idempotency key is `slug = sanitize(email_localpart)`, not `user_id`. Two registrations whose email-localparts sanitize to the same string return the **same** `workspace_id` + `cell_id` to both users, regardless of whether they share an email domain.

| Attacker step | Result |
|---|---|
| 1. Attacker registers `alice@evil.example` | Workspace `alice` + cell `default` created. Attacker is NOT added to `cell_members` (see workspace_service.py:24 docstring) but receives `workspace_id` + `cell_id` in `RegisterResult`. |
| 2. Victim later registers `alice@trusted-corp.com` | `find_by_slug_active("alice")` returns the attacker's workspace. Victim receives the **attacker's** `workspace_id` + `cell_id` in their `RegisterResult`. |
| 3. Victim's frontend stores `active_workspace_id = <attacker workspace>` | Any subsequent `cell_members` INSERT (Phase 00.5 invite-accept flow) bound to this id either fails RLS (best case) or silently grafts the victim into the attacker's tenant (worst case). |

The compensating control is "neither user is added as `cell_member`" — true today, but Phase 00.5 onboarding wizard explicitly enables RBAC assignments, and the launch-checklist for 00.5 lists a `cell_member_invite` flow that takes a `workspace_id` from the client. Slug collision is also an **enumeration oracle**: the attacker can probe whether `slug X` exists by registering `X@throwaway` and observing whether `workspace_id` matches an out-of-band query (a side-channel via the consent_marketing emission timing too).

Slug collision rate is high — `john`, `admin`, `support`, `info`, `sales`, `hello`, `contact` are common localparts AND attractive target slugs.

The docstring at `auth_service.py:151-155` acknowledges the issue ("collision between alice@x and alice@y is a known Wave-1 user-testing risk") but the runtime behaviour is **silent linkage**, not "registration fails with 409" — which is a much more severe contract than "Wave-1 risk".

**Suggested fix (any one of these closes it):**

1. **Make the idempotency key `(user_id, slug)` not just `slug`:** if the existing workspace is found but its sole owner is a different user, append a disambiguator (`alice-2`, `alice-{user_uuid_first_8}`) instead of returning the existing IDs. This requires either tracking workspace ownership (a `created_by_user_id` column — `multitenancy.workspaces` doesn't have one today) or joining via `cell_members` with an "owner" role check.

2. **Reject on collision instead of replaying:** if `find_by_slug_active(slug) is not None`, raise a registration-time error and let the user pick a workspace slug at first-login. This breaks the docstring's "idempotent replay" guarantee but eliminates the cross-tenant linkage.

3. **Use a uniqueness key that's NOT shared across users:** derive slug from `user_id` (`workspace-{user_uuid_first_8}`) instead of email-localpart. The user can rename the slug via PATCH after first login.

4. **At minimum, before the fix lands, log a SECURITY WARNING when the idempotent-replay branch fires from a different `user_id` than originally created the workspace.** Without an `owner` column this requires joining through `cell_members`, but the warning gives a forensic trail.

Note: Option 3 is the smallest change and matches the stub semantics (synthetic per-user IDs). Option 1 is the most correct but adds a column. The current docstring's "1 user → 1 workspace at registration" invariant is not enforced by the schema — `cell_members` does not constrain a user to a single workspace, and `workspaces` has no `created_by_user_id` FK to any user table.

---

### MEDIUM

#### S-MED-1 — `audit.audit_log` has no RLS policies; cross-tenant PII reads possible from any role with SELECT
**Files:**
- `backend/migrations/versions/audit/0001_audit_log_partitioned.py:1-167` (no `ENABLE ROW LEVEL SECURITY`, no `CREATE POLICY`)
- `backend/src/iam/services/auth_service.py:190` (writes `email` into `payload` JSONB)
- `backend/src/multitenancy/services/cell_service.py:196` (writes `email` into `payload` JSONB)
- `backend/src/audit/repositories/audit_repository.py:62-97` (`list_by_actor`, `list_by_resource` — no tenant filter)

**Threat model:**
Every other tenant-scoped table in this PR (`multitenancy.*`, `rbac.role_assignments`, `llm_gateway.byok_keys`, `llm_gateway.llm_usage_log`, `billing.credit_transactions`, `mcp.mcp_connections`) has `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + tenant-isolation policies. `audit.audit_log` does not — defense relies entirely on `GRANT SELECT, INSERT` to `oriion_app` (line 163). Every row stores `actor_id`, `cell_id`, `workspace_id`, `ip` (inet), `user_agent` (text), and `payload` (jsonb which today contains `{"email": user.email, ...}` for `iam.user.registered` and `iam.consent.granted`).

The append-only trigger protects integrity (no UPDATE / DELETE), but **anything with `SELECT` on `audit.audit_log` reads ALL tenants' rows**. The `AuditRepository.list_by_actor` / `list_by_resource` methods take no tenant filter — they return rows for any `actor_id` / `resource_id` the caller passes. When Phase 00.5 ships a `/api/v1/audit/events` endpoint backed by these repo methods (which is the natural progression — both methods exist, neither is currently called), an authenticated user from tenant A can query for tenant B's `resource_id` and read tenant B's emails / IPs.

FZ-152 implication: `email` and `ip` are personal data. The audit log is exempt from short retention because of legitimate interest (security forensics), but **the access-control model required to maintain that exemption is "least privilege" — meaning per-tenant SELECT, not cross-tenant SELECT**.

**Suggested fix:**

```sql
ALTER TABLE audit.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.audit_log FORCE  ROW LEVEL SECURITY;

CREATE POLICY audit_log_workspace_isolation ON audit.audit_log
    FOR SELECT
    USING (
        workspace_id IS NULL  -- system events (cross-tenant) only visible to BYPASSRLS
        OR workspace_id = _shared.current_workspace_id()
    );

-- INSERT policy mirrors the SELECT contract: caller must own the workspace OR
-- be a system actor (workspace_id IS NULL).
CREATE POLICY audit_log_insert_with_context ON audit.audit_log
    FOR INSERT
    WITH CHECK (
        workspace_id IS NULL
        OR workspace_id = _shared.current_workspace_id()
    );
```

Apply the same policy to every monthly partition (Postgres does NOT inherit table-level RLS to partitions automatically) — same pattern as the GRANT block on lines 164-166. Add this to the maintenance job for new partitions.

Defense-in-depth: stop writing raw `email` into `payload`. Replace `payload={"email": user.email, "workspace_id": ...}` with `payload={"workspace_id": ...}` and rely on `actor_id` → `iam.users.email` join when forensics needs the email. Same for `cell_service.py:196`.

---

#### S-MED-2 — JWT dev-default secret has no prod-startup refusal
**File:** `backend/src/_shared/config.py:51-54`, prior audit M-1 — **unresolved in this PR**

```python
jwt_secret_access_v1: SecretStr = Field(
    default=SecretStr("changeme-dev-only-please-replace-in-prod-min-32-chars"),
    ...
)
```

The PR materially expands the blast radius: pre-PR, `register` was the only auth surface that issued tokens; post-PR, the full lifecycle (register, login, refresh, logout) runs through the real session pool. The `TokenService` reads the secret via `get_secret_value()` and uses it for HS256 signing (token_service.py:79, 92). If a deploy ships with `APP_ENV=prod` and the unchanged default, **every issued access token is forgeable from public knowledge** (the literal string is in this repo).

**Suggested fix:** add a Pydantic `model_validator(mode='after')` to `Settings`:

```python
@model_validator(mode='after')
def _refuse_dev_defaults_in_prod(self) -> Self:
    if self.app_env in ("prod", "staging"):
        if self.jwt_secret_access_v1.get_secret_value() == (
            "changeme-dev-only-please-replace-in-prod-min-32-chars"
        ):
            raise ValueError(
                "JWT_SECRET_ACCESS_V1 must be overridden in prod/staging "
                "(currently set to the dev default literal)."
            )
        if (
            self.kms_backend == "local"
            and not self.byok_master_key_b64.get_secret_value()
        ):
            raise ValueError(
                "BYOK_MASTER_KEY_B64 must be set when KMS_BACKEND=local "
                "(currently empty). Use Yandex KMS in prod or generate via "
                "`openssl rand -base64 32`."
            )
    return self
```

Same validation should reject `consent_version_current == "2026-05-17"` (the dev default) in prod, since consent is FZ-152-required to be pinned at a public published version.

---

#### S-MED-3 — Testcontainers E2E fixture runs as DB owner; "RLS-aware" docstring is false
**Files:**
- `backend/tests/conftest.py:96-101` (container started as `oriion` superuser)
- `backend/tests/integration/test_e2e_auth_flow.py:11` (claim: "real RLS-aware oriion_app credentials")

The testcontainers `PostgresContainer(username="oriion", password="oriion-dev", ...)` boots PG with `oriion` as the superuser AND the owner of every table created by alembic. `oriion` is exempted from FORCE RLS by virtue of being the owner only when `FORCE ROW LEVEL SECURITY` is OFF — but the migrations correctly set `FORCE`, so `oriion` IS subject to policies in principle. However: in this PR no policy denies `oriion` because the policies use `_shared.current_workspace_id()` and the test fixture never calls `set_tenant_context(...)`. The `multitenancy.cell_members` test at `tests/multitenancy/test_rls_isolation.py:96` correctly does `SET LOCAL ROLE oriion_app` — the new E2E test does not.

Implication: The E2E test demonstrates that the **happy path** works end-to-end against real PG, but does not demonstrate that **RLS isolation holds for the auth flow**. The launch checklist's "real RLS-aware oriion_app credentials" claim should be either (a) honored by adding `SET LOCAL ROLE oriion_app` in `override_get_db`, or (b) the docstring should be corrected to "real DB-owner credentials".

**Suggested fix:**

In `test_e2e_auth_flow.py::app::override_get_db`:

```python
async def override_get_db() -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        # Mirror prod posture — handler runs as oriion_app, not the DB owner.
        await session.execute(text("SET LOCAL ROLE oriion_app"))
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
```

This will cause some assertions to fail (because the post-handler `assertion_session` then can't read rows under RLS unless GUCs are set), at which point you'll see how thin the current "E2E" coverage actually is. That's the point — surfacing the gap before Phase 00.5 wires more handlers.

---

#### S-MED-4 — `os.environ["DATABASE_URL"]` mutation in `_alembic_upgrade_heads` is process-global; race-unsafe under future xdist
**File:** `backend/tests/conftest.py:177-213`

```python
prev = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = async_url
try:
    ...
    command.upgrade(cfg, "heads")
finally:
    if prev is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = prev
```

`pyproject.toml` does not pull in `pytest-xdist`, so this is single-process today and the `finally` block correctly restores. But: (a) any future move to `pytest -n auto` for CI speedup will introduce a TOCTOU on `DATABASE_URL` where the alembic upgrade in one worker overwrites the env-var while another worker is reading it; (b) the env-var leaks to any subprocess `command.upgrade` spawns (alembic uses `async_engine_from_config` which doesn't, but a future env.py rewrite that does will inherit a possibly-wrong DSN); and (c) more importantly, **CI sets `DATABASE_URL` to the GitHub-services container DSN at job-level** (workflow line 60), and this fixture transiently overwrites it — for the duration of alembic, the value is the testcontainers DSN. If another fixture reads `DATABASE_URL` during that window (e.g. a side-effecting import chain reading config at fixture init), it sees the wrong URL.

**Suggested fix:** pass the URL into alembic via `cfg.set_main_option("sqlalchemy.url", async_url)` and patch `env.py` to prefer the config-passed URL over `os.environ`. Then drop the env-mutation entirely. Workflow line 60's `DATABASE_URL` doesn't need to be globally mutated.

Alternatively, document explicitly that the fixture is single-process-only and add a runtime assertion: `assert not os.environ.get("PYTEST_XDIST_WORKER"), "fixture is xdist-unsafe — see S-MED-4"`.

---

#### S-MED-5 — `MultitenancyError` exception handler is NOT registered in production `main.py`
**Files:**
- `backend/src/main.py:34-80` (only registers `IamError` handler)
- `backend/tests/multitenancy/test_workspaces_router.py:36-44` (test-only `_install_multitenancy_handler`)

The test mini-app pattern reinstalls the handler:

```python
# test_workspaces_router.py:36
def _install_multitenancy_handler(app: FastAPI) -> None:
    @app.exception_handler(MultitenancyError)
    async def _h(request: Request, exc: MultitenancyError) -> JSONResponse:
        body = {"code": exc.code, "title": exc.title, "status": exc.status_code}
        if exc.detail:
            body["detail"] = exc.detail
        return JSONResponse(status_code=exc.status_code, content=body)
```

…but `main.py` does NOT include the multitenancy router and does NOT register this handler. So today nothing leaks. The risk is **Phase 00.5 timing**: when 00.5 wires `multitenancy.routers.workspaces` (and `cells`) into `main.py`, the dev who does the wiring MUST also port `_install_multitenancy_handler`. Without it, every `MultitenancyError` (e.g. `WorkspaceNotFound`, `CellProvisioningError`, `WorkspaceSlugConflict`) bubbles to the default FastAPI 500 handler with a full stack trace in `app.debug=True` and a generic 500 in prod — **either reveals internal class names + DB error fragments** (DB constraint violation messages from PG include the constraint name and the offending values).

**Suggested fix (do in this PR, before 00.5):** move the handler from the test mini-app into `main.py` next to `iam_error_handler`. The handler is pure error-class introspection — registering it before its routers are wired is harmless. Same for `AuditError`, `LlmGatewayError`, `McpError`, `BillingError`, `RbacError` if they exist (sweep for `class *Error(BaseException)` patterns).

```python
# main.py — add alongside iam_error_handler
@app.exception_handler(MultitenancyError)
async def multitenancy_error_handler(request: Request, exc: MultitenancyError) -> JSONResponse:
    body = {
        "type": f"https://oriion.app/errors/{exc.code.replace('.', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "code": exc.code,
    }
    if exc.detail:
        body["detail"] = exc.detail
    body["instance"] = str(request.url)
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )
```

---

### LOW

#### S-LOW-1 — Audit failure can abort user creation (TX-atomicity is desired but the contract isn't documented)
**File:** `backend/src/iam/services/auth_service.py:184-196`

`emit_audit_event(session=self._session, ...)` runs `session.add(row); session.flush()` inside the request's outer TX. If the audit insert raises (e.g. `audit.audit_log_2026_05` partition is missing because the maintenance job lapsed and the DEFAULT partition is full / has different ACL), **the user row is rolled back**. The user gets a 500, the workspace is rolled back, the verification email is NOT sent (it runs before audit in `register()`, so it MIGHT have been queued — see L-2 below).

This is the right atomicity contract for compliance auditing — if you can't audit it, it didn't happen — but it's not documented in the docstring as a deliberate trade-off. A future maintainer "fixing" the 500-rate metric might wrap audit_event in `try/except` and silently break compliance.

**Suggested fix:** add a comment block at `auth_service.py:78-99` documenting "audit emission is on the happy-path TX deliberately — if audit_log writes fail, the entire register MUST fail. Do not wrap in try/except." Or, better, add an `AuditWriteRequired` exception class and assert it propagates in tests.

---

#### S-LOW-2 — Email send (`send_verification_email`) runs BEFORE audit insert; partial-failure leaks an email to a never-registered user
**File:** `backend/src/iam/services/auth_service.py:169-196`

Order: `_email_sender.send_verification_email(...)` → `emit_audit_event(...)`. If the audit insert fails after the email has been queued, the user receives a verification email pointing at a `user_id` that no longer exists (rolled back). Token lookup will 404 on verify-email, no DB row remains. Worst case: email send is via a real SMTP provider; the rolled-back user `user.id` is recycled at the next `gen_random_uuid()` (collision probability ≈ 0, but the user-facing UX is "email arrived from a service I can't log into").

**Suggested fix:** reorder so `send_verification_email` happens AFTER the audit + token rows commit. Or, more correctly, use the outbox pattern: enqueue the email-send into an `outbox_events` table inside the TX, and a separate worker delivers AFTER commit. The outbox table doesn't exist yet (Phase 00.6?), so the interim fix is just reordering.

---

#### S-LOW-3 — `Base.type_annotation_map` change is global — any model wanting TIMESTAMP WITHOUT TIME ZONE must explicitly override
**File:** `backend/src/_shared/db/base.py:30-32`

```python
type_annotation_map: ClassVar[dict[type, DateTime]] = {
    datetime: DateTime(timezone=True),
}
```

Sweep results (grep for `mapped_column(DateTime`): **zero** models explicitly override. All migrations create `timestamptz`. So the change is consistent with current DDL. The risk is forward-only: if a future bounded context (e.g. an analytics partition that legitimately wants naive timestamps for query simplicity) adds `Mapped[datetime]` without realizing the global default is `timezone=True`, they'll get a silent timezone-aware column. Document this in the docstring as "global default — to opt out, use `Mapped[datetime] = mapped_column(DateTime(timezone=False), ...)`".

---

#### S-LOW-4 — Test fixture hardcodes `byok_master_key_b64="MDEy...ZWY="` literal (32-byte `0123456789abcdef0123456789abcdef`)
**File:** `backend/tests/integration/test_e2e_auth_flow.py:105`

Distinct from the CI workflow's generated `ci-test-master-key-for-dev-only!`. Both are low-entropy non-secrets that gitleaks may flag (`.gitleaksignore` has 16 entries — verify this literal is covered). The test key never escapes the test process and decrypts only test-ciphertext, so no real-secret exposure. Low because: (a) the value is publicly known cryptographic test material (the literal `0123456789abcdef` is in countless test suites), (b) the BYOK flow isn't exercised by this E2E test (LLM routers return 404 — line 425-454), and (c) the `.gitleaksignore` was extended in commit `92067b5` to whitelist the existing pattern.

**Suggested fix:** mark the test key with a comment line directly above: `# noqa: gitleaks — non-secret test fixture, 0x0..ef bytes`. Verify `.gitleaksignore` covers this specific literal.

---

#### S-LOW-5 — `db_session_committed.TRUNCATE` cleanup hits partition children individually; could fire on partitions added post-deployment
**File:** `backend/tests/conftest.py:298-315`

The cleanup query is:

```sql
SELECT schemaname || '.' || tablename
  FROM pg_tables
 WHERE schemaname IN ('iam','multitenancy','rbac','audit','llm_gateway','billing','mcp')
   AND tablename NOT LIKE 'alembic_%'
```

This includes both `audit.audit_log` (parent) AND `audit.audit_log_2026_05` / `audit.audit_log_default` (partitions). Listing partitions alongside the parent is benign (TRUNCATE on parent cascades to all attached partitions; running it again on a child is a no-op-after-empty), but **a future per-cell schema (`cell_<uuid>.memory_entries`)** materialized by `multitenancy.provision_cell_schema()` won't match `schemaname IN (...)` and will accumulate across tests. This isn't a security issue per se, but the next maintainer who adds a per-cell test will find inexplicable test bleed.

**Suggested fix:** extend the schema filter to include schemas matching `cell_*` via `pg_namespace.nspname LIKE 'cell\_%' ESCAPE '\\'`. Or, simpler, build the schema list at runtime by reading `multitenancy.cells.id` and constructing the schema names. Track as a Wave-1 issue — not blocking this PR.

---

## Verification recommendations for Phase 00.5

Before 00.5 lands the LLM / multitenancy / MCP routers in `main.py`, these tests must pass:

1. **S-HIGH-1 regression:** register two users with email-localpart collision; assert their `workspace_id` differs.
2. **S-MED-1 regression:** as `oriion_app` (after `SET LOCAL ROLE`), `SELECT * FROM audit.audit_log WHERE workspace_id = '<other-tenant-id>'` returns zero rows; same query without `set_tenant_context` returns zero rows (default-deny).
3. **S-MED-2 regression:** start the app with `APP_ENV=prod` and unchanged `JWT_SECRET_ACCESS_V1` → assert startup fails with `ValidationError`. Same for `BYOK_MASTER_KEY_B64=""` + `KMS_BACKEND=local`.
4. **S-MED-3 regression:** modify `override_get_db` to `SET LOCAL ROLE oriion_app`; assert the existing E2E still passes (failure means the auth flow isn't actually RLS-tested today).
5. **S-MED-5 regression:** before any multitenancy router is wired into `main.py`, `MultitenancyError` exception handler is registered. Test: instantiate `production_app` with multitenancy router included, raise `WorkspaceNotFound` in a route, assert response body matches the test mini-app's contract.

---

## Summary

The stub→real swap is architecturally correct and the new E2E test surfaces real integration risk that the unit suite couldn't see — these are good things. The audit_repository is correctly minimal (no UPDATE/DELETE methods), the append-only triggers are inherited to partitions, the AuthService.session field gives clean TX atomicity, and the prior audit's H-1 / H-2 / part of M-7 appear to have been addressed in intervening commits.

The one HIGH finding (S-HIGH-1) is a real bug introduced by this PR — it wasn't visible in the prior audit because the Wave-0 stub returned synthetic UUIDs. The MEDIUM findings are all "this PR materially expands the consequence" of pre-existing gaps: audit_log gains real PII writes (S-MED-1), JWT secret protects more endpoints (S-MED-2), the E2E test's RLS claim is false (S-MED-3), the conftest env mutation becomes more important when 00.5 adds parallel-test load (S-MED-4), and the missing exception handler becomes a 00.5 wiring trap (S-MED-5).

**Recommended PR action: FLAG.** Merge after S-HIGH-1 is fixed in this PR (3-line change to slug derivation OR a new column on `multitenancy.workspaces`). Track S-MED-1 through S-MED-5 as Phase 00.5 blockers — they are not exploitable today because the affected routers (multitenancy, llm_gateway, mcp) are not wired into `main.py`, but each becomes exploitable the moment they are.

Files referenced (absolute paths):

- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\iam\services\auth_service.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\multitenancy\services\workspace_service.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\multitenancy\repositories\workspace_repository.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\audit\services\audit_service.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\audit\repositories\audit_repository.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\migrations\versions\audit\0001_audit_log_partitioned.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\_shared\config.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\_shared\db\base.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\main.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\src\iam\services\consent_service.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\tests\conftest.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\tests\integration\test_e2e_auth_flow.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\backend\tests\multitenancy\test_workspaces_router.py`
- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.github\workflows\ci-backend.yml`
