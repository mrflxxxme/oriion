# Section 02 — Architecture audit (cumulative pre-Phase-00.5)

**Auditor:** Backend Architect (sub-agent)
**Date:** 2026-05-19
**Scope:** Cumulative Wave-0 architecture state on branch `claude/pre-phase-05-audit`
(off `main` at merge-commit `20451e0`, post-PR-#32 merge — equivalent to head
of `claude/heuristic-rhodes-f7a3ef` worktree). Covers Phases 00.1 → 00.2 →
00.3 → 00.4 → 00.2.5 combined.
**Method:** Read-only inspection of `backend/src/`, `backend/migrations/`,
`backend/src/main.py`, plus the four prior audit reports (`AUDIT-2026-05-19/`,
`AUDIT-2026-05-19-PR-00-2-5/`, `POST-MERGE-AUDIT-2026-05-19.md`,
`PHASE-00-2-5-LAUNCH-CHECKLIST.md`) and the planning trio
(`HANDOFF.md`, `STATUS.md`, `JOURNAL.md`).

---

## Top-level verdict: **FLAG**

The cumulative architecture is **structurally sound** and the major prior
findings have either been fixed in-loop or escalated into explicit
Phase 00.5 / Wave 1 backlog items. The bounded-context graph (12 contexts
in 6 implemented + 6 deferred) is acyclic; the migration DAG is clean with
seven branches converging on `_shared_0002_current_user_id_helper`; the
atomic 3-currency write contract is intact; the cost-ledger pair
(`llm_usage_log` + `credit_transactions`) is now uniformly append-only
via triggers + revoked UPDATE/DELETE grants; `audit.audit_log` is correctly
RANGE-partitioned with seed partitions + a DEFAULT catch-all; the 3-GUC
RLS posture has helper-function adoption across all six write contexts;
provider failover + circuit-breaker semantics in `LLMRouter` are correct.

**However, three architecturally significant gaps remain open at the
Phase 00.5 gate:**

