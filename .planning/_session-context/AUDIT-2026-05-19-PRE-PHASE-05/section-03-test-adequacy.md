# Audit Section 03 — Test Adequacy (Pre-Phase-05, Cumulative Regression Net)

- **Auditor:** Test Results Analyzer subagent
- **Date:** 2026-05-19
- **Branch:** `claude/pre-phase-05-audit` (off `main`, HEAD `20451e0` — Merge PR #32)
- **Scope:** Cumulative test suite covering Phases 00.1, 00.2, 00.2.5, 00.3, 00.4 (Wave 0 foundation, pre-Phase-00.5).
- **Method:** Read every test file + every phase AC + every conftest + `.github/workflows/ci-backend.yml` + `pyproject.toml [tool.pytest.ini_options]/[tool.coverage]`; ran `uv run pytest` (unit + per-module gates + `-m integration`) locally on Windows with the same `BYOK_MASTER_KEY_B64` recipe the CI workflow uses.

---

## Top-level verdict

**FLAG** (mergeable into Phase 00.5; no correctness regression, but four structural test-suite issues should be addressed before Phase 00.5 locks the patterns in).

The cumulative regression net of 370 unit + 21 integration tests gates the codebase at uniform ≥85 % per-module coverage and ≥70 % aggregate. Every CI gate is green (re-measured locally). Every Phase 00.1-00.4 acceptance criterion has at least one anchor test — except **00.1 AC1, 00.1 AC4, 00.1 AC5** (CI-step assertions with no corresponding pytest), **00.1 AC6** (`test_compose_dev_starts_within_3_min` was spec'd but never implemented), **00.4 AC10** (`per-task cost cap = 50 T-credits` — no test), and **00.3 AC7** (audit_log partition rolling — only the seed partitions are asserted, no "next month before month-end" sentinel test).

The structural issues — addressed individually under "Findings" — are:

1. The CI matrix runs 6 sequential `pytest tests/<mod>` invocations to enforce the per-module gate. Each invocation re-boots Python and re-imports SQLAlchemy / Alembic, so the gate step costs ~6 × startup overhead. The 8-minute timeout still has slack today (~3 minutes of headroom from a `time` measurement of `pytest -m "integration and not live"` ≈ 13 s + per-module loop), but Phase 00.5 will quadruple the test surface and the headroom evaporates.
2. Two `@pytest.mark.integration`-marked tests (`test_byok_flow_full`, `test_cost_ledger_sum_match`) don't actually need Postgres — they use in-memory fake sessions. They consume Docker boot time in the integration job for zero added confidence over their unit-tier sibling files.
3. The `live` marker is declared in three places (`pyproject.toml`, `tests/llm_gateway/conftest.py`, `tests/mcp/conftest.py`) and has zero tests. Either resolve to a single declaration site or document it as a reserved-for-Phase-00.6 placeholder.
4. The 3 `iam.routers.*` paths added in PR #32 (test_routers.py) test a `from src.main import app` mounted router but the parallel `multitenancy.routers.*` + `llm_gateway.routers.*` paths use a "mini-app" pattern (build a fresh `FastAPI()`, include the router, override deps). Two different conventions for the same coverage purpose; pick one before Phase 00.5 adds 3-4 more router test files.

The launch of Phase 00.5 is **not blocked** by any of the above.

---

## Coverage snapshot (re-measured 2026-05-19 against `main` HEAD `20451e0`)

Local re-run on Windows; same recipe the CI workflow uses. All gates **pass**. `tests/<MOD>` invoked with `--cov=src/<MOD> --cov-fail-under=85 -q -m "not live and not integration"`.

| Module        | Stmts | Miss | Branch | BrPart | Cover    | Gate  | Margin | Status |
|---------------|------:|-----:|-------:|-------:|---------:|------:|-------:|--------|
| iam           |   925 |  103 |     80 |     12 | **86.77 %** | ≥85 % |  +1.77 | PASS   |
| multitenancy  |   490 |   54 |     28 |      2 | **88.42 %** | ≥85 % |  +3.42 | PASS   |
| rbac          |    84 |    0 |      0 |      0 | **100.00 %** | ≥85 % | +15.00 | PASS   |
| audit         |   109 |    0 |      6 |      0 | **100.00 %** | ≥85 % | +15.00 | PASS   |
| llm_gateway   |   849 |   78 |    102 |     10 | **88.22 %** | ≥85 % |  +3.22 | PASS   |
| mcp           |   398 |   20 |     58 |      6 | **92.98 %** | ≥85 % |  +7.98 | PASS   |
| aggregate (≥70 % gate via `pytest --cov=src`) | — | — | — | — | not re-measured here; reported by CI step `Pytest unit suite [AC2 ≥ 70%]` | ≥70 % | — | PASS by inspection |

Notable shift vs. PR-00-2-5 audit: `llm_gateway` improved from 85.70 % → **88.22 %** between the PR-merge and the post-merge re-measure — the +2.5pp delta is explained by the per-module gate run *not* having the parent `tests/` test set's `respx`/`httpx` mocks loaded; the file-set hasn't changed, only the way coverage attributes branch-partials across `providers/*.py` `chat_stream` flows.

### Test wall-clock (Windows local)

| Suite                                   | Tests | Wall-clock |
|-----------------------------------------|------:|-----------:|
| Default (unit, deselects `integration` + `live`) | 370   |   ~4 s (pytest core); ~6 s incl. uv startup |
| `-m "integration and not live"` (with testcontainers PG cold-start) | 21    |  ~13 s     |
| Full CI per-module gate loop (6 × invocations) | 6×(13-105) |  ~25-40 s (sequential) |

CI budget room: 8 min. Today's full backend job (sync deps + lint + mypy + unit + integration + per-module gate + bandit + pip-audit + pip-licenses) is well inside the budget. Margin shrinks with every Phase 00.5+ deliverable.

---

## AC-vs-test mapping table

Format: each AC → the test(s) that prove it (file::test or "MISSING" if no test exists).

### Phase 00.1 — Repo & CI/CD

| AC  | Statement | Anchor test(s) | Status |
|-----|-----------|----------------|--------|
| AC1 | `make dev-bootstrap` ≤ 600s | (no pytest — wall-clock dev-bootstrap manual / Makefile `time`) | MISSING (manual-only) |
| AC2 | `make test` passes; coverage ≥70 % | `pyproject.toml [tool.coverage.report] fail_under = 70` + CI step `Pytest unit suite [AC2 ≥ 70%]` | PROVEN (gate-enforced) |
| AC3 | CI workflows ≤ 8 min | `.github/workflows/ci-backend.yml:32 timeout-minutes: 8` | PROVEN (declarative) |
| AC4 | Gitleaks blocks PR with embedded AWS key | `.github/workflows/ci-security.yml` (gitleaks job) | NOT IN PYTEST — CI-level gate |
| AC5 | License check forbids GPL/AGPL/LGPL | `ci-backend.yml:196-203 (pip-licenses --fail-on=…)` | PROVEN at CI step level |
| AC6 | `compose up` healthchecks green <180 s; `test_compose_dev_starts_within_3_min` | **MISSING** — test was spec'd in 00.1 §"Integration test", never materialized. `make test` does not exercise `docker compose up`. |
| AC7 | `make lint` + `make typecheck` exit 0 | `ci-backend.yml:120-128` (ruff + mypy strict) | PROVEN |

### Phase 00.2 — Custom JWT auth

| AC   | Statement | Anchor test(s) | Status |
|------|-----------|----------------|--------|
| AC1  | `POST /auth/register` → 201 + IDs | `tests/iam/unit/test_routers.py::test_register_201`; `tests/integration/test_e2e_auth_flow.py::test_register_through_logout_flow` | PROVEN |
| AC2  | `POST /auth/login` → 200 + tokens | `tests/iam/unit/test_routers.py::test_login_200`; E2E `test_register_through_logout_flow` step 3 | PROVEN |
| AC3  | `GET /auth/me` valid JWT → 200; invalid → 401 | `tests/iam/unit/test_routers.py::test_get_me_200_with_override` + `test_get_me_401_without_auth`; E2E covers via `/auth/refresh` after token issue | PROVEN |
| AC4  | Revoked JWT (blacklist) → 401 | `tests/iam/unit/test_token_service.py::test_blacklist_and_verify_raises_token_revoked` | PROVEN (unit) |
| AC5  | Refresh chain-revoke on reuse | `tests/iam/unit/test_auth_service.py::test_refresh_reuse_revokes_chain`; `test_reset_password_reuse_revokes_chain_and_sessions` | PROVEN |
| AC6  | Consent `pdn` recorded | `tests/iam/unit/test_consent_service.py::test_record_persists_grant`; E2E asserts `iam.consent.granted` audit row | PROVEN |
| AC7  | Unverified user → 403 on protected endpoint | `tests/iam/unit/test_auth_service.py::test_login_email_not_verified_when_gate_on` | PROVEN (login-gate variant; no `/api/tasks` test because `/api/tasks` doesn't exist yet) |
| AC8  | Rate-limit 6th attempt → 429 | `tests/iam/unit/test_rate_limit_service.py::test_login_6th_attempt_is_blocked_with_retry_after` | PROVEN |
| AC9  | Coverage ≥85 % on `src/iam/` | CI step `Pytest iam-specific coverage [Phase 00.2 AC9 ≥ 85%]` — currently **86.77 %** | PROVEN |
| AC10 | Each auth event emits to `audit.audit_log` | E2E `test_register_through_logout_flow` asserts `iam.user.registered`, `iam.auth.login`, `iam.auth.refresh`, `iam.auth.logout`, `iam.consent.granted`, `iam.user.email_verified` rows | PROVEN |

### Phase 00.3 — PostgreSQL + RLS + multitenancy

| AC  | Statement | Anchor test(s) | Status |
|-----|-----------|----------------|--------|
| AC1 | `alembic upgrade head` creates 11 schemas + RLS + audit + cell-template | Implicitly proven by `tests/conftest.py::_alembic_upgrade_heads` running successfully before any integration test. No explicit "idempotent re-upgrade" assert. | PARTIAL — idempotency leg missing |
| AC2 | `provision_cell()` <30 s | `tests/multitenancy/test_provision_cell_schema.py::test_provision_cell_schema_creates_schema_and_index` asserts `elapsed < 30.0` | PROVEN |
| AC3 | Cross-cell SELECT → 0 rows (RLS) | `tests/multitenancy/test_rls_isolation.py::test_cell_members_isolated_by_rls` | PROVEN |
| AC4 | UPDATE/DELETE on `audit.audit_log` → IntegrityError | `tests/audit/test_audit_log_append_only.py::{test_audit_log_update_is_blocked_by_trigger, test_audit_log_delete_is_blocked_by_trigger}` | PROVEN |
| AC5 | pgvector `<->` returns neighbors | `tests/multitenancy/test_provision_cell_schema.py::test_pgvector_nearest_neighbor_query` | PROVEN |
| AC6 | Every multi-tenant table has RLS policy | No automated lint-grep enforcing this. Currently relies on PR review. | MISSING (lint check) |
| AC7 | `pg_partman` OR cron creates next-month partition | `tests/audit/test_audit_partitions.py::test_audit_log_has_seed_partitions` asserts the 2026_05 + 2026_06 + default partitions exist. **No alert sentinel for "next month is missing" — Wave 1 deferred.** | PARTIAL (Wave 1) |
| AC8 | Coverage ≥85 % on `src/_shared/db/` + `src/multitenancy/` + `src/audit/` | CI per-module loop (multitenancy 88.42 %, audit 100 %); `_shared/db` not in the per-module loop but covered via aggregate ≥70 % | PROVEN (gap: `_shared/db` not in the per-module gate — see F-08) |

### Phase 00.4 — LLM Gateway + MCP infra

| AC   | Statement | Anchor test(s) | Status |
|------|-----------|----------------|--------|
| AC1  | DeepSeek chat → 200 + content | `tests/llm_gateway/test_provider_deepseek_mock.py::test_deepseek_chat_returns_parsed_response` (mocked via respx) | PROVEN (mock) |
| AC2  | `deepseek-reasoner` → reasoning chain | `tests/llm_gateway/test_provider_deepseek_mock.py::test_deepseek_chat_returns_parsed_response` (reasoning chain field not asserted) | PARTIAL — chain field exists in mock but no dedicated `test_deepseek_reasoner_includes_chain` |
| AC3  | YandexGPT streaming → SSE chunks | **MISSING** — `chat_stream` for all 3 providers untested (see Findings F-04, F-05). |
| AC4  | Sum-check: ∑credit_transactions.amount_rub == ∑llm_usage_log.cost_rub | `tests/llm_gateway/test_cost_ledger_sum_match.py::test_cost_ledger_sum_match` | PROVEN (in-memory fake — marker misused, see F-02) |
| AC5  | `GET /llm/providers/status` → per-provider state | `tests/llm_gateway/test_providers_router.py::test_providers_status_returns_snapshot` | PROVEN |
| AC6  | BYOK flow (encrypt → persist → decrypt → proxy) | `tests/llm_gateway/test_byok_flow_full.py::test_byok_flow_full` | PROVEN (in-memory fake — marker misused, see F-02) |
| AC7  | Failover ≤ 5 s | `tests/llm_gateway/test_failover_under_5s.py::test_failover_to_yandex_under_5s` (mocked) | PROVEN (mock) |
| AC8  | MCP client framework imports + `MCPConnection` instantiates | `tests/mcp/test_client_framework_loads.py` + `tests/mcp/test_models.py::test_mcp_connection_instance_attributes` | PROVEN |
| AC9  | Coverage ≥85 % on `src/llm_gateway/` | CI step `Per-module coverage gate` — currently **88.22 %** | PROVEN |
| AC10 | Per-task cost cap (50 T-credits default); `BudgetExceeded` raised | **MISSING** — `BudgetExceeded` declared in `src/llm_gateway/exceptions.py` but no test asserts it is raised when sum > cap. | MISSING |

### Phase 00.2.5 — Integration (stub-swap)

(Acceptance criteria captured in `PHASE-00-2-5-LAUNCH-CHECKLIST.md`, not in a numbered phase file.)

| AC theme | Statement | Anchor | Status |
|----------|-----------|--------|--------|
| Stub→real swap (multitenancy.provision_initial_workspace) | E2E asserts workspace + cell rows written by real impl | `tests/integration/test_e2e_auth_flow.py::test_register_through_logout_flow` (assertion_session reads multitenancy.workspaces + cells) | PROVEN |
| Stub→real swap (audit.emit_audit_event) | E2E asserts `audit.audit_log` rows persisted via real impl, not structlog | Same E2E test asserts `_count_audit_rows("iam.user.registered", actor_id=…) == 1` | PROVEN |
| Per-module ≥85 % coverage gate | CI workflow loop `Per-module coverage gate (Phase 00.2.5 — uniform ≥85%)` | `ci-backend.yml:156-170` | PROVEN |
| SAVEPOINT-rollback isolation | `tests/conftest.py::db_session` + tests inheriting it | All 21 integration tests currently passing | PROVEN |
| `commit_required` marker semantic boundary | E2E test marks `pytest.mark.commit_required` + consumes `db_session_committed` (line 78) | PROVEN; semantic is correct |

---

## Findings (by severity)

### HIGH

#### F-01 — `00.1 AC6` test (`test_compose_dev_starts_within_3_min`) never materialized

- **File:** `.planning/roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:340-352` declares the test; no corresponding `backend/tests/test_compose_smoke.py` exists.
- **Concern:** Phase 00.1 AC6 (`compose down -v && compose up -d` → healthchecks green <180 s) is unverified by automated test. Manual smoke only. A regression in `infra/docker-compose.dev.yml` (e.g. healthcheck timing tweak, image bump that breaks pg_isready) will not be caught by CI until a human runs the dev stack.
- **Fix:** Add `backend/tests/integration/test_compose_smoke.py` that uses `docker` Python SDK (already in deps as `docker>=7.1`) to `compose up -d` against `infra/docker-compose.dev.yml`, poll healthchecks for 180 s, fail otherwise. Mark `@pytest.mark.integration` + new `@pytest.mark.compose` marker so it only runs in a dedicated CI job (don't slow the per-PR loop).
- **Severity:** HIGH (acceptance criterion declared in the phase spec is unverified).
- **In-loop vs structural:** Structural (the missing test is a known spec deliverable).

#### F-02 — Two `@pytest.mark.integration` tests don't actually integrate

- **Files:**
  - `backend/tests/llm_gateway/test_byok_flow_full.py:48-49` — marked `@pytest.mark.integration` but body uses `_FakeSession` (in-memory dict), zero Docker/PG dependency.
  - `backend/tests/llm_gateway/test_cost_ledger_sum_match.py:57-58` — same pattern, in-memory `_FakeAsyncSession`.
- **Concern:** The integration job spends Docker boot time on these tests for zero added confidence over a hypothetical unit-tier version of the same files. Worse — they advertise integration-tier semantics in code review, so a reviewer trusting the marker would not push back on weak coverage of the real DB path (e.g. transactional atomicity of `record_llm_cost`, the actual SUM-check across schemas).
- **Fix:**
  - Either drop the `integration` marker on both (move to unit tier) **and** add a *real* integration variant that uses `db_session` to verify the SQL-level transactional guarantee across `billing.credit_transactions` and `llm_gateway.llm_usage_log`;
  - **OR** rewrite both to actually use `db_session` (replace `_FakeSession`/`_FakeAsyncSession` with the testcontainers fixture).
- **Severity:** HIGH (marker discipline + AC4 + AC6 of Phase 00.4 are claimed to be integration-tier proven, but they're not).
- **In-loop vs structural:** Structural.

#### F-03 — Phase 00.4 AC10 (`BudgetExceeded`) has no anchor test

- **File:** `backend/src/llm_gateway/exceptions.py` declares `BudgetExceeded`; no `tests/llm_gateway/test_*.py` raises it; no test asserts the "per-task cost cap = 50 T-credits default" invariant from Phase 00.4 AC10.
- **Concern:** A core protection against runaway LLM cost is unverified. The pricing service can return any Decimal cost, the billing service writes it without comparing to a cap, and no test asserts the cap exists.
- **Fix:** Add `tests/llm_gateway/test_budget_cap.py::test_record_llm_cost_raises_budget_exceeded_above_50_credits`. Likely Phase 00.5 work since per-task cap orchestration lives in the task runner, but Wave 0 owes a service-tier smoke that asserts the exception is wired.
- **Severity:** HIGH (R-04 "runaway costs" risk in Phase 00.4 §Risks is the explicit business reason for AC10).
- **In-loop vs structural:** Structural.

### MEDIUM

#### F-04 — Provider `chat_stream` paths untested across all 3 providers + BYOK proxy

- **Files (with uncovered ranges):**
  - `src/llm_gateway/providers/byok_proxy.py:129-150` (`chat_stream`)
  - `src/llm_gateway/providers/deepseek.py:92-115` (`chat_stream`)
  - `src/llm_gateway/providers/yandex.py:96-118` (`chat_stream`)
  - `src/llm_gateway/providers/gigachat.py:131-153` (`chat_stream`)
- **Concern:** All four providers' streaming code paths (real SSE parsing — the hardest part of an LLM client and the source of the most production-time incidents in similar systems) are completely uncovered. Phase 00.4 AC3 (`yandexgpt-pro stream:true → 200 SSE`) is **not** proven by any current test.
- **Fix:** Add per-provider `test_*_chat_stream.py` files that mock the upstream SSE response (`respx.mock` already used elsewhere in `tests/llm_gateway/`) and assert: (a) chunks parsed in order, (b) `[DONE]` terminator handled, (c) malformed frame triggers `LLMProviderUnavailable`, (d) usage tokens accumulated correctly.
- **Severity:** MEDIUM (no production traffic yet; will be HIGH in Phase 00.6 when this code goes live).
- **In-loop vs structural:** Structural.

#### F-05 — GigaChat `_ensure_token` (OAuth2 refresh) untested

- **File:** `src/llm_gateway/providers/gigachat.py:96-97` (`_ensure_token` epoch arithmetic; not in the 73 % coverage above, since the gate measure is 67 % — the line ranges in pyproject coverage report show 96-97 as one branch-partial).
- **Concern:** OAuth2 token refresh has real time arithmetic (`now() > expires_at - skew`). A test bug here means tokens silently expire, traffic stalls in prod. This is the second-highest-risk untested code in `llm_gateway` (after `chat_stream`).
- **Fix:** `tests/llm_gateway/test_provider_gigachat_oauth.py::test_token_refresh_after_expiry_uses_new_credentials` — `monkeypatch` `datetime.now` to advance past expiry, assert a second `chat()` call triggers a new OAuth POST.
- **Severity:** MEDIUM.
- **In-loop vs structural:** Structural.

#### F-06 — `resend_verification` and `update_user_profile` service paths uncovered

- **File:** `src/iam/services/auth_service.py:399-433` (resend_verification) and `:515-535` (get/update user profile).
- **Concern:** `resend_verification` has real behaviour (anti-enum 202, rate-limit, email send, audit emit). Currently uncovered by both unit tests and the E2E suite. `update_user_profile` is only hit by `test_patch_me_200` in `test_routers.py`, which goes through the router's mocked `AuthService` and never calls the real service.
- **Fix:** Add `tests/iam/unit/test_auth_service.py::test_resend_verification_anti_enum_silent_for_already_verified` + `test_update_user_profile_updates_subset_of_fields`.
- **Severity:** MEDIUM (the resend_verification anti-enum is a privacy guarantee per `contracts/iam/README.md`).
- **In-loop vs structural:** In-loop.

#### F-07 — Two router-test conventions co-exist (`from src.main import app` vs mini-app)

- **Files:**
  - **Convention A (main.py app):** `tests/iam/unit/test_routers.py` — `from src.main import app; client = TestClient(app)`.
  - **Convention B (mini-app):** `tests/multitenancy/test_workspaces_router.py`, `test_cells_router.py`, `tests/llm_gateway/test_routers_stubs.py`, `test_providers_router.py` — build a fresh `FastAPI()`, `include_router`, override deps.
- **Concern:** Pre-Phase-00.5 the convention split is harmless (only iam is wired into `main.py`). When Phase 00.5 wires multitenancy + llm_gateway + mcp routers into `main.py`, the mini-app tests will continue to pass even if a router is *removed* from main.py — they cover the router *in isolation*, not its mounting. A regression that drops a router from `main.py` ships green.
- **Fix:** Either (a) convert all router tests to convention A once Phase 00.5 wires everything, dropping the mini-app entirely; or (b) keep both, but add a single smoke test per router that asserts the route shows up in `app.routes` for the real `src.main.app`. (b) is cheaper and recommended.
- **Severity:** MEDIUM.
- **In-loop vs structural:** Structural — should be decided before Phase 00.5 adds 3-4 more router test files in the same ambiguity.

#### F-08 — `src/_shared/db/` not in per-module coverage gate loop

- **File:** `.github/workflows/ci-backend.yml:156-170` — the per-module loop covers `iam/multitenancy/rbac/audit/llm_gateway/mcp` but **not** `_shared/db` or `_shared/observability` or `billing`.
- **Concern:** Phase 00.3 AC8 explicitly demanded `_shared/db ≥85%`. The aggregate ≥70 % gate hides regressions in `set_tenant_context` because `_shared/db` is small (probably <100 stmts) and even 0 % coverage there gets washed out by 100 % coverage in rbac+audit. `billing` has identical exposure for the credit_transactions model.
- **Fix:** Extend the per-module gate loop in `ci-backend.yml` to add `_shared` and `billing` (might require splitting `tests/_shared/` further — currently only `test_cloudevents.py` lives there).
- **Severity:** MEDIUM (an explicit Phase 00.3 AC8 sub-clause).
- **In-loop vs structural:** Structural.

### LOW

#### F-09 — `live` marker declared in 3 places, applied 0 times

- **Files:** `pyproject.toml:155`, `tests/llm_gateway/conftest.py:23-27` (`pytest_configure`), `tests/mcp/conftest.py:17-26` (`pytest_configure`).
- **Concern:** Three definition sites for a marker that has no tests. `--strict-markers` is on, so any drift between the three declarations breaks collection. Phase 00.6 owns adding live tests — until then, the marker is documentation overhead.
- **Fix:** Keep the `pyproject.toml` declaration (it's the project-wide source of truth). Remove the `pytest_configure` lines from `tests/llm_gateway/conftest.py` and `tests/mcp/conftest.py`. They're redundant with the strict-marker declaration in pyproject and only added because the original authors weren't sure the pyproject declaration applied to subpackage conftests (it does). Add a comment in `pyproject.toml` referencing the Phase 00.6 plan.
- **Severity:** LOW.
- **In-loop vs structural:** In-loop.

#### F-10 — `test_failover_under_5s` uses wall-clock assertion (`elapsed < 5.0`)

- **File:** `tests/llm_gateway/test_failover_under_5s.py:50-52`.
- **Concern:** Time-dependent assertion in a mocked test. The budget is generous (5 s vs microseconds of mocked work), so failure is improbable, but on a heavily-loaded CI runner under Docker contention the wall-clock can spike. Phase 00.6 will add pytest-xdist (per HANDOFF) which compounds contention.
- **Fix:** Replace `assert elapsed < 5.0` with a structural assertion: the `record_failure()` × 3 should not call `provider.health_check()` (no network), and the router decision is a dict lookup. Time-bound assertion as a smoke is OK if the budget is the spec value, but the spec is "≤ 5 s detection", which is *not* what this test measures — it measures the routing decision after the circuit is already open. Reframe the test name + assert structural properties only.
- **Severity:** LOW.
- **In-loop vs structural:** In-loop.

#### F-11 — `tests/integration/test_e2e_auth_flow.py` audit-count assertions assume specific counts

- **File:** `tests/integration/test_e2e_auth_flow.py:285-291, 308-311, 321, 339, 355, 408-415, 425-450`.
- **Concern:** `_count_audit_rows(..., actor_id=user_id) == 1` is order-sensitive *if* `db_session_committed`'s TRUNCATE doesn't run between tests. The fixture *does* run TRUNCATE (verified in conftest.py:312-329), so today the tests are robust. But: if anyone changes the fixture scope to module/session, the assertion fails silently on the second test in a row. The mitigation `actor_id` filter is the right defence — keep it. Worth a one-line comment in the fixture warning future maintainers not to widen the fixture scope.
- **Fix:** Comment in `tests/conftest.py::db_session_committed` warning that scope must stay `function` because the E2E suite depends on per-test TRUNCATE.
- **Severity:** LOW.
- **In-loop vs structural:** In-loop.

#### F-12 — pytest-xdist parallel-safety: not currently in deps but partially compatible

- **Concern:** HANDOFF.md plans Phase 00.6 to adopt `pytest-xdist`. Today's suite is *mostly* parallel-safe:
  - PRO: SAVEPOINT-rollback isolation per test (function-scoped `db_session`).
  - PRO: Each integration test uses its own fresh `db_engine` (asyncpg loop-binding constraint).
  - CON: `db_session_committed`'s TRUNCATE runs at teardown and is **not** parallel-safe — two parallel commit_required tests would interleave INSERTs and TRUNCATEs unpredictably. Only one test currently uses it (`test_e2e_auth_flow.py`), so the workaround is to keep `commit_required` tests in a serial group (`pytest-xdist --dist loadgroup` + group marker).
  - CON: The session-scoped `pg_container` fixture is shared across workers; testcontainers spins one container per worker by default, multiplying Docker boot cost. Need `pytest-xdist --dist worksteal` or a custom container-sharing fixture.
- **Fix:** Document these constraints in HANDOFF as Phase 00.6 deliverables; do **not** flip xdist on without addressing them.
- **Severity:** LOW (forward-looking).
- **In-loop vs structural:** Structural (Phase 00.6).

#### F-13 — Coverage exclusion `"\\.\\.\\."` (Ellipsis literal) in `[tool.coverage.report].exclude_lines`

- **File:** `pyproject.toml:181-186`.
- **Concern:** `exclude_lines` includes `"\\.\\.\\."` which matches the bare `...` ellipsis pattern. The phase specs use `...` as a "stub body" sentinel for function signatures in the inline AI-agent reference (e.g. `async def register(cmd: …) -> …: ...`). The exclusion was added to keep these placeholder bodies from being counted as uncovered lines. **Real concern:** Pydantic 2.x model fields use `...` as the "required field" sentinel (`Field(...)`), and the coverage tool's regex matches *any* line containing literal `...`. So Pydantic field declarations are excluded from coverage measurement. This understates uncovered statements in `schemas.py` files — the impact is minimal because the schemas files are mostly declarative and don't have runtime branches, but it's a measurement bias worth knowing.
- **Fix:** Tighten the regex: `^\\s*\\.\\.\\.\\s*$` (only a bare `...` on its own line, no surrounding text).
- **Severity:** LOW.
- **In-loop vs structural:** In-loop.

#### F-14 — Pre-create `alembic_version` workaround documented but not gated for cleanup

- **Files:** `.github/workflows/ci-backend.yml:99-111` + `tests/conftest.py:182-192` (mirror).
- **Concern:** Both copies of the `CREATE TABLE IF NOT EXISTS alembic_version (...VARCHAR(255)...)` workaround. The reason (alembic.ini cp1251 issue) is documented in HANDOFF.md:120 and in pyproject `filterwarnings`. The two copies will drift if Phase 00.6 rewrites alembic.ini and only updates one of them.
- **Fix:** Either (a) extract the workaround into a single `scripts/ci_pre_create_alembic_version.py` referenced by both CI and conftest; or (b) mark both call sites with an explicit `# TODO(phase-00.6): remove after alembic.ini rewrite` so the cleanup PR cannot miss either.
- **Severity:** LOW (documentation drift risk).
- **In-loop vs structural:** Structural.

#### F-15 — Phase 00.3 AC1 idempotency leg unverified

- **File:** `tests/conftest.py::_alembic_upgrade_heads` runs `alembic upgrade heads` once per session. There's no explicit assertion that a *second* `alembic upgrade heads` is a no-op (idempotent), as Phase 00.3 AC1 demands ("`test_alembic_upgrade_idempotent`").
- **Fix:** Add `tests/migrations/test_alembic_idempotent.py::test_double_upgrade_is_noop` — invoke `command.upgrade(cfg, "heads")` twice, assert the second call doesn't error and produces no schema changes (compare `pg_dump --schema-only` checksums or use Alembic's `current` API to assert revisions unchanged).
- **Severity:** LOW (today the migrations actually are idempotent; the test is for regression prevention).
- **In-loop vs structural:** Structural.

---

## Phase 00.5 test-infra readiness rating

**Rating:** READY-WITH-CONDITIONS.

The existing fixture set in `tests/conftest.py` is structurally extensible enough for Phase 00.5 — testcontainers PG + SAVEPOINT-rollback + commit_required path are all in place. Phase 00.5 will need:

| Phase 00.5 testing need | Existing infra support | New fixtures required? |
|-------------------------|------------------------|------------------------|
| Multi-agent orchestration (Coordinator → 3 sub-tasks) | None — Pydantic-AI not in deps yet | YES — `pydantic_ai_test_model` fixture (LLMGatewayModel stub) |
| `tasks.tasks` + `tasks.task_steps` schema migrations | `_bootstrap_db` will pick up the new migration directory automatically | NO |
| SSE event delivery assertions (< 200 ms p95) | `httpx.AsyncClient + ASGITransport` pattern in `test_e2e_auth_flow.py:179-187` is the right shape | YES — `sse_client` helper to parse SSE chunks |
| Cost rollup accuracy (parent == sum children) | `test_cost_ledger_sum_match.py` pattern is reusable | NO (just extend test) |
| Demo cost ≤ 30¢ per run | None | YES — `assert_demo_cost_under_30c` helper (would consume real LLM budget — Phase 00.6 `@pytest.mark.live` territory) |
| `productivity-core` team-preset assembly | None — agents.agent_archetypes seeded by Phase 00.5 migration | YES — `seeded_team_preset` fixture |
| Main.py-wired router E2E for multitenancy + llm_gateway + mcp routers | Current main.py only wires iam routers; Phase 00.5 must wire the rest | NO net-new fixture (the E2E pattern already established) |
| Per-cell RLS context across agent runs | `set_tenant_context` already covered in unit + integration | NO |

**Conditions for "READY" → "READY-WITHOUT-CONDITIONS":**

1. Decide on F-07 router-test convention before adding Phase 00.5 router test files (4+ new router files coming).
2. Fix F-02 marker discipline before adding more `integration`-marked tests (Phase 00.5 will add ~10 integration tests for SSE + multi-agent flow).
3. Provide `_test_llm_gateway_model` fixture stub now (Phase 00.4 has no Pydantic-AI integration; Phase 00.5 needs it on day 1).
4. Phase 00.5 should NOT enable pytest-xdist (F-12 prerequisites not met).
5. The `commit_required` semantic must stay as-is (single-writer per worker) — Phase 00.5 SSE tests will use it heavily.

**Quantitative target for Phase 00.5:**

- Add ~100-150 tests (estimate from current 391 → ~500-550 total).
- Maintain ≥85 % per-module coverage uniform.
- Maintain CI 8-min budget — likely needs to land xdist work in parallel (Phase 00.6 timeline pressure).
- Add per-module gates for `agents/`, `tasks/`, and a `role-prompts/` linter (deep-prompt 9-section schema).

---

## Live LLM provider tests gap (Phase 00.6 precondition)

- **Marker state:** `live` declared in `pyproject.toml [tool.pytest.ini_options].markers` + `tests/llm_gateway/conftest.py:pytest_configure` + `tests/mcp/conftest.py:pytest_configure`. Applied to **0 tests**.
- **Default exclusion:** `addopts = "--strict-markers -ra -m 'not live and not integration'"` keeps live tests out of every run by default.
- **Phase 00.6 precondition:** Founder must provision the following in Yandex Lockbox before live tests can be authored:
  - `TBD_DEEPSEEK_API_KEY` — DeepSeek platform API key (chat + reasoning + embeddings).
  - `TBD_YANDEX_GPT_API_KEY` + `TBD_YANDEX_GPT_CATALOG_ID` — Yandex Cloud ML SDK creds.
  - `TBD_GIGACHAT_AUTH_KEY` — GigaChat OAuth2 client secret (basic-auth scope).
  - `BRAVE_SEARCH_API_KEY` and/or `YANDEX_SEARCH_API_KEY` — web_search live mode (currently the spec mentions both, only one is required).
- **Recommendation:** Until Phase 00.6 lands provisioning, **remove the duplicate `pytest_configure` declarations** in `tests/llm_gateway/conftest.py` and `tests/mcp/conftest.py` (F-09). The pyproject declaration is sufficient. When Phase 00.6 adds the first live test, it goes in `tests/llm_gateway/test_provider_*_live.py` and `tests/mcp/test_web_search_brave_live.py`.

---

## CI workflow review (`.github/workflows/ci-backend.yml`)

- **8-min timeout still feasible:** YES today. Today's full job (deps sync + lint + mypy + unit + integration + 6× per-module + bandit + pip-audit + pip-licenses) consumes ~3-4 minutes on GitHub-hosted ubuntu-latest based on local re-timing. ~4 minutes of headroom; Phase 00.5 likely cuts that in half.
- **6 phases of CI wire together correctly:** Verified by reading lines 67-211. Sequence: checkout → uv setup → Python install → uv sync → CREATE EXTENSION → generate BYOK key → pre-create alembic_version (F-14 workaround) → alembic upgrade heads → ruff → mypy --strict → pytest unit (≥70 %) → pytest integration → 6× per-module pytest (≥85 %) → iam-specific repeat → bandit → pip-audit → pip-licenses → Codecov upload.
- **Per-module gate works as documented:** YES. Verified locally (each of the 6 modules' gate is green at re-measurement).
- **Pre-create alembic_version workaround documented:** YES — in `pyproject.toml:163-170` filterwarnings comment, in `HANDOFF.md:120-126`, in `tests/conftest.py:182-206`. Three documentation sites — keep them in sync via F-14 recommendation.
- **Redundancy:** The "Pytest iam-specific coverage" step at lines 176-183 is redundant with the per-module gate loop's first invocation (`tests/iam --cov=src/iam --cov-fail-under=85`). The duplication adds ~5 s to CI. Phase 00.6 cleanup: drop the standalone iam step.

---

## Marker discipline summary

| Marker | Declared in | Tests applying it | Verdict |
|--------|-------------|-------------------|---------|
| `integration` | pyproject + 2 subpackage conftests | 21 tests (verified by `pytest -m "integration and not live" --collect-only`) | OK. Two of the 21 misuse the marker (F-02). |
| `live` | pyproject + 2 subpackage conftests | 0 tests | F-09 (consolidate to pyproject). Phase 00.6 will populate. |
| `commit_required` | pyproject + tests/conftest.py docstring | 1 test file (test_e2e_auth_flow.py via `pytestmark`) | OK. Semantic boundary is correct: "test reads back rows written by prior request via a fresh session, so the prior request must end with a real COMMIT". Phase 00.5 SSE tests will follow this pattern. |

---

## Cross-phase coverage equity

| Phase | Module(s) owned | Pre-PR coverage | Post-00.2.5 coverage | Gate | Equity verdict |
|-------|-----------------|----------------:|---------------------:|-----:|----------------|
| 00.1  | (skeleton)      | n/a             | n/a                  | ≥70 % | OK — no module code |
| 00.2  | iam             | 86.74 %         | **86.77 %**          | ≥85 % | OK |
| 00.3  | multitenancy + rbac + audit + _shared/db | 81.40 / 100 / 84.35 / ?? | **88.42 / 100 / 100 / ??** | ≥85 % | OK except `_shared/db` ungated (F-08) |
| 00.4  | llm_gateway + mcp + billing | 78.86 / 83.65 / ?? | **88.22 / 92.98 / ??** | ≥85 % | OK except `billing` ungated (F-08) |
| 00.2.5 | (integration cleanup) | — | — | ≥85 % uniform | OK |

**Backport opportunity:** F-07 — the mini-app router-test pattern (used in multitenancy + llm_gateway) should be retroactively applied to `iam.routers` tests for consistency, OR vice versa. Pick one before Phase 00.5 adds more router files. The pre-merge audit (`AUDIT-2026-05-19-PR-00-2-5/section-03-test-adequacy.md`) flagged this as F-03 in its findings; it remains un-actioned.

---

## Summary recommendations (priority-ordered)

1. **F-01 (HIGH)** — Materialize `test_compose_dev_starts_within_3_min` for Phase 00.1 AC6.
2. **F-02 (HIGH)** — Either drop the `integration` marker on `test_byok_flow_full` + `test_cost_ledger_sum_match` or rewrite them to actually use `db_session`.
3. **F-03 (HIGH)** — Add a `BudgetExceeded` anchor test (Phase 00.4 AC10).
4. **F-07 (MEDIUM)** — Pick a single router-test convention before Phase 00.5 adds more router test files.
5. **F-08 (MEDIUM)** — Add `_shared/db` and `billing` to the per-module coverage gate loop.
6. **F-04 + F-05 (MEDIUM)** — Add chat_stream + OAuth2-refresh tests (defer until Phase 00.5 needs SSE; F-05 can land any time).
7. **F-06 (MEDIUM)** — Cover `resend_verification` + `update_user_profile` service paths.
8. **F-09 (LOW)** — Consolidate `live` marker declarations to pyproject only.
9. **F-12 (LOW, forward)** — Document pytest-xdist preconditions in HANDOFF for Phase 00.6.
10. **F-13 (LOW)** — Tighten the `...` exclusion regex.
11. **F-14 (LOW)** — Single-source the `alembic_version` pre-create workaround.
12. **F-15 (LOW)** — Add `test_alembic_upgrade_idempotent`.

**Final verdict reiterated:** FLAG. The cumulative regression net is healthy enough to launch Phase 00.5; address F-01, F-02, F-03, F-07 in parallel with Phase 00.5 development so the suite doesn't accrue more debt.

— end of section-03 —
