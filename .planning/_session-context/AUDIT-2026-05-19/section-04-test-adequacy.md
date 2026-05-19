# Audit Section 4 — Test Results Analyzer

**Auditor:** Test Results Analyzer subagent
**Date:** 2026-05-19
**Scope:** Phase 00.3 + 00.4 test suites (branch `claude/cool-bell-0c74ba`)

## Verdict

**FLAG**

Rationale: All six per-module unit suites are GREEN with zero failures
(76 + 46 + 13 + 23 + 82 + 79 = **319 tests pass, 0 fail, 16 deselected**),
and every module clears the global `fail_under = 70%` gate. The phase-specific
**≥85% gate (00.3 AC8 + 00.4 AC9)**, however, is missed by two modules
(`multitenancy` at 81.4%, `llm_gateway` at 78.9%). Several Phase 00.4 ACs are
covered only via stubs / fake sessions and have no end-to-end integration test
yet; AC10 (per-task cost cap / BudgetExceeded) appears entirely uncovered.
None of these are correctness regressions — they are gate / coverage gaps.

---

## Coverage matrix

Numbers are from `uv run pytest tests/<module> --cov=src/<module> -q -m "not integration"`
(see raw outputs in this audit folder). "AC Gate" is the phase-spec target
(85% for 00.3 + 00.4 modules; rbac+mcp have no explicit gate so 70% global).

| Module | Current % | AC Gate | Status | Top uncovered (file:line) |
|---|---|---|---|---|
| iam        | **86.69%** | ≥85% (00.2) | PASS | `repositories/user_repository.py` 39%; `services/auth_service.py` lines 374-396, 482-501; `deps.py` 35-67 |
| multitenancy | **81.40%** | ≥85% (00.3 AC8) | **MISS** | `routers/cells.py` **0%** (14-227); `routers/workspaces.py` **0%** (3-81); 4 repositories 57-58% (cell, workspace, cell_member); `services/workspace_service.py` 80% (92-94, 110-123) |
| rbac       | **100.00%** | n/a | PASS | none |
| audit      | **84.35%** | ≥85% (00.3 AC8) | **NEAR-MISS** (-0.65pp) | `repositories/audit_repository.py` 44% (lines 46-60, 75-79, 90-97) |
| llm_gateway | **78.86%** | ≥85% (00.4 AC9) | **MISS** | `routers/providers.py` **0%** (3-72); `providers/byok_proxy.py` 40% (78-175); `providers/deepseek.py` 51% (92-115, 127-135); `providers/gigachat.py` 48% (56-153); `providers/yandex.py` 60% (96-118, 144-150) |
| mcp        | **83.65%** | (no explicit gate) | PASS | `tools/read_url.py` 82% (106-113, 219-225, 251-254) |

Combined-suite numbers stay above the `fail_under=70%` global gate enforced
by `pyproject.toml`, so CI is green. But the phase-spec gate is stricter.

---

## Phase 00.3 AC coverage

| AC | Description | Test path | Status |
|---|---|---|---|
| AC1 | `alembic upgrade head` creates all 11 schemas + RLS + audit + cell-template | _no_ `test_alembic_upgrade_idempotent` found in suite (grep `alembic|upgrade_idempotent` → 0 hits) | **MISSING** |
| AC2 | `provision_cell()` <30s + per-cell schema + HNSW | `tests/multitenancy/test_provision_cell_schema.py::test_provision_cell_schema_creates_schema_and_index` (asserts `elapsed < 30.0`) | PASS (integration) |
| AC3 | Cross-cell SELECT returns 0 rows (RLS isolation) | `tests/multitenancy/test_rls_isolation.py::test_cell_members_isolated_by_rls` | PASS (integration; targets `cell_members`, not `tasks` as inline spec hints — acceptable substitute) |
| AC4 | UPDATE/DELETE on `audit.audit_log` → IntegrityError ("append-only") | `tests/audit/test_audit_log_append_only.py::test_audit_log_{update,delete}_is_blocked_by_trigger` + insert sanity | PASS (integration) |
| AC5 | pgvector `<->` cosine returns nearest neighbours | `tests/multitenancy/test_provision_cell_schema.py::test_pgvector_nearest_neighbor_query` | PASS (integration; uses `<=>` not `<->` — same cosine op alias) |
| AC6 | Every multi-tenant table has RLS policy or `BYPASS_RLS_INTENTIONAL` marker | _no_ lint test (grep `BYPASS_RLS_INTENTIONAL` → 0 hits in tests/) | **MISSING** (lint not enforced) |
| AC7 | `pg_partman`/cron creates next-month partition (Wave 0 — sentinel + alert) | `tests/audit/test_audit_partitions.py::test_audit_log_has_seed_partitions` asserts `2026_05`, `2026_06`, `default` partitions exist | PARTIAL (sentinel verified; alert-if-missing-next-partition path not asserted) |
| AC8 | Coverage ≥85% for `_shared/db/`, `multitenancy/`, `audit/` | combined coverage runs above | **PARTIAL**: audit 84.35% (-0.65pp), multitenancy 81.40% (-3.6pp), `_shared/db/` not measured in isolation |