1. **H1 (carried over from PR #32 audit, intentionally deferred).** The
   register() bootstrap path inserts into `multitenancy.{workspaces, cells,
   cell_members}` with no tenant GUC and no SECURITY DEFINER escape hatch.
   The E2E tests pass only because testcontainers connects as the
   cluster superuser (which bypasses FORCE RLS); production
   (`oriion_app`, no BYPASSRLS) will fail the INSERT WITH CHECK on the
   first registration. **This is Phase 00.5's first AC** per HANDOFF.md;
   it MUST land before multitenancy/llm-gateway/mcp routers are wired
   under real auth.

2. **H2 (new finding — discovered during this audit).** `set_tenant_context`
   is defined in `src/_shared/db/rls.py` but is **not called from a single
   production source file** outside its own docstring example. The 3-GUC
   model exists at the database layer (all six tenant-scoped tables FORCE
   RLS + reference `_shared.current_*_id()` helpers), but the application
   layer never sets the GUCs. This is symptomatic of the iam-only routing
   surface in main.py — no router that needs tenant scoping is wired yet —
   but it means the 3-GUC contract has zero production-code regression
   coverage. Phase 00.5 must wire a request-scope middleware (or per-router
   dependency) that calls `set_tenant_context` before any RLS-protected
   query.

3. **H3 (carried over, sanctioned).** `llm_gateway.billing_service`
   directly imports `src.billing.models.CreditTransaction` (ADR-024 §2
   cross-context model import). Sanctioned per HANDOFF.md:123 as the price
   of atomic 3-currency write integrity; the ADR-024 amendment (A-12 from
   POST-MERGE-AUDIT) has not been authored yet. Adding a 3-line amendment
   note to ADR-024 would close the doc gap without any code change.

The 5 **MEDIUM** findings are all observability or hygiene gaps that are
non-blocking; 6 **LOW** items are commentary on choices that are already
correct.

**Phase 00.5 readiness rating: 4 / 5** (one architectural blocker — H1 —
that Phase 00.5 is explicitly chartered to resolve; the rest is wiring
work with clean DI extension points).

---

## Architectural invariants matrix

| # | Invariant | Source | Status | Evidence |
|---|---|---|---|---|
| 1 | 12 bounded contexts; 6 implemented (`iam`, `multitenancy`, `rbac`, `audit`, `llm_gateway`, `mcp`) + 1 skeleton (`billing`) | ADR-024 §1 | ✅ PASS | `backend/src/{iam,multitenancy,rbac,audit,llm_gateway,mcp,billing,_shared}/` all present; `agents/tasks/artifacts/memory` deferred to Wave 1+ as expected |
| 2 | Cross-context source imports go through `services.<thing>` or `models`, not into repositories.* or internal modules | ADR-024 §2 | ✅ PASS | Inventory below shows 6 sanctioned cross-context edges; zero illicit reaches into `repositories.*` from another context |
| 3 | Single sanctioned cross-context model import: `llm_gateway.billing_service → src.billing.models.CreditTransaction` | HANDOFF.md:123 | ⚠️ PASS-WITH-DEBT | Confirmed sole exception (see Section "Cross-context import graph"); ADR-024 amendment to formalize the carve-out is unwritten (A-12 from POST-MERGE-AUDIT) |
| 4 | Audit context is a leaf — no `audit → *` imports | ADR-024 §1 | ✅ PASS | `src/audit/services/audit_service.py` imports only `_shared.cloudevents` + own repository |
| 5 | 3-GUC layered RLS via `app.current_user_id` / `_workspace_id` / `_cell_id` | ADR-009 amendment 2026-05-19 | ⚠️ PARTIAL | DB-layer correct (helpers in `_shared/0002_current_user_id_helper.py`; all six write-context policies use the helpers, no inline `::uuid` casts remain after the 2026-05-19 Security audit H-1 fix). Application-layer **NEVER calls** `set_tenant_context` outside its own docstring → H2 |
| 6 | Every tenant-scoped table has FORCE ROW LEVEL SECURITY + a helper-gated policy | ADR-009 | ✅ PASS | 8 tables verified: `multitenancy.{workspaces, cells, cell_members}`, `rbac.role_assignments`, `llm_gateway.{byok_keys, llm_usage_log}`, `billing.credit_transactions`, `mcp.mcp_connections` — all `ENABLE` + `FORCE` RLS + policies use `_shared.current_*_id()` helpers |
| 7 | `audit.audit_log` is intentionally non-RLS (cross-tenant compliance artefact); append-only via trigger; partition-DROP retention | ADR-014 amendment 2026-05-19 | ✅ PASS | `audit/0001_audit_log_partitioned.py:54-181` — RANGE-partitioned by `ts`, `audit_log_2026_05`/`2026_06` + `audit_log_default`, `deny_update_delete` trigger, `oriion_app` grants restricted to `SELECT, INSERT` |
| 8 | `llm_gateway.llm_usage_log` is append-only paired with `billing.credit_transactions` | llm-gateway invariant #7 + Architect audit H3 fix 2026-05-19 | ✅ PASS | `llm_gateway/0003:112-140` + `billing/0001:85-111` both have `deny_update_delete_*` triggers + `GRANT SELECT, INSERT` only (REVOKE UPDATE/DELETE on `oriion_app`). PR #30 audit H3 is closed |
| 9 | Atomic 3-currency write in single TX | llm-gateway invariant #7 | ✅ PASS | `billing_service.record_llm_cost` writes both rows on the caller-owned session, no commit; caller's `get_db` is the single commit boundary; cost-ledger SUM-match integration test (`test_cost_ledger_sum_match.py`) is in the green suite |
| 10 | Failover chain `deepseek → yandex → gigachat`; circuit-breaker state machine `CLOSED → OPEN → HALF_OPEN` | Phase 00.4 spec AC7 | ✅ PASS | `router_service.py:_CHAT_CHAIN = ("deepseek", "yandexgpt", "gigachat")`; `circuit_breaker.py:18-97` implements the full state machine + `try_half_open` cooldown + `record_failure` reset-on-half-open-failure |
| 11 | BYOK envelope encryption: AES-256-GCM (LocalAESKMS Wave 0) + YandexKMS stub for Phase 00.6 | ADR-014 amendment 2026-05-19 | ✅ PASS | `kms_provider.py:34-110` — KMSProvider Protocol + LocalAESKMS (12-byte nonce ‖ ct ‖ 16-byte tag canonical packing) + YandexKMS stub. `byok_service.fingerprint = sha256[:8]`; plaintext never persisted |
| 12 | Per-cell schema `cell_<uuid>.memory_entries` + HNSW index materialized in same TX as `cells` INSERT | ADR-009 amendment 2026-05-19 | ✅ PASS | `multitenancy/0004_provision_cell_schema_function.py:38-100` — SECURITY DEFINER function + idempotent `IF NOT EXISTS` clauses + `m=16, ef_construction=64` HNSW; `workspace_service._call_provision_cell_schema` invokes inside caller's outer TX so a failure unwinds the cells INSERT via SQLAlchemy session rollback |
| 13 | JWT HS256 + opaque refresh tokens with OWASP chain-revoke | ADR-014 | ⚠️ PARTIAL | `token_service.py:55-147` — HS256 ✅, jti UUID ✅, Redis blacklist on logout ✅, refresh-chain reuse detection in `auth_service.rotate_refresh:325-340` revokes the rotation_chain_id ✅. **But the `_V1`/`_V2` rotation slot only has `jwt_secret_access_v1` in `Settings`** — there is no `kid` claim wiring, no `_V2` slot, no rotation mechanism. The audit charter explicitly listed `_V1`/`_V2` slots with `kid` pinned → L1 |
| 14 | CloudEvents 1.0 envelope; source = `oriion://contexts/<context>`; type = `oriion.<context>.<entity>.<action>.<version>` | ADR-024 §3 | ✅ PASS | `iam._SOURCE = "oriion://contexts/iam"`, `multitenancy._SOURCE = "oriion://contexts/multitenancy"`, `audit._AUDIT_CE_SOURCE = "oriion://contexts/audit"`, `llm_gateway._SOURCE = "oriion://contexts/llm-gateway"` (hyphen, matching ADR convention); types follow `oriion.<ctx>.<entity>.<action>.v1` uniformly |
| 15 | Migration chain is a clean DAG; idempotent up/down halves | ADR-024 §1 (alembic discipline) | ✅ PASS | 24 revisions, all `down_revision` strings resolve; iam-branch forks at `_shared_0001` (predates 0002 helper, documented L1 in PR #30 audit); the rest fork at `_shared_0002`; only one declared `depends_on` (`llm_gateway_0002_byok_keys → multitenancy_0001_workspaces`) which is correct because of the physical FK |
| 16 | RBAC seed migration is idempotent (`ON CONFLICT DO NOTHING`) | Architect-audit (PR #30) | ✅ PASS | `rbac/0005_seed_built_in_roles.py` uses `ON CONFLICT DO NOTHING`; E2E TRUNCATE deliberately excludes the seed tables (F-1 fix in PR #32 audit) |

**Score: 13 PASS / 3 PARTIAL / 0 FAIL / 0 BLOCK.**

---

## Findings by severity

### BLOCK
*(none)*

### HIGH

#### H1 — `register()` writes to RLS-FORCEd tables with no tenant GUC; will fail under `oriion_app` in production

- **Carried over from:** AUDIT-2026-05-19-PR-00-2-5/section-04-architecture.md (H1) + AUDIT-REPORT.md (H-DEFER-2). Status: explicitly deferred to Phase 00.5 with Phase-05 AC pin.
- **Files:**
  - `backend/src/multitenancy/services/workspace_service.py:181-194` (INSERT workspace + cell + cell_schema)
  - `backend/src/iam/services/auth_service.py:156-160` (call site from `register()`)
  - `backend/migrations/versions/multitenancy/0003_cell_members.py:145-161` (per-command write policies)
- **Invariant violated:** "3-GUC default-deny RLS posture" (Wave 0 security decision #1); ADR-009 amendment "missing GUC → NULL → default-deny".
- **Evidence:** Greped all of `backend/src/`. `set_tenant_context` is referenced exactly twice — once at the definition (`_shared/db/rls.py:37`) and once in its own docstring example (`_shared/db/rls.py:48`). **Zero production code paths call it.** The test container masks this because superusers bypass FORCE RLS.
- **Suggested fix:** Three reasonable shapes (per PR #32 audit section 04 — pick one in Phase 00.5):
  1. SECURITY DEFINER `multitenancy.provision_initial_workspace_bootstrap()` SQL helper (matches the pattern of `provision_cell_schema`).
  2. Loosen INSERT policies to `WITH CHECK (_shared.current_user_id() IS NOT NULL OR pg_has_role(current_user, 'oriion_provisioner', 'MEMBER'))`.
  3. Set GUC to the just-created user_id before the multitenancy writes (cleanest from the application side; requires reading the just-flushed `users.id` and calling `set_tenant_context(workspace_id=NULL, cell_id=NULL, user_id=user.id)` — but the helper requires non-NULL workspace_id/cell_id; would need an `IS_REGISTERING` bootstrap escape).
- **Fix is:** Structural (needs the multitenancy router lifespan first to share the design with the request-scope GUC middleware).
- **Tracked:** HANDOFF.md "Founder action" + HANDOFF.md:102-118 Phase 00.5 brief lists it as AC#1.

#### H2 — `set_tenant_context` is dead code; the 3-GUC application layer has no caller

- **New finding (this audit).**
- **File:** `backend/src/_shared/db/rls.py:37-83`.
- **Invariant violated:** Same ADR-009 amendment as H1, but viewed from the application side: the 3-GUC context-setter is the single chokepoint that enforces tenant scoping, and it has no production caller. The DB-layer policies will return zero rows whenever queried under `oriion_app` (correct default-deny), so the test suite passes only because every test that exercises tenant-scoped data does so under the testcontainers superuser DSN.
- **Evidence:** `grep -rn 'set_tenant_context' backend/src/` returns 3 hits, all in `_shared/db/rls.py` itself (definition + docstring example + `clear_tenant_context` sibling).
- **Implication for Phase 00.5:** When LLM/multitenancy/MCP routers are wired into main.py, the request-scope GUC middleware MUST be designed and installed at the same time — otherwise the routers return empty pages for every authenticated user because RLS evaluates `_shared.current_user_id() = NULL`.
- **Suggested fix:** Install a `get_tenant_db_session` FastAPI dependency that wraps `get_db` + `set_tenant_context`, parameterized by `(workspace_id, cell_id, user_id)` resolved from `AuthenticatedUser` (per-user workspace lookup via `WorkspaceRepository.find_by_user_id` — single-membership Wave-0 simplification). The router boundary becomes the consistent GUC-setting site; the bootstrap path (register()) becomes the documented exception handled by H1's fix.
- **Fix is:** Structural; this is precisely the design Phase 00.5 owns.
- **Tracked:** Folded into H1's resolution.

#### H3 — `llm_gateway.billing_service → src.billing.models.CreditTransaction` cross-context model import (sanctioned but unformalized)

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (H1) + POST-MERGE-AUDIT-2026-05-19.md (D-1). Status: sanctioned debt; ADR-024 amendment promised but not written (A-12 in POST-MERGE backlog).
- **File:** `backend/src/llm_gateway/services/billing_service.py:26`.
- **Invariant violated:** ADR-024 §2 ("bounded-context source modules import their own models or `_shared`"). The atomic 3-currency write requirement makes a clean port/adapter expensive (the rich payload would need to traverse a service boundary in the same TX), so the violation is intentional.
- **Suggested fix:** Add a 3-line amendment to ADR-024 explicitly listing the sanctioned exception(s): `billing_service → billing.models.CreditTransaction` for atomic ledger writes; Wave 1+ refactor via outbox or ledger-port. Once the amendment exists, ruff/import-linter rules can codify the carve-out so accidental cross-context imports stop being indistinguishable from sanctioned ones.
- **Fix is:** In-loop (single docs file).
- **Tracked:** A-12 in POST-MERGE-AUDIT-2026-05-19.md.

---

### MEDIUM

#### M1 — Audit emits omit `workspace_id`/`cell_id` on 8 of 10 iam/multitenancy callsites

- **Carried over from:** PR #32 audit M2 (deferred).
- **Files:** `iam/services/auth_service.py:257-267, 299-307, 329-339, 363-373, 391-399, 481-489, 503-511`; `iam/services/consent_service.py` (verify the same pattern).
- **Invariant degraded (not violated):** ADR-014 "tenant attribution on audit rows". Audit_log is non-RLS (correctly), but the partial indexes `audit_log_cell_id_ts_idx` / `audit_log_workspace_id_ts_idx` have `WHERE cell_id IS NOT NULL` / `WHERE workspace_id IS NOT NULL` — login/refresh/logout/verify-email/forgot/reset events skip both. Roughly 95% of iam audit rows fall out of the per-tenant lookup path.
- **Suggested fix:** Add `WorkspaceRepository.find_by_user_id` lookup at AuthService session-issue time; cache the `(workspace_id, cell_id)` on the request scope so every downstream emit can stamp both. Wave-0 single-workspace assumption holds. Wave-1 (multi-workspace) needs an active-workspace claim in the JWT anyway.
- **Fix is:** In-loop (~15 lines in `auth_service.py` + `consent_service.py`); deferrable to Phase 00.5 because it's observability hygiene.

#### M2 — `emit_audit_event` free-function pattern persists; `AuditService` class exists but unused

- **Carried over from:** PR #32 audit M3 (deferred).
- **Files:** `audit/services/audit_service.py:83-132` (AuditService class — orphaned) vs `audit/services/audit_service.py:169-249` (free function — 10+ callsites pass `session=self._session`).
- **Symptom:** every iam/multitenancy service that wants to audit must (a) hold an AsyncSession in `__init__`, (b) thread it through 10+ keyword args at each callsite, (c) the unit-test conftest autouse-patches the free function at the import site (`tests/iam/unit/conftest.py:25-38`) because the 10-arg signature defies clean mocking.
- **Invariant violated:** None per se — but every other context follows the "repo is unit-of-work owner; service holds repo in `__init__`" pattern. The free function is the odd one out.
- **Suggested fix:** Refactor 10+ callsites to construct `AuditService` via DI and call `audit_service.record(...)`. Delete the free function. Wipe the conftest patch. Phase 00.5 would benefit because the new multitenancy/llm-gateway routers can take `AuditService = Depends(get_audit_service)` instead of inheriting the session-threading pattern.
- **Fix is:** Structural (touches every audit-emitting service); cleanest if landed before Phase 00.5 adds 5+ new audit callsites from llm-gateway routes.

#### M3 — `LocalAESKMS` + `get_kms_provider` read env directly instead of via `Settings`

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (M3, deferred).
- **Files:** `llm_gateway/services/kms_provider.py:62-110` (env reads of `BYOK_MASTER_KEY_B64` + `KMS_BACKEND`); `_shared/config.py:84-104` (Settings fields exist with `SecretStr`).
- **Invariant violated:** "Settings is the single env reader" (cross-context convention; no formal ADR, but every other module pulls from `Settings`). Two consequences: (a) test-time env mutation can drift from a cached `Settings()`; (b) `SecretStr` repr-protection on the master key is bypassed.
- **Suggested fix:** `LocalAESKMS.__init__(*, master_key_b64: SecretStr)` + factory `get_kms_provider(settings: Settings)` accept the Settings instance via FastAPI Depends. Phase 00.5 will need to construct the KMSProvider inside the lifespan anyway for the byok router DI; the refactor is cheap if folded into the lifespan assembly.
- **Fix is:** Structural-light (one file + lifespan wiring); land with Phase 00.5.

#### M4 — `cells_workspace_slug_uidx` is a full UNIQUE index; cells.archived_at is ignored

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (L7).
- **File:** `backend/migrations/versions/multitenancy/0002_cells.py:42-47`.
- **Invariant degraded:** Soft-archive semantics. Re-creating a cell with the same slug after archive is impossible because the unique index doesn't filter on `archived_at IS NULL`. Workspaces correctly use `WHERE deleted_at IS NULL` (`workspaces_slug_active_uidx`) — cells inconsistent.
- **Suggested fix:** New alembic migration (`multitenancy_0005_cells_slug_partial_unique.py`) that drops the full unique index and recreates it as partial with `WHERE archived_at IS NULL`. 5 lines of DDL.
- **Fix is:** In-loop (small migration); can land in Phase 00.5 or Wave 1 without coupling to anything else.

#### M5 — H-DEFER-1 (slug-based cross-tenant linkage) remains open

- **Carried over from:** PR #32 audit S-HIGH-1.
- **File:** `src/multitenancy/services/workspace_service.py:160-179` + `src/iam/services/auth_service.py:151-160` (call site).
- **Invariant violated:** Tenant isolation (silent cross-tenant linkage). `alice@x.com` and `alice@y.com` both derive slug `alice`; the second registration's idempotent-on-slug path returns the FIRST alice's workspace + cell IDs.
- **Status:** Founder-sanctioned for Wave-0 user-testing per Round 2 Q6 of the PR #32 grill. Security audit reframes it as cross-tenant linkage; founder accepted.
- **Suggested fix:** Append `uuid4().hex[:6]` suffix to the slug on collision, OR raise `WorkspaceSlugConflict` instead of returning the existing rows. The second is safer.
- **Fix is:** In-loop (~5 lines in `provision_initial_workspace`); deferrable to Wave 1 per founder grill.

---

### LOW

#### L1 — JWT key rotation `_V1`/`_V2` slot + `kid` claim is not wired

- **New finding (this audit).** The audit charter (point 8) explicitly listed "HS256 access tokens with rotating `_V1`/`_V2` secret slots (kid pinned)" as an invariant to verify.
- **Files:**
  - `_shared/config.py:51` — only `jwt_secret_access_v1: SecretStr` exists; no `_v2` field.
  - `iam/services/token_service.py:61-114` — `issue_access_token` and `verify_access_token` hard-code `self._settings.jwt_secret_access_v1.get_secret_value()`. No `kid` claim is set or read.
- **Invariant degraded:** ADR-014 mentions "rotation slot" but the field is single-slot. This is consistent with Wave 0 (no rotation has been needed) but the rotation infrastructure isn't ready when it is.
- **Suggested fix:** Wave 1 hardening — add `jwt_secret_access_v2: SecretStr | None`, write a `kid` claim ("v1"|"v2"), let `verify_access_token` try v1 then v2 on `InvalidSignatureError`. ~30 lines.
- **Fix is:** In-loop, Wave-1-blocking but not Phase-00.5-blocking.

#### L2 — `JWT` dev-default secret in Settings (M-DEFER-4 from PR #32 audit)

- **File:** `_shared/config.py:51-54` — `default=SecretStr("changeme-dev-only-please-replace-in-prod-min-32-chars")`.
- **Wave-1 fix candidate:** Prod-startup validator that refuses to boot if `app_env=="prod"` and the secret matches the dev literal. Single `model_validator` decorator on `Settings`.
- **Tracked:** PR #32 audit M-DEFER-4.

#### L3 — `BYOKKey.workspace_id ON DELETE CASCADE`

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (L8).
- **File:** `migrations/versions/llm_gateway/0002_byok_keys.py:30`.
- **Concern:** Workspaces are soft-deleted; `ON DELETE CASCADE` only fires on hard-delete (admin-only) but silently destroys key-custody records. `ON DELETE RESTRICT` matches `cells.workspace_id`.
- **Fix is:** In-loop; small follow-up migration; defer to Wave 1.

#### L4 — `LLMUsageLog.id bigserial` vs uniform `uuid PK gen_random_uuid()` elsewhere

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (L3).
- **File:** `migrations/versions/llm_gateway/0003_llm_usage_log.py:31`.
- **Concern:** Inconsistency only; the choice is fine for very-high-volume tables. The COMMENT explaining the deviation never landed.
- **Fix is:** In-loop (1 line: `COMMENT ON COLUMN`); cosmetic, defer.

#### L5 — `_shared.current_user_id()` marked STABLE; `current_setting('…', true)` is technically VOLATILE

- **Carried over from:** AUDIT-2026-05-19/section-05-architecture.md (L11).
- **File:** `migrations/versions/_shared/0002_current_user_id_helper.py:42`.
- **Concern:** Postgres planner may cache STABLE results within a query plan; if `SET LOCAL` runs mid-transaction, the cached value lingers. `set_tenant_context` only runs at request entry, so the invariant holds — but it's an implicit contract.
- **Fix is:** In-loop (documentation comment); defer.

#### L6 — `read_url` SSRF TOCTOU window (DNS-rebinding)

- **Carried over from:** AUDIT-2026-05-19/section-03-security.md H-3 + HANDOFF.md:124.
- **File:** `src/mcp/tools/read_url.py:116-124, 243-255`.
- **Concern:** Time-of-check (`_validate_url` resolves hostname via `getaddrinfo`) vs time-of-use (httpx connects, potentially re-resolving) window. The redirect event hook re-runs `_validate_url`, partially mitigating; the initial connect is still vulnerable.
- **Status:** Already documented as Wave 1 hardening (5MB cap + scheme allow-list + redirect hook reduce blast radius for Wave 0).
- **Fix is:** Structural (resolve hostname once at validate time, pass IP to httpx with `Host` header preserved); Wave 1.

---

## Cross-context import graph (verified inventory)

Greped all `^from src\.<ctx>\.` imports in `backend/src/`. Cross-context
edges where `<ctx_A> ≠ <ctx_B>` (own-context + `_shared` imports excluded):

| From | To | Symbol | Verdict |
|---|---|---|---|
| `iam.services.auth_service:28` | `audit.services.audit_service` | `emit_audit_event` | ✅ Sanctioned (audit is the published port consumed by everyone) |
| `iam.services.auth_service:59` | `multitenancy.services.workspace_service` | `provision_initial_workspace` | ✅ Sanctioned per `contracts/multitenancy/README.md:124-150` |
| `iam.services.consent_service:17` | `audit.services.audit_service` | `emit_audit_event` | ✅ Sanctioned |
| `multitenancy.services.cell_service:18` | `audit.services.audit_service` | `emit_audit_event` | ✅ Sanctioned |
| `multitenancy.routers.{cells,workspaces}:23-24/9-10` | `iam.middleware` | `AuthenticatedUser`, `get_current_user` | ✅ Composition-root pattern; routers depending on `iam`'s published auth port is canonical FastAPI |
| `llm_gateway.services.billing_service:26` | `billing.models` | `CreditTransaction` (model, not service) | ⚠️ ARCH-DEBT — sanctioned but ADR-024 amendment unwritten (see H3) |

**Acyclicity check:**
- `audit → *`: ZERO outgoing cross-context edges from audit (leaf ✅).
- `_shared → *`: ZERO outgoing context edges (foundation ✅).
- `multitenancy → iam`: only at the router layer (`AuthenticatedUser` port) — service layer is clean.
- `iam → multitenancy`: only `provision_initial_workspace` (single sanctioned port).
- `iam → audit`, `multitenancy → audit`: only `emit_audit_event` (single sanctioned port).
- `llm_gateway → billing`: single sanctioned model import (H3).
- `rbac`, `mcp`: zero cross-context imports.

**Graph is a DAG.** No cycles introduced.

---

## Phase 00.5 readiness assessment

### Rating: **4 / 5**

### What's clean and ready

1. **Router code exists for all three pending contexts.** `multitenancy.routers.{workspaces, cells}`, `llm_gateway.routers.{chat, embeddings, providers, byok, usage}`, `mcp.client + mcp.services.connection_service`. All return 501 / contract surface only; service layer underneath is fully unit-tested.
2. **Exception hierarchies are uniform.** `IamError`, `MultitenancyError`, `MCPError`, `LLMGatewayException` all carry `(code, status_code, title, detail)` — the `IamError` handler in `main.py:59-80` can be lifted near-mechanically. RFC 7807 problem+json envelope already established.
3. **DI extension points are clean.** `iam/deps.py` shows the canonical pattern (FastAPI Depends factories returning per-request service instances; `Settings` + `Redis` cached via `lru_cache`). Phase 00.5 can mirror this for `WorkspaceService`, `CellService`, `LLMRouter`, `MCPConnectionService`.
4. **Provider DI assembly is straightforward.** `LLMRouter.__init__(*, providers: dict[str, LLMProvider], circuits: dict[str, ProviderCircuit])` takes a static providers dict + mutable circuits dict. The FastAPI lifespan can construct DeepSeekProvider / YandexGPTProvider / GigaChatProvider + the circuit dict + LocalAESKMS once, store on `app.state`, expose via dependency.
5. **CloudEvents / structlog telemetry is uniform.** All four implemented contexts emit consistent CE source URIs + CE-type strings; main.py wiring of additional routers will inherit the configured `configure_structlog()` call.
6. **Audit-log infrastructure is production-grade.** Partitioned + append-only + retention by DROP. New audit events from the wired routers just need to flow through `emit_audit_event(..., session=db)`.

### What blocks (must land in Phase 00.5)

1. **H1 + H2 (bootstrap RLS + tenant-context middleware).** Phase 00.5's first AC per HANDOFF.md. Cannot be deferred — the moment multitenancy routers go live under real auth, every `GET /workspaces` returns an empty page without the GUC middleware.
2. **Multitenancy + LLM gateway + MCP exception handlers in main.py.** Three near-identical handler functions; ~60 lines of code. The IamError handler is the template.
3. **LLM provider DI.** Construct DeepSeekProvider / YandexGPTProvider / GigaChatProvider in lifespan; thread KMSProvider in via `Settings`-driven factory; expose `get_llm_router()` dependency.
4. **Replace `test_llm_chat_endpoint_is_not_yet_wired`** with the full register → chat → embeddings → BYOK matrix (per HANDOFF.md:111-117).

### What's friction (not a blocker, but adds Phase 00.5 hours)

1. **M2 (`emit_audit_event` free function).** Refactoring 10+ callsites is cleaner BEFORE Phase 00.5 adds 5+ new ones. Worth a 1-hour pre-Phase-05 commit if scope allows.
2. **M3 (KMS env→Settings).** Lands naturally with the LLM-router lifespan assembly.
3. **DB engine + Redis lifespan.** `get_engine()` is `@lru_cache(maxsize=1)` (process-wide). FastAPI lifespan should call `engine.dispose()` on shutdown to drain the pool cleanly. Testcontainers fixture uses a per-session engine (`tests/conftest.py:79-119, 219-242`), independent of the prod bootstrap path — so the engine lifecycle is correct in both worlds, but the lifespan dispose is currently absent.

### Phase 00.5 readiness commentary

**Score 4/5.** Minus one point for the H1+H2 blocker that Phase 00.5 is
explicitly chartered to resolve — the multitenancy / LLM / MCP routers
literally cannot serve a real request until the GUC middleware exists.
Plus full credit for everything else: clean DI seams, uniform exception
hierarchies, sanctioned cross-context graph, production-grade audit and
cost-ledger infrastructure, correct circuit-breaker semantics, working
BYOK custody with documented future-Yandex-KMS swap, idempotent eager
per-cell schema provisioning, and an established CloudEvents +
structlog telemetry pattern.

**Recommended Phase 00.5 sequence:**
1. Write the request-scope GUC middleware (`get_tenant_db_session`) + the
   register-bootstrap escape (option 1 of H1: SECURITY DEFINER SQL
   function). Replace `override_get_db` in the E2E fixture with
   `SET LOCAL ROLE oriion_app` to force the test to surface the prod
   role's behaviour.
2. Install `MultitenancyError`, `LLMGatewayException`, `MCPError`
   handlers in `main.py` (60 lines, mechanical lift).
3. Construct LLM provider instances + circuits + KMSProvider in the
   FastAPI lifespan; expose dependencies.
4. Wire `multitenancy.routers` + `llm_gateway.routers` + (minimal) MCP
   surface under `/api/v1` prefix.
5. Optionally pre-fold M2 (AuditService DI'd everywhere) before step 4
   to avoid the new routers inheriting the session-threading pattern.
6. Replace the 501-stub E2E test with the full matrix per launch-checklist
   §5.

---

## Summary

The cumulative Wave-0 architecture is in a **healthy, defensible state**.
The three prior audits (Architect-only for PR #30, then five-agent for
PR #32, then this cumulative one) have converged: the 4 HIGH findings of
PR #30 were fixed in-loop; PR #32's HIGH findings were either fixed in-loop
or escalated to Phase 00.5 / Wave 1 with named ownership; the deferred
catalog (H1, H3, M1-M5, L1-L6) is internally consistent — nothing flagged
"Wave 1" actually blocks Phase 00.5, and nothing flagged "Phase 00.5"
was supposed to be Wave 0.

Two architecturally significant items remain:

* **H1 + H2 together** form the single material risk for Phase 00.5
  startup: the bootstrap RLS path AND the absence of any production
  `set_tenant_context` caller. Phase 00.5 must land both in the same
  commit (the GUC middleware is the application-side answer; the
  SECURITY DEFINER bootstrap is the database-side answer for the
  register-time exception). The E2E fixture must be tightened to run
  as `oriion_app` so the test certifies prod behaviour.

* **H3** is a single documentation-amendment commit away from being
  fully resolved.

**Phase 00.5 readiness: 4/5.** Greenlight with the explicit AC pin on
H1+H2 resolution as the first commit of the new worktree.

**Finding count:** 0 BLOCK, 3 HIGH (1 new — H2; 2 carried over with
named tracking), 5 MEDIUM, 6 LOW = 14 total. Recommended verdict: **FLAG**,
proceed to Phase 00.5 with explicit AC pin on H1+H2 + H3 ADR amendment.
