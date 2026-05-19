# Post-merge consistency audit — PR #30 (Phase 00.3 + 00.4)

**Auditor:** Compliance Auditor
**Date:** 2026-05-19
**Branch state:** `claude/cool-bell-0c74ba` (pre-merge to main; PR #30 open, CI approaching green)

## Verdict

**FLAG** — no blockers for Phase 00.2.5 to start, but **4 must-fix-before-merge** corrections (3 are doc-only one-line edits, 1 is a stale-comment fix). The integration runway is clean: stub signatures are formally tested against real impls (`test_emit_audit_event_stub_compat.py` proves it for audit), the migration chain is verified by CI, and the AUDIT-2026-05-19 swarm already absorbed the 4 HIGH security/RLS findings in-loop. The remaining items are documentation drift, not code drift.

The founder can confidently open Phase 00.2.5 immediately after the merge. The Phase 00.2.5 brief in `HANDOFF.md` is accurate; the stub inventory below is the source-of-truth for that worktree's task list.

## Consistency matrix (12 dimensions)

| # | Dimension | Status | Finding |
|---|---|---|---|
| 1 | STATUS.md vs git log | PASS | All 9 atomic commits cited + 9 follow-up CI/test fixes reflected in the "Phase 00.3 + 00.4 combined PR" paragraph. STATUS.md:33 wording "code-complete" matches phase-spec status fields. |
| 2 | HANDOFF.md vs commits/tooling | PASS | 9 atomic commits enumerated `HANDOFF.md:55-65` match `git log --oneline` 1-to-1. Build/test state `HANDOFF.md:69-75` matches AUDIT-REPORT.md final verification block. |
| 3 | JOURNAL.md append-only + latest entry | PASS | Latest entry `JOURNAL.md:156-174` (`2026-05-19 · cool-bell-0c74ba`) is consistent with HANDOFF; no edits to prior entries (git log JOURNAL.md confirms append-only — only new entries added 2026-05-14/15/17/18/19). |
| 4 | Phase-spec Status fields | PASS | `00.2-custom-jwt-auth.md:10`, `00.3-db-rls-multitenancy.md:12`, `00.4-llm-gateway.md:12` all read "✅ Code-complete" — match STATUS.md headline. |
| 5 | ADR amendments 2026-05-19 | PASS | All 5 ADRs (`ADR-005`, `ADR-009`, `ADR-014`, `ADR-018`, `ADR-024`) carry `(amendment 2026-05-19, see «Wave 0 implementation decisions»)` status line and the dated decision sections — verified `ADR-005-pgvector-then-qdrant.md:3-7` as template. |
| 6 | PLACEHOLDERS.md TBD coverage | FLAG | 4 new env vars introduced; 3 registered (`TBD_BYOK_MASTER_KEY_B64`, `TBD_YANDEX_CLOUD_KMS_KEY_ID`, `TBD_FX_RATE_USD_TO_RUB_OVERRIDE`, `TBD_YANDEX_SEARCH_API_KEY` — `PLACEHOLDERS.md:94/103/104/105`). `BRAVE_SEARCH_API_KEY` is referenced in `.env.example:93` as `TBD_BRAVE_SEARCH_API_KEY` and exists in `PLACEHOLDERS.md:94` — confirmed registered. **All four declared "new" tokens are present.** |
| 7 | Contracts vs migrations — legacy `organization` term | FLAG | DDL + new code is clean (all migrations + `src/multitenancy/` use `workspace`). However **3 contracts still reference legacy `organization` term outside their amendment notes**: `contracts/mcp/schema.sql:8/18/30/38/56/69` (`organization_id` column + comments), `contracts/billing/schema.sql:8/18/22/31/39/56/74/87` (skeleton, deferred to Wave 2 — explicitly skeleton per `billing/README.md:21`), `contracts/rbac/schema.sql:90/148/156-158` (commented-out seed SQL still using old slugs). The rbac code (`migrations/versions/rbac/0005_seed_built_in_roles.py:19`) implements the correct `workspace.*` slugs — only the SQL **comments** in the contract files are stale. See finding C-1. |
| 8 | `backend/src/_stubs/` inventory of consumers | PASS | 5 import sites (4 production + 1 test, 2 test imports for compat suites). Full list under "Phase 00.2.5 readiness assessment / Stubs inventory" below. |
| 9 | Cross-context model imports (forbidden per ADR-024) | FLAG | One known violation: `src/llm_gateway/services/billing_service.py:26` imports `from src.billing.models import CreditTransaction`. **Already documented as architecturally-sanctioned** debt per `HANDOFF.md:117` (atomic 3-currency write across `llm_usage_log` + `credit_transactions`) and flagged in the architect-audit H1. No other cross-context model imports detected. |
| 10 | Migration chain integrity | PASS | Verified `down_revision` chain via Grep: `_shared_0001_init` (root) → `_shared_0002_current_user_id_helper` → 6 branches (`iam`, `multitenancy`, `rbac`, `audit`, `llm_gateway`, `billing`, `mcp`). **`iam` branch forks at `_shared_0001_init` (skips the 0002 helper) — by design**, because `iam.users` table predates the GUC helpers. CI uses `alembic upgrade heads` (plural) since 8 heads exist — verified `.github/workflows/ci-backend.yml:118`. Pre-create of `alembic_version` with VARCHAR(255) `.github/workflows/ci-backend.yml:99-111` handles long revision IDs. CI green proves the chain. |
| 11 | Test marker consistency | PASS | `pyproject.toml:142` declares strict markers + default deselect of `live` and `integration`. Audit: 8 `@pytest.mark.integration` tests all require PG (`audit/test_audit_log_append_only.py`, `audit/test_audit_partitions.py`, `multitenancy/test_rls_isolation.py`, `multitenancy/test_provision_cell_schema.py`, `llm_gateway/test_byok_flow_full.py`, `llm_gateway/test_cost_ledger_sum_match.py`). **0 actual `@pytest.mark.live` test functions exist in the suite** — `live` marker is declared but never applied. This is consistent with HANDOFF "live deferred to Phase 00.6"; the marker is reserved for future provider tests. |
| 12 | OQ-04 status | PASS | `OPEN-QUESTIONS.md:11` "До Phase 00.2" + `STATUS.md:67` "Submitted — dev unblocked. Final РКН confirmation required до prod-launch" + `HANDOFF.md:24` identical wording — three-way consistent. |

## Phase 00.2.5 readiness assessment

### Stubs inventory (file:line list with source/target pairs)

**Production callers** (must be rewired in 00.2.5):

| # | Caller (file:line) | Stub import | Target real impl | Signature delta |
|---|---|---|---|---|
| 1 | `backend/src/iam/services/auth_service.py:23` | `from src._stubs.audit import emit_audit_event` | `src.audit.services.audit_service::emit_audit_event` | Real is strict superset (verified by `test_emit_audit_event_stub_compat.py:17-91`). Pure import swap. |
| 2 | `backend/src/iam/services/auth_service.py:24` | `from src._stubs.multitenancy import provision_initial_workspace` | `src.multitenancy.services.workspace_service::provision_initial_workspace` | **Signature drift** — stub takes `(user_id)`, real takes `(session, user_id, email_localpart)`. **Not** a pure import swap. See finding M-1. |
| 3 | `backend/src/iam/services/consent_service.py:15` | `from src._stubs.audit import emit_audit_event` | `src.audit.services.audit_service::emit_audit_event` | Pure import swap. |
| 4 | `backend/src/multitenancy/services/cell_service.py:18` | `from src._stubs.audit import emit_audit_event` | `src.audit.services.audit_service::emit_audit_event` | Pure import swap. **Stale comment** at line 18 reads "# 00.3-audit-subagent will swap" — the audit subagent already landed the real impl in this same PR; comment should read "00.2.5 integration will swap". See finding M-2. |
| 5 | `backend/src/iam/services/auth_service.py:143` | Calls `provision_initial_workspace(user.id)` | Real impl needs `(session, user_id, email_localpart)` | Same as #2 — call site refactor required. |

**Test-only stub consumers** (do not need rewiring — the tests validate stub-vs-real compatibility):

| # | Test file | Purpose | Action in 00.2.5 |
|---|---|---|---|
| 6 | `backend/tests/audit/test_emit_audit_event_stub_compat.py:13` | Imports stub + real, asserts signature superset relationship. | Keep until `_stubs/` is deleted. Then delete this test (it has nothing to compare against). |
| 7 | `backend/tests/iam/unit/test_stubs.py:8-9` | Smoke-tests the stub itself. | Delete with `_stubs/` directory. |

### Signature compatibility check (stub vs real impl)

#### Audit — `emit_audit_event` — PASS (formally tested)

Stub signature (`backend/src/_stubs/audit.py:25-34`):
```
async def emit_audit_event(
    actor_type: str,
    actor_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None
```

Real signature (`backend/src/audit/services/audit_service.py:169-182`):
```
async def emit_audit_event(
    actor_type: str,
    actor_id: UUID,
    action: str,
    resource_type: str | None = None,   # was required str — relaxed to optional
    resource_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    *,
    session: AsyncSession | None = None,    # new
    workspace_id: UUID | None = None,        # new
    cell_id: UUID | None = None,              # new
) -> None
```

**Strict superset confirmed by 5 unit tests** (`test_emit_audit_event_stub_compat.py`):
- every stub param exists in real (`test_real_impl_includes_every_stub_parameter`)
- positional order prefix preserved (`test_real_impl_preserves_stub_parameter_order_prefix`)
- no stub-optional param made required (`test_real_impl_stub_param_defaults_compatible`)
- `session`, `workspace_id`, `cell_id` are kwonly with default `None` (`test_real_impl_adds_*`)
- return annotation remains `None`

Caveat: the relaxation of `resource_type` from `str` to `str | None` is backward-compatible for runtime but a **strict type-narrowing for any caller that had `resource_type: str` typed**. mypy passes (per HANDOFF.md:72), so no caller depends on the stricter annotation.

#### Multitenancy — `provision_initial_workspace` — FAIL (signature drift; intentional)

| Aspect | Stub | Real |
|---|---|---|
| File | `backend/src/_stubs/multitenancy.py:35` | `backend/src/multitenancy/services/workspace_service.py:135` |
| Signature | `(user_id: UUID) -> WorkspaceProvisionResult` | `(session: AsyncSession, user_id: UUID, email_localpart: str) -> WorkspaceProvisionResult` |
| Result shape | `WorkspaceProvisionResult{workspace_id, cell_id}` | Identical `WorkspaceProvisionResult{workspace_id, cell_id}` |
| Behaviour | uuid5-derived deterministic IDs, no DB write | INSERT workspace + cell, idempotent on slug, calls `multitenancy.provision_cell_schema(uuid)`, emits 2 CloudEvents |

**Phase 00.2.5 action required at call site** (`backend/src/iam/services/auth_service.py:143`):
- Pass `session` (already available via DI in `AuthService.register`).
- Pass `email_localpart` (derive from `cmd.email` — split on `@`).

The result-shape match means downstream consumers in `auth_service.register` (which read `provision.workspace_id` / `provision.cell_id`) are untouched. This is acknowledged in the real impl docstring (`workspace_service.py:7-12`): "The Wave-0 stub takes only `user_id`; this real implementation takes `(session, user_id, email_localpart)`... The 00.2.5 integration phase owns the call-site refactor."

#### RLS — `set_tenant_context` — NO-STUB (phase-spec text-only drift)

Phase 00.4 spec (`00.4-llm-gateway.md:7`) and architect-PR context (`_session-context/2026-05-17-architect-pr-3-way-parallel.md:197,225`) reference a planned `backend/src/_stubs/rls.py::set_tenant_context` stub. **No such file exists** — and that is correct, because `backend/src/_shared/db/rls.py::set_tenant_context` (the real impl) landed in this same combined PR. Phase 00.4 code (`backend/src/mcp/services/connection_service.py:13`) imports from the real `_shared/db/rls`, not from any stub. **The phase-spec text overestimates the stubs to remove.** See finding M-3 (advisory).

Stub-RLS-was-never-needed; only 2 stubs exist and Phase 00.2.5 only needs to remove `_stubs/audit.py` + `_stubs/multitenancy.py` + `_stubs/__init__.py`.

### New debt that didn't exist before this PR

| ID | File:line | Description | Severity |
|---|---|---|---|
| D-1 | `backend/src/llm_gateway/services/billing_service.py:26` | Cross-context import of `src.billing.models.CreditTransaction` (ADR-024 violation) | Sanctioned (per HANDOFF.md:117 — atomic 3-currency write); refactor Wave 1+ via outbox/port. **No action 00.2.5.** |
| D-2 | `backend/src/mcp/tools/read_url.py` (SSRF TOCTOU) | DNS-rebinding window between `_validate_url` and httpx connect | Acknowledged in HANDOFF.md:119; Wave 1 hardening. **No action 00.2.5.** |
| D-3 | `backend/migrations/versions/llm_gateway/0003_llm_usage_log.py` + `billing/0001_credit_transactions_skeleton.py` | Skeleton DDL inline (not in `contracts/billing/`) | Acknowledged contract gap; full billing contract Wave 2. **No action 00.2.5.** |

### Anything missing for the 00.2.5 worktree to start cleanly

Nothing blocking. The brief in `HANDOFF.md:96-111` is accurate. Recommended additions to the brief:

1. Pass `session` + derive `email_localpart` from `cmd.email` at `auth_service.py:143` when swapping `provision_initial_workspace` import (signature change, not import-only).
2. Delete `backend/src/_stubs/` entirely (3 files: `__init__.py`, `multitenancy.py`, `audit.py`).
3. Delete `backend/tests/iam/unit/test_stubs.py` (smoke-tests the deleted stubs).
4. Delete `backend/tests/audit/test_emit_audit_event_stub_compat.py` (loses its second comparator).
5. Pre-existing CI pre-create-alembic-version step (`.github/workflows/ci-backend.yml:99-111`) — keep until the alembic.ini cp1251 issue closes in Phase 00.6.
6. iam repository coverage (~<60% via mocks per JOURNAL.md:149) — 00.2.5 owns the real-PG TestClient integration suite that will lift this to the AC9 ≥85% target on `src.iam`.

## Findings to fix before merge

### Severity: M (medium — doc + comment hygiene)

#### M-1 — Phase 00.2.5 brief should call out `provision_initial_workspace` signature change

**File:** `.planning/HANDOFF.md:104-105`
**Current text:** `rewire iam.auth_service.register → multitenancy.workspace_service.provision_initial_workspace`
**Issue:** Reads like an import swap, but it's also a call-site refactor (add `session=`, add `email_localpart=cmd.email.split("@")[0]`).
**Suggested edit:** Append "(pass session + derive email_localpart at the call site; signature differs from stub)".

#### M-2 — Stale "audit-subagent will swap" comment in cell_service

**File:** `backend/src/multitenancy/services/cell_service.py:18`
**Current:** `from src._stubs.audit import emit_audit_event  # 00.3-audit-subagent will swap`
**Issue:** The 00.3 audit-subagent landed the real impl in this same PR; the swap is owned by Phase 00.2.5, not 00.3.
**Suggested edit:** `from src._stubs.audit import emit_audit_event  # 00.2.5 integration will swap`

#### M-3 — Phase-spec 00.4 + architect-PR context-doc reference a non-existent `_stubs/rls.py`

**Files:**
- `.planning/roadmap/wave-0-foundation/phases/00.4-llm-gateway.md:7` ("`backend/src/_stubs/rls.py::set_tenant_context(...)` — no-op context manager")
- `.planning/_session-context/2026-05-17-architect-pr-3-way-parallel.md:197,225`

**Issue:** `backend/src/_stubs/rls.py` was planned but never created (real `_shared/db/rls.py` landed in same PR, making the stub unnecessary). Phase 00.4 code uses `_shared/db/rls` directly.
**Suggested edit:** Add a 2-line note at the top of `00.4-llm-gateway.md` "Architect-PR overrides" block: *"`_stubs/rls.py` was never created — real `_shared/db/rls.py::set_tenant_context` landed in the same combined PR. Phase 00.2.5 inventory only needs to delete `_stubs/audit.py` + `_stubs/multitenancy.py`."*

#### M-4 — Contract SQL comments still reference legacy `organization` term

**Files:**
- `.planning/contracts/mcp/schema.sql:8,18,30,38,56,69` (`organization_id` in DDL — mcp contract was not amended 2026-05-19)
- `.planning/contracts/rbac/schema.sql:90,148,156-158` (commented seed SQL with `organization.view/.update/.delete` slugs — code uses `workspace.*` correctly per `migrations/versions/rbac/0005_seed_built_in_roles.py`)
- `.planning/contracts/artifacts/README.md:25,38`, `memory/README.md:18,48,55`, `mcp/README.md:20,35,61`, `billing/events.yaml:13,31` — legacy term in non-amended docs

**Issue:** Code is clean; contracts have legacy terms in comments + skeleton sections. Risk: a future agent reading these contracts as "current" introduces `organization_id` in new code.
**Suggested edit:** Add a 1-line bridging note at the top of each affected contract README (`mcp/`, `artifacts/`, `memory/`): *"NOTE 2026-05-19: any `organization` / `organization_id` reference below is legacy; canonical term is `workspace` / `workspace_id` per the multitenancy contract amendment."* This is what `multitenancy/README.md:14` and `rbac/README.md:26` already do. Skeleton billing contract (`billing/schema.sql`) is already flagged as "deferred to Wave 2" in `billing/README.md:21` — no action needed there.

**None of M-1 through M-4 block the merge.** They are 1-3 line edits that can either land as a follow-up "docs(planning)" commit on `main` or be merged via PR #30 if the founder elects to amend.

## Findings to track in Phase 00.2.5 backlog (advisory)

1. **A-1.** Delete `backend/src/_stubs/` directory entirely (3 files).
2. **A-2.** Delete `backend/tests/iam/unit/test_stubs.py` (validates stubs that no longer exist).
3. **A-3.** Delete `backend/tests/audit/test_emit_audit_event_stub_compat.py` (its second comparator is gone after stub deletion).
4. **A-4.** Refactor `auth_service.register` to pass `session=` and derive `email_localpart=` when calling real `provision_initial_workspace` (M-1 above).
5. **A-5.** Add the iam repository integration suite against real PG (lifts current ~<60% repo-layer mock coverage to the AC9 ≥85% target on real I/O paths per JOURNAL.md:149).
6. **A-6.** Add testcontainers session-scoped `pg_container` fixture to `tests/conftest.py` so `@pytest.mark.integration` tests run without docker-compose stack (HANDOFF.md:121 — currently pytest-postgresql + testcontainers are declared in dev deps but conftest is not wired).
7. **A-7.** Add the E2E TestClient smoke suite (register → verify-email → login → `/api/v1/llm/chat` → refresh → logout) to cover the router-glue ~0% coverage tier (HANDOFF.md:116).
8. **A-8.** Update `roadmap/wave-0-foundation/phases/00.2.5-*.md` (does not yet exist as a spec file — create from HANDOFF.md "Founder action" block).
9. **A-9.** When Phase 00.6 closes the alembic.ini cp1251 issue (HANDOFF.md:120), remove the CI pre-create-alembic_version workaround (`.github/workflows/ci-backend.yml:99-111`).
10. **A-10.** Section 01 (Code Reviewer) audit was not delivered — schedule a standalone code-review pass in Phase 00.2.5 per HANDOFF.md:115.
11. **A-11.** Live LLM provider tests (`@pytest.mark.live`) — marker is declared in `pyproject.toml:145` but no test actually uses it. Either populate the suite in Phase 00.6 (per phase-spec 00.4:10 "live deferred to Phase 00.6") or remove the unused marker until needed.
12. **A-12.** Cross-context import sanctioning — add a one-line ADR-024 amendment ("Wave 0 sanctioned exceptions: `billing_service → billing.models` for atomic 3-currency write; Wave 1 refactor via outbox") so future ruff/import-linter rules can codify it.

## Summary

PR #30 lands in a healthy state. Of the 12 consistency dimensions, **9 PASS** outright; **3 FLAG** (placeholder coverage is fine but worth re-verifying — done; legacy `organization` term in unaffected contracts; one sanctioned cross-context import). All 4 must-fix-before-merge items are documentation/comment hygiene — none block the integration phase. The stub inventory for Phase 00.2.5 is **2 production stubs + 3 production callers + 2 test files**, not the 3 that the phase-spec implies — `_stubs/rls.py` was never created because the real impl landed in the same PR.

The founder's confidence to open Phase 00.2.5 is justified. Recommended sequence:

1. Land M-2 + M-3 as a single 5-minute "docs(planning): post-merge stale-references cleanup" commit (or fold into PR #30 if still open).
2. Merge PR #30.
3. Open `claude/phase-00-2-5-integration` worktree per HANDOFF.md:99-111 with the brief amended per M-1 (pass session + email_localpart at the `provision_initial_workspace` call site).
4. Track A-1 through A-12 as the Phase 00.2.5 backlog.

Key evidence files:
- `backend/tests/audit/test_emit_audit_event_stub_compat.py:1-91` (formal superset proof for audit stub)
- `backend/src/multitenancy/services/workspace_service.py:7-12,135-225` (signature delta + idempotency contract)
- `backend/migrations/versions/_shared/0001_init.py:43-44` + chain (root migration; all other branches verified)
- `.planning/_session-context/AUDIT-2026-05-19/AUDIT-REPORT.md:7-30` (pre-merge audit verdict matches this post-merge re-verification)