---

## Phase 00.4 AC coverage

| AC | Description | Test path | Status |
|---|---|---|---|
| AC1 | `POST /api/llm/chat/completions {deepseek-chat}` → 200 + content | `tests/llm_gateway/test_provider_deepseek_mock.py::test_deepseek_chat_returns_parsed_response` (provider-level, not router) | **PARTIAL** — provider path tested; router stub returns 501 (`test_chat_completion_stub_returns_501`); no test of live wiring through `/api/v1/llm/chat/completions` returning content |
| AC2 | `{deepseek-reasoner}` → 200 + reasoning chain | grep `deepseek-reasoner` → only `test_router_service` (asserts model name) + `test_cost_ledger_sum_match` (price row). No reasoning-chain assertion. | **MISSING** |
| AC3 | `{yandexgpt-pro, stream:true}` → SSE chunks | grep `stream\|SSE` → only `test_deepseek_mock.py` line 52 (asserts `stream is False`). No streaming test. | **MISSING** |
| AC4 | Every LLM call atomically writes `credit_transactions` + `llm_usage_log`, sums match | `tests/llm_gateway/test_cost_ledger_sum_match.py::test_cost_ledger_sum_match` (in-memory fake session) | PARTIAL (real-PG variant deferred per file docstring; atomicity proven only against fake) |
| AC5 | `GET /api/llm/providers/status` returns per-provider state + circuit | `src/llm_gateway/routers/providers.py` has **0% coverage**, no test exercises this endpoint. `tests/llm_gateway/test_health_service.py` covers the underlying `HealthMonitor` only. | **MISSING** (router untested) |
| AC6 | BYOK store → encrypt → decrypt → proxy call | `tests/llm_gateway/test_byok_flow_full.py::test_byok_flow_full` + `test_byok_service*.py` | PASS (with caveat: uses fake session, not Postgres) |
| AC7 | DeepSeek 3× 503 → circuit OPEN → routes to YandexGPT < 5s | `tests/llm_gateway/test_failover_under_5s.py::test_failover_to_yandex_under_5s` | PASS |
| AC8 | MCP client framework imports + instantiates | `tests/mcp/test_client_framework_loads.py` (5 cases incl. inactive-connection rejection + disconnect idempotency) | PASS |
| AC9 | Coverage ≥85% for `src/llm_gateway/` | 78.86% measured | **MISS** (-6.1pp) |
| AC10 | Per-task cost cap = 50 T-credits default; `BudgetExceeded` if exceeded | grep `BudgetExceeded\|cost_cap\|50.*T-credit` → 0 hits in `tests/`. Exception class exists in `src/llm_gateway/exceptions.py`. | **MISSING** |

---

## Test-quality findings

### Severity: HIGH

1. **Two phase-spec coverage gates are missed.** `multitenancy` 81.40% (gate 85, miss -3.6pp) and `llm_gateway` 78.86% (gate 85, miss -6.1pp). `audit` is 0.65pp short. The `fail_under=70%` in `pyproject.toml` masks this in CI. Either tighten `fail_under` per-module or add a phase gate in CI. (`backend/pyproject.toml:156`)
2. **`src/llm_gateway/routers/providers.py` has 0% coverage** — entire `/api/llm/providers/status` endpoint (AC5) untested. The other LLM stub routers have 501-smoke tests; this one is missing from `test_routers_stubs.py`. (`backend/src/llm_gateway/routers/providers.py:3-72`)
3. **`src/multitenancy/routers/cells.py` 0% + `routers/workspaces.py` 0%** — 88 statements of HTTP surface entirely untested. No FastAPI/`TestClient` tests for cells/workspaces routers. (`backend/src/multitenancy/routers/cells.py:14-227`, `backend/src/multitenancy/routers/workspaces.py:3-81`)
4. **AC10 (`BudgetExceeded` per-task cap) entirely uncovered.** Exception is defined but no test exercises the threshold. Cost-runaway risk R-04 cited in spec is not gated by tests.
5. **AC2 (deepseek-reasoner reasoning chain) and AC3 (Yandex streaming SSE) have no tests.** The `test_provider_deepseek_mock.py::test_deepseek_chat_returns_parsed_response` asserts `body["stream"] is False` — *negation* of streaming, not positive assertion.
6. **AC1 of 00.3 (`alembic upgrade head` idempotent) has no test.** The phase explicitly named `test_alembic_upgrade_idempotent`; no file matches that pattern. Schema-bootstrap regression has no automated detector.

### Severity: MEDIUM

7. **`tests/llm_gateway/test_cost_ledger_sum_match.py` is marked `@pytest.mark.integration` but runs against an in-memory `_FakeAsyncSession`.** The file docstring acknowledges "this unit-tier variant uses an in-memory fake session" but keeps the integration marker "for organisational consistency". This means the `-m "not integration"` filter (default in `pyproject.toml addopts`) **skips the only test that proves atomicity** of the dual-write. Either drop the integration mark (so it runs in the default unit suite — currently deselected) or add a real-PG version. (`backend/tests/llm_gateway/test_cost_ledger_sum_match.py:57-58`)
8. **Same issue for `tests/llm_gateway/test_byok_flow_full.py`** — `@pytest.mark.integration` but uses `_FakeSession`. The file docstring is explicit: "uses an in-memory fake session so it runs in the unit tier, but keeps the integration mark for organisational consistency". AC6 evidence is therefore deselected in the default CI lane. (`backend/tests/llm_gateway/test_byok_flow_full.py:48-50`)
9. **`backend/src/llm_gateway/providers/{byok_proxy,deepseek,gigachat,yandex}.py` have 40-60% coverage.** Streaming paths, error paths and timeout paths are untested. E.g. `gigachat.py` OAuth refresh lines 56-84 are 0% covered.
10. **`backend/src/audit/repositories/audit_repository.py` 44% coverage.** Both the insert (46-60) and the list/query helpers (75-79, 90-97) lack unit tests. The `AuditService` is tested via mocks-of-repository — repository itself is unverified.
11. **structlog global config interference.** `tests/multitenancy/test_events.py:21` uses an autouse `structlog.reset_defaults()` fixture; `tests/iam/unit/test_events.py:17` calls `structlog.configure(...)` *inside* a test without a teardown. Run order can affect `structlog.testing.capture_logs()` reliability. Promote the reset to a session-scope autouse in `backend/tests/conftest.py`. (`backend/tests/iam/unit/test_events.py:17`)
12. **The deepseek `embeddings` and yandex provider error paths use `NotImplementedError`.** `pyproject.toml:160` excludes `raise NotImplementedError` from coverage, so a chunk of unimplemented surface is silently hidden — fine, but combined with the 51-60% provider coverage it conceals how much of `chat_stream` / `tool_calls` is genuinely tested versus excluded.

### Severity: LOW

13. **Magic numbers without comments.** `test_provision_cell_schema.py:39` (`elapsed < 30.0`) and `test_failover_under_5s.py:52` (`elapsed < 5.0`) — both *do* have AC references in surrounding strings ("AC2 = <30s", "AC7"), which is best-practice. `test_iam/test_token_service.py:9` magic-numbers are pulled from settings, OK. Overall the suite is good here.
14. **No `time.sleep`/`asyncio.sleep` in any test** (grep returned 0 hits in `tests/`). Excellent — no race-condition risk. The `time.monotonic()` usage in `test_provision_cell_schema.py:30` and `time.perf_counter()` in `test_failover_under_5s.py:36` are measurement only, not waits.
15. **`tests/iam/unit/test_events.py::test_all_emit_functions_run_without_raising`** is a weak "no-raise" smoke test — by name and behaviour. It only proves CloudEvent emitters don't crash; no envelope-content assertion. The companion `test_user_registered_emits_envelope_with_required_keys` (same file) has the comment `# Whether captured or not, the call shouldn't raise.` indicating the author knew this is a weak test. Acceptable as smoke, but should not be counted as "AC coverage" for any envelope-shape requirement.
16. **Mock overuse — service tests that mock service-internal collaborators heavily.** `tests/multitenancy/test_cell_service.py` patches `CellRepository`, `CellMemberRepository`, all four emitter functions *and* audit. This makes the service test essentially a wiring test; behaviour is barely exercised. Same in `test_workspace_service.py`. Acceptable for unit tier, but the missing integration coverage (see #2, #3, #7, #8 above) means the wiring is *only* validated by wiring tests.
17. **Repository tests are missing entirely** — `iam/repositories/*` at 39-58% coverage and `multitenancy/repositories/*` at 57-58% coverage. No `tests/iam/repositories/` or `tests/multitenancy/repositories/` directories exist. The `services/` tier mocks repos away, so repository CRUD logic is unverified.
18. **`tests/llm_gateway/test_byok_flow_full.py:56`** uses `plaintext_key = "sk-test-byok-fake-key-1234567890"` with `# gitleaks:allow`. That's safe; only flagging because the same pattern is used in 3 other files (`test_routers_stubs.py:64`, `conftest.py` for iam, etc.) — would benefit from a central `tests/fixtures/test_keys.py` to reduce repetition and single-source the gitleaks allowlist.
19. **AC tests not annotated with AC IDs.** The audit-traceability mapping above had to be reconstructed by file/test-name inspection. Adding `# AC: 00.4-AC7` markers (or pytest markers like `@pytest.mark.ac("00.4-AC7")`) would make traceability automated. Currently only file-header docstrings carry the AC link (good: `test_provision_cell_schema.py`, `test_audit_log_append_only.py`).

---

## Test infrastructure observations

- **`backend/tests/conftest.py`** defines only `db_engine` + `db_session` (integration) and `backend_version` (used only by `test_smoke.py`). Both `db_*` fixtures are correctly session-/per-test scoped with `await engine.dispose()` and per-test `rollback()`. **No session-leak risk in the unit lane** because no unit test consumes them.
- **Per-module `conftest.py`**: `tests/iam/conftest.py` provides FakeRedis + fast-Argon2 hasher (well-isolated, no global state); `tests/llm_gateway/conftest.py` autouse-isolates `BYOK_MASTER_KEY_B64` env (good); `tests/mcp/conftest.py` provides FakeRedis (independent stand-in from iam's — minor code duplication but no shared mutable state, so safe).
- **testcontainers vs pytest-postgresql consistency**: `pyproject.toml:46-49` declares both; no test currently uses either directly (integration tests use raw `db_session` against `TEST_DATABASE_URL` from env). The fallback story exists in deps but is unused in code. Acceptable for Wave 0 but document it.
- **Markers**: `pyproject.toml:137` sets `addopts = "--strict-markers -ra -m 'not live and not integration'"`. Good. `live` is registered by `tests/llm_gateway/conftest.py:24-28` *and* globally — duplicate registration is a no-op but redundant.
- **Coverage `fail_under = 70`** (`pyproject.toml:156`) — global, not per-module. Phase 00.3 AC8 + 00.4 AC9 expect 85 per-module; CI does not actually enforce this. Suggest per-module `--cov-fail-under=85` in the dedicated jobs.
- **`filterwarnings = ["error"]`** is on (`pyproject.toml:144-146`) — excellent, prevents silent deprecation drift.
- **structlog reset is local** to `test_events.py` files. `tests/iam/unit/test_events.py:17` calls `structlog.configure()` mid-test without resetting — could leak config to subsequent tests. The `tests/multitenancy/test_events.py:21` autouse `reset_defaults()` is the right pattern; promote it.

---

## Summary

The Phase 00.3 + 00.4 suite is **functionally green and well-engineered at the
unit tier** — 319 passing tests, no flake-prone `sleep` calls, deterministic
fixtures, good use of `httpx.MockTransport` over heavier mocking libs, and
sensible separation of unit / integration / live markers.

The audit issues are coverage-gate / AC-traceability problems, not correctness
regressions:

1. **Coverage gates** for 00.3 AC8 and 00.4 AC9 are not met (`multitenancy`
   -3.6pp, `llm_gateway` -6.1pp, `audit` -0.65pp). The global `fail_under=70`
   hides this from CI.
2. **HTTP-router surface** is barely tested. `llm_gateway/routers/providers.py`
   and `multitenancy/routers/{cells,workspaces}.py` sit at 0% coverage.
3. **5 ACs are wholly or partly missing**: 00.3 AC1, 00.3 AC6 lint; 00.4 AC2
   (reasoner chain), AC3 (Yandex streaming SSE), AC5 (`/providers/status`),
   AC10 (BudgetExceeded cap).
4. **Two AC-named tests carry the `integration` marker but are unit-mode**
   (`test_cost_ledger_sum_match.py`, `test_byok_flow_full.py`) — they are
   skipped by the default CI lane, so AC4 and AC6 evidence is *not actually
   executed* in the default test run despite the files existing.
5. **Repository tier is untested** — services mock repos away; repository
   classes themselves are at 39-58% coverage with no targeted tests.

None of the above are blockers for merging the *functionality*, but they are
blockers for the *phase-acceptance bar* the spec set. Verdict: **FLAG** —
fix the gate-misses and the deselected-integration-mark issue before claiming
phase done; the missing ACs (AC10, streaming, reasoner-chain,
providers/status endpoint) can be tracked as immediate follow-ups.
