# Audit Section 3 — Test Adequacy (PR 00.2.5)

**Auditor:** Test Results Analyzer subagent
**Date:** 2026-05-19
**Scope:** Test suite changes on branch `claude/heuristic-rhodes-f7a3ef`
(6 commits ahead of `main`: `cdde94f → a0e0aed`).
**Method:** Read all 5 new router/repo test files + new E2E suite + new
`conftest.py` + CI workflow diff; ran each `pytest tests/<MOD>
--cov=src/<MOD> --cov-fail-under=85 -q -m "not integration"` gate locally
against the project's pytest install on Windows (no Docker — relied on
the default `addopts = -m 'not live and not integration'` filter so
testcontainers PG was never instantiated).

---

## Top-level verdict

**FLAG**

All six per-module coverage gates pass locally. The CI bump to uniform
≥85% is technically met by the new tests, but the way several modules
get there is **structurally fragile**:

1. **`llm_gateway` clears the gate by 0.70 percentage points** (85.70%
   vs 85.00%). A single 10-line refactor in `providers/byok_proxy.py`
   chat-stream branch — or pulling out one method — drops it below the
   gate and reds CI on what should be a no-op change.
2. **The E2E suite advertises `commit_required`** but never consumes
   the `db_session_committed` fixture, so its accumulated COMMITs are
   never cleaned between tests. Cross-test audit-row assertions (`==
   1`) are order-sensitive (see Finding F-01).
3. **The 5 new router/repo files exist primarily to lift coverage** of
   routers that aren't wired into `src/main.py` yet (Phase 00.5 work).
   They exercise routing tables + handler glue, which is useful, but
   they replace nothing that was previously caught by integration —
   they are an additive coverage instrument, not a regression net.

None of these are correctness regressions. The PR is mergeable — but
the gate-tightening and the E2E pattern should be hardened before the
next phase locks them in.

---

## Coverage table (per module)

Measurements taken locally on `claude/heuristic-rhodes-f7a3ef` with
`uv run pytest tests/<MOD> --cov=src/<MOD> --cov-fail-under=85 -q -m
"not integration"`. "Before (main)" is reproduced from
`.planning/_session-context/AUDIT-2026-05-19/section-04-test-adequacy.md`
(the pre-merge per-module audit produced by the previous audit swarm
on the same baseline).

| Module        | Before (main) | After (this PR) | Gate (CI) | Margin | Status   |
|---------------|--------------:|----------------:|----------:|-------:|----------|
| iam           |       86.69 % |     **86.74 %** |    ≥85 %  | +1.74  | PASS     |
| multitenancy  |       81.40 % |     **88.39 %** |    ≥85 %  | +3.39  | PASS     |
| rbac          |      100.00 % |    **100.00 %** |    ≥85 %  | +15.00 | PASS     |
| audit         |       84.35 % |    **100.00 %** |    ≥85 %  | +15.00 | PASS     |
| llm_gateway   |       78.86 % |     **85.70 %** |    ≥85 %  | **+0.70** | PASS (tight) |
| mcp           |       83.65 % |     **92.98 %** |    ≥85 %  | +7.98  | PASS     |
| **aggregate** |     ≈83.16 %¹ |   ≈92 %² (est)  |    ≥70 %  |        | PASS     |

¹ Weighted average from prior audit, including the modules below
threshold.
² Aggregate not re-measured (CI's `Pytest unit suite [AC2 ≥ 70%
aggregate]` step still uses `--cov=src --cov-fail-under=70` and was
not changed for this PR).

### What's still uncovered & why

Per-module residual gaps, classified `J` (justifiable — defensive /
unreachable / deferred to next phase) or `U` (unjustifiable — real
behaviour the suite walks past).

| Module | Lines missing | Classification |
|---|---|---|
| `iam/deps.py:35,39,43-45,52,68` | DI factories whose construction is exercised only via the not-yet-mounted routers (cells / workspaces are Phase 00.5). | **J** (deferred) |
| `iam/services/auth_service.py:399-421` (`resend_verification`) | Real behaviour — anti-enum 202 + rate-limit + email send. No unit or E2E test. | **U** — covered route exists in `routers/auth.py` but no path test. |
| `iam/services/auth_service.py:509-512,522-528` (`get_user_profile`, `update_user_profile`) | Real behaviour on `/users/me`. `test_routers.py` exercises the router but the service branch where `find_by_id == None` (raises `InvalidCredentials`) is dead in the unit because the router test asserts 200. | **U** (small) |
| `iam/services/auth_service.py:289->291,310,315,337,431->438,436,468` | Branch partials inside login / refresh / logout error paths. Most are `if ip is None` short-circuits in rate-limit gating. | **J** (defensive) |
| `iam/repositories/*.py` 39-58 % | All real DB-binding methods. Unit suite mocks the session; integration suite (deselected by default `addopts`) covers them when run with `-m integration`. | **J** (integration-tier responsibility) |
| `multitenancy/services/workspace_service.py:92-94,110-123,126,129,245-248` (80 %) | `archive_workspace`, `restore_workspace`, soft-delete cascade branches. Service tests skip these methods. | **U** — same code path will be hit in Phase 00.5 router smoke; ship now is OK only because no router exposes them yet. |
| `multitenancy/services/cell_service.py:145-157,276,285-286` | `update_settings_jsonb` JSON-merge branch + `remove_member` "last admin" guard. | **U** (small — the last-admin guard is invariant 7 in the multitenancy contract). |
| `multitenancy/repositories/*.py` 57 % | Same story as iam repos — integration-tier. | **J** |
| `llm_gateway/providers/byok_proxy.py:82,99,129-150` (73 %) | Line 82 (`_client()` body) and 129-150 (`chat_stream`) are **literally untested** because `_patched_proxy` in `test_byok_proxy_provider.py` overrides `_client`. The real headers (`Authorization: Bearer <key>`, `Content-Type`) are never asserted to be on the wire. | **U** — see F-04. |
| `llm_gateway/providers/deepseek.py:39,57,92-115` (62 %) | `__init__` `base_url` strip + `chat_stream`. | **U** for chat_stream (real SSE parsing untested). |
| `llm_gateway/providers/gigachat.py:56-84,96-97,131-153,168` (48 %) | OAuth token refresh (`_ensure_token`) + `chat_stream` + `embeddings`. Token refresh has real time arithmetic (epoch ms vs s). | **U** — `_ensure_token` is the highest-risk uncovered code in the PR. |
| `llm_gateway/providers/yandex.py:45,96-118,144-150` (60 %) | `_client()` + `chat_stream` + `health_check` exception branch. | **U** for chat_stream; **J** for `_client()` (covered indirectly by chat mock test, but not asserted). |
| `llm_gateway/circuit_breaker.py:55,64` (93 %) | Two `if self._state == OPEN` short-circuits. | **J** (defensive). |
| `llm_gateway/services/router_service.py:85,113,115` (91 %) | Failover next-provider iteration branches. | **J**. |
| `mcp/tools/read_url.py:106-113,213,219-220,224-225,251-254` (82 %) | `_strip_html` fallback + content-too-large + retry exhaustion + final `else` branches. | **J** (defensive, mostly error paths). |
| `mcp/tools/web_search.py:146,175,212,233` (93 %) | Single-branch error fall-throughs. | **J**. |

---

## Findings by severity

### HIGH

#### F-01 — E2E suite marks `commit_required` but never consumes the cleanup fixture
**File**: `backend/tests/integration/test_e2e_auth_flow.py:64`
**Concern**: The module-level `pytestmark = [pytest.mark.integration,
pytest.mark.commit_required]` declares intent to use real COMMITs, but
none of the 5 tests consumes the `db_session_committed` fixture
(`backend/tests/conftest.py:274-315`). The `db_session_committed`
fixture is the **only** thing in the test infrastructure that runs the
`TRUNCATE TABLE … RESTART IDENTITY CASCADE` cleanup. Because the E2E
tests instead drive writes through their own `app` fixture's
`override_get_db` (which **does** real COMMIT-per-request — see lines
117-125), the rows persist across tests.

This breaks `test_register_through_logout_flow`'s assertion at line
246: `assert await _count_audit_rows(assertion_session,
"iam.user.registered") == 1`. The query has no `WHERE
user_id = :u` filter — it counts every `iam.user.registered` row in
`audit.audit_log`. When this is the **first** test run in a fresh
container the count is 1. When `test_forgot_and_reset_password_flow`
(also registers) ran before it (e.g. after a `pytest -k` reorder, or
when `-p no:randomly` is removed in a future change), the count is 2
and the test reds.

The same fragility exists for line 265 (`email_verified == 1`), 275
(`login == 1`), 293 (`refresh == 1`), 307 (`logout == 1`), 359
(`password_reset == 1`).

The doc-comment at lines 37-40 explicitly claims "uses
`commit_required`… real COMMITs … reads back rows" — but the
mechanism described (the SAVEPOINT-vs-real-COMMIT distinction in the
fixture) is the wrong half of the contract. Cross-TX visibility is
already achieved via the per-request COMMITs in `override_get_db`; the
**cleanup** half is the one that's missing.

**Suggested fix**: One of —
1. Add `db_session_committed: AsyncSession` as a parameter to each
   E2E test function (even unused) — pytest will then realise the
   fixture and run the TRUNCATE teardown.
2. OR add an autouse fixture in `tests/integration/conftest.py` that
   TRUNCATEs the application schemas before each E2E test starts
   (preferred — keeps E2E tests order-independent without forcing each
   one to drag an unused fixture).
3. OR change every cross-test count assertion to filter by `actor_id =
   :u` so the test only sees the rows it produced. This is what the
   `_count_audit_rows` helper at line 172-177 was designed to support
   but isn't using.

#### F-02 — `llm_gateway` coverage margin is +0.70 pp — gate is one refactor away from red
**File**: `.github/workflows/ci-backend.yml:169`,
`backend/src/llm_gateway/`
**Concern**: The `Per-module coverage gate (Phase 00.2.5 — uniform
≥85%)` step uses `--cov-fail-under=85`. Local measurement shows
`TOTAL 849 stmts, 99 miss, 102 branch, 7 brpart → 85.70 %`. Adding
**6 untested lines** (or one 6-statement defensive branch) drops it
below 85 %. The largest contributors to that thin margin are
`providers/gigachat.py` (48 %) — particularly the `_ensure_token`
OAuth refresh path (lines 55-84) and the stream parsers. Any
follow-up phase that adds a single uncovered helper to one of the
provider files will red CI on what should be unrelated work.

**Suggested fix**:
1. Backfill `test_provider_gigachat_mock.py` to cover `_ensure_token`
   (both fresh-token and cached-token branches) and at least one
   `chat_stream` iteration. This is the cheapest path to a 2-3 pp
   margin.
2. OR explicitly mark provider stream methods `# pragma: no cover —
   covered by Phase 00.5 live-mode tests` to surface the intent
   instead of relying on the gate's tightness as a hidden contract.
3. OR drop the per-module gate to 80 % until Phase 00.5 adds the
   provider matrix tests, then ratchet back to 85 % once margin is
   restored. (CI rule of thumb: gates should sit ≥3 pp below current
   coverage; this PR puts `llm_gateway` 0.7 pp inside the gate.)

### MEDIUM

#### F-03 — `iam/unit/conftest.py` autouse-patches `emit_audit_event`, masking signature drift
**File**: `backend/tests/iam/unit/conftest.py:25-38`
**Concern**: The fixture `_stub_emit_audit_event` is `autouse=True` and
replaces `emit_audit_event` with `AsyncMock()` at both
`src.iam.services.auth_service` and
`src.iam.services.consent_service`. The patches are name-bound, so the
real impl is only swapped at the iam unit call sites — that part is
fine.

The risk is signature drift. `AsyncMock()` accepts **any** call shape
without complaint. Today both call sites pass
`session=self._session` (auth_service.py:474-482 etc.,
consent_service.py:61-71) and the real `emit_audit_event`
(`audit/services/audit_service.py`) declares `session: AsyncSession |
None = None`. If, in Phase 00.5, `emit_audit_event` is renamed (e.g.
to `record_audit_event`) or its kwargs change (e.g. `session` →
`db_session`), the iam unit suite stays green while the real call
shape silently broke. The integration tier (E2E) would catch it — but
only if E2E is actually run, which currently happens in CI only via
the separate `Pytest integration suite (real PG)` step at line
145-154.

Mitigation in place: `tests/audit/test_audit_service.py` (lines 22-90)
covers the real `emit_audit_event` contract including the
`session=AsyncMock` branch with `insert_mock.await_args.kwargs`
assertions. So the contract IS independently pinned — but the
contract test asserts the function shape in isolation, not the
caller's adherence to it.

**Suggested fix**: Use `spec=emit_audit_event` on the `AsyncMock`:
```python
from src.audit.services.audit_service import emit_audit_event as _real
with (
    patch("src.iam.services.auth_service.emit_audit_event",
          AsyncMock(spec=_real)),
    patch("src.iam.services.consent_service.emit_audit_event",
          AsyncMock(spec=_real)),
):
    yield
```
`AsyncMock(spec=fn)` raises `TypeError` on wrong-arity / wrong-kwarg
calls. Adds 2 lines, kills the silent-drift risk.

#### F-04 — `test_byok_proxy_provider.py` subclasses to override `_client()` — bypasses real HTTP setup
**File**:
`backend/tests/llm_gateway/test_byok_proxy_provider.py:21-40`
**Concern**: `_patched_proxy` returns a `_Patched(BYOKProxyProvider)`
subclass whose `_client()` returns an `httpx.AsyncClient` built around
`httpx.MockTransport`. The override **duplicates** the headers logic
(`Authorization: Bearer …`, `Content-Type: application/json`) from
the real `_client()` (`src/llm_gateway/providers/byok_proxy.py:81-88`).

Three consequences:
1. The real `_client()` body (line 82-88) is **uncovered**
   (it's in the 73 % gap reported above).
2. If someone changes the real `_client()` to add a new header (e.g.
   `OpenAI-Beta: assistants=v2`), the test passes because the test's
   override is independent. A bug shipped where the real BYOK call
   misses the new header would not be caught.
3. The duplicated header dict in the test creates a maintenance fork.

The same anti-pattern lives in `test_provider_deepseek_mock.py:26-41`
(`_PatchedDeepSeekProvider` overrides `_client`). Both files
intentionally avoid `respx`/`pytest-httpx` (which are pinned in
`pyproject.toml:50-51` as dev deps, so the dependency is available
but unused for these two providers).

**Suggested fix**: Either —
1. Migrate both files to `respx.mock(base_url=…)` (already done for
   `test_deepseek_health_check_reachable` at line 90-95 of
   `test_provider_deepseek_mock.py` — proves the pattern works). This
   exercises the real `_client()` because `respx` patches at the
   transport layer of `httpx`, not by replacing the client.
2. OR inject the transport via constructor (`BYOKProxyProvider(...,
   transport: httpx.AsyncBaseTransport | None = None)`) so the real
   `_client()` stays the only code path and the test just passes a
   MockTransport in. This is a 3-line prod-code change with no runtime
   cost.

#### F-05 — Router mini-app tests cover routers that aren't mounted in `main.py`
**File**: `backend/tests/multitenancy/test_workspaces_router.py`,
`backend/tests/multitenancy/test_cells_router.py`,
`backend/tests/llm_gateway/test_providers_router.py`
**Concern**: All three test files construct a fresh `FastAPI()`,
include only the router under test, override every dependency, and
exercise the route handlers via `TestClient`. The docstring at
`src/multitenancy/routers/cells.py:10-11` says "The 00.2.5
integration phase mounts both routers in src/main.py" — but
inspection of `src/main.py` (`Grep include_router`) shows only
`auth_router` and `me_router` are included. The new E2E test at
`test_e2e_auth_flow.py:425-454` explicitly pins this with
`assert r.status_code == 404` for `/api/v1/llm/chat/completions`,
`/embeddings`, `/byok-keys`.

This means:
- The router tests exercise route-handler glue + Pydantic
  serialization + exception-mapping — **real behaviour, not
  trivial**. They do catch real regressions (e.g. forgetting to
  install the `MultitenancyError` handler).
- But they cover code that **doesn't ship through `main.py`** in
  this PR. A user request hitting `/api/v1/workspaces` returns 404,
  not the 201 the test asserts. The tests pin the contract for Phase
  00.5 wiring — which is valuable forward-protection — but they are
  **not** an end-to-end check.
- They contribute meaningfully to coverage (without them
  `multitenancy/routers/workspaces.py` and `…/cells.py` would be 0 %,
  pulling the module total to ~70 %).

This is acceptable as a forward-cover pattern, but it should be
explicitly documented. The current naming
(`test_workspaces_router.py`) implies these are integration-tier
tests; they aren't.

**Suggested fix**:
1. Add a module-level docstring banner: "PHASE 00.5 PRE-WIRING — these
   tests exercise the router in isolation; the router is not yet
   mounted in `src/main.py`. When Phase 00.5 wires the router, the
   E2E suite in `tests/integration/test_e2e_auth_flow.py` should grow
   smoke coverage for the same endpoints, and this file remains as
   the fast-feedback unit layer." (cells_router.py already has half
   of this in its `_install_multitenancy_handler` comment.)
2. Add a `test_e2e_auth_flow.py` assertion (mirroring the existing
   `test_llm_chat_endpoint_is_not_yet_wired`) for `/api/v1/workspaces`
   so the Phase 00.5 contributor sees the flipped assertion as a
   prompt to extend coverage.

### LOW

#### F-06 — `db_session_committed` fixture is declared but never used
**File**: `backend/tests/conftest.py:274-315`
**Concern**: The fixture is described thoroughly (43 lines of docstring
across the conftest header + the fixture body) but no test in the
suite consumes it. `Grep "db_session_committed" tests/` returns only
the conftest definition and three doc-string references. Dead
fixtures rot: in 3 months the next maintainer will either delete it
(losing the cleanup helper) or refactor without realising no test
caller exists.
**Suggested fix**: After F-01 is addressed (E2E tests opt into the
fixture, or an autouse cleanup is added to `tests/integration/
conftest.py`), this fixture either becomes used or can be removed in
favour of the autouse pattern.

#### F-07 — `assertion_session` reads through a fresh session — no race window
**File**: `backend/tests/integration/test_e2e_auth_flow.py:145-156`
**Concern note**: The audit prompt asks about a race window between
handler COMMIT and assertion SELECT. There is **none**: the test
awaits the `httpx` request fully (line 207 `r = await client.post(…)`
returns only after the handler's `override_get_db` reaches `await
session.commit()` at line 125). The COMMIT completes before the
client returns the response. The subsequent `assertion_session.execute()`
runs in a new `AsyncSession` bound to the same `AsyncEngine`, so it
acquires a fresh connection from the pool and sees the committed
rows. Asyncpg + PG's MVCC guarantee read-after-commit visibility on a
new connection.
**Verdict**: not a finding — the pattern is correct. Recording here so
the audit prompt is answered explicitly.

#### F-08 — Test `test_remove_member_204` does not assert that `remove_member` was awaited
**File**: `backend/tests/multitenancy/test_cells_router.py:223-225`
**Concern**: The test calls `client.delete(...)` and asserts
`r.status_code == 204`. It does not assert
`mock_service.remove_member.assert_awaited_once_with(...)`. A handler
that returned 204 without calling the service (e.g. a stub that
forgot to `await` the service call) would silently pass.
**Suggested fix**: Add `mock_service.remove_member.assert_awaited_once()`
after the status-code assertion. Same minor issue applies to
`test_create_workspace_201` (line 97-108 — doesn't assert
`create_workspace.assert_awaited_once_with(...)` with expected
kwargs).

#### F-09 — `test_providers_status_returns_snapshot` over-asserts a stub
**File**: `backend/tests/llm_gateway/test_providers_router.py:145-154`
**Concern**: The Wave-0 stub at `src/llm_gateway/routers/providers.py:60-80`
returns `state="healthy"`, `circuit="closed"` for **every** active
provider. The test asserts the same. When Phase 00.5+ wires
`HealthMonitor` (per the comment at line 65-67), this test will need
to be rewritten — but the test gives no signal that this is a Wave-0
placeholder. The test name doesn't say "stub_snapshot".
**Suggested fix**: Rename to
`test_providers_status_returns_static_wave0_snapshot` and add a
docstring banner: "WAVE-0 PLACEHOLDER — when `HealthMonitor` lands,
delete this test and replace with one that drives state via the
monitor."

#### F-10 — `coverage.run` includes `branch = true` but the `omit` list is minimal
**File**: `backend/pyproject.toml:172-186`
**Concern**: `omit = ["tests/*"]` — that's correct. But `exclude_lines`
omits the common defensive patterns (`pragma: no cover`,
`if TYPE_CHECKING:`, `raise NotImplementedError`, `...`). What's
**not** excluded:
- `if __name__ == "__main__":` (none currently, but a future smoke
  script would count against the gate).
- Async-generator `return` after `yield` (which produces a
  partially-covered branch even when fully tested).
- `except KeyboardInterrupt:` patterns.
None of these would currently cause an issue. The configuration is
fine. Recording for completeness in case future Phase 00.x adds CLI
entry points that should be excluded.
**Suggested fix**: none required now; revisit if a Phase 00.x adds
script entry points or `__main__` blocks.

#### F-11 — `commit_required` marker is declared but only one file uses it
**File**: `backend/pyproject.toml:155-156`, `tests/`
**Concern**: The marker is registered with a 4-line description but
applied at exactly one site (the E2E module-level mark — which then
doesn't actually consume the fixture, per F-01). Tests that **would
benefit** from it (because they read back rows after a COMMIT) and
either skip the marker or get away without it:
- `tests/audit/test_audit_partitions.py` — reads `pg_catalog` only,
  doesn't write, marker correctly absent.
- `tests/audit/test_audit_log_append_only.py` — writes + tries to
  UPDATE in the same TX, SAVEPOINT-rollback is correct, marker
  correctly absent.
- `tests/multitenancy/test_rls_isolation.py` — also same-TX, marker
  correctly absent.

So the audit shows marker usage is actually **correct** (the only
caller needs cross-TX visibility, which the marker exists to opt into).
The problem is the caller doesn't consume the fixture — see F-01.
**Suggested fix**: covered by F-01. Once F-01 is fixed, the marker
has at least one true consumer and the contract is well-formed.

#### F-12 — CI gate uniformity ignores module size
**File**: `.github/workflows/ci-backend.yml:165-170`
**Concern**: The gate is uniformly 85 % across six modules whose
statement counts vary by ~10×: `rbac` = 84 stmts, `llm_gateway` = 849
stmts. A single 8-line uncovered branch is 9 % of `rbac` and 0.94 %
of `llm_gateway`. The uniform gate is therefore much harsher on small
modules (easy to lose 5+ pp on one PR) and very permissive on large
ones (where 130 lines can be uncovered while still passing). `rbac`'s
100 % is a fluke driven by tiny surface, not by rigor. As the
modules grow (multitenancy + llm_gateway in particular will roughly
double in Phase 00.5), the gate will become uniformly easier to clear
on the large modules and harder on small ones until small modules
also grow.

**Suggested fix**: short-term — keep the uniform 85 %, but track the
absolute uncovered-line count per module in the CI summary so a 5pp
drop on `rbac` (8 lines) reads as obviously different from a 5pp drop
on `llm_gateway` (42 lines). Long-term (Phase 00.5+): per-module
gates calibrated to module size + risk (e.g. `audit` and `iam` get
90 %, `llm_gateway` providers get 80 % until Phase 00.6 live
matrix, defensive-heavy modules get 75 %).

---

## Marker discipline (audit-prompt §4)

- `commit_required`: declared in `pyproject.toml:155`, applied at one
  site (`test_e2e_auth_flow.py:64`). The marker's contract (the
  fixture it nominally opts into) is not honoured by its only caller
  (F-01). Other tests that don't need it correctly omit it.
- `integration`: applied consistently. Every test under
  `tests/integration/`, `tests/audit/test_audit_log_append_only.py`,
  `tests/audit/test_audit_partitions.py`,
  `tests/multitenancy/test_provision_cell_schema.py`,
  `tests/multitenancy/test_rls_isolation.py`,
  `tests/llm_gateway/test_byok_flow_full.py`,
  `tests/llm_gateway/test_cost_ledger_sum_match.py`,
  `tests/rbac/test_seed_data.py` carries the marker. No false
  positives spotted (no unit test mis-marked as integration; no
  integration test missing the marker that I could find via grep).
- `live`: declared, not yet used. Reserved for Phase 00.6 per
  `conftest.py:47-48`. Fine.

---

## Flaky-test risk (audit-prompt §5)

1. **Time-dependent assertions**: 1 site —
   `test_provision_cell_schema.py:39` asserts `elapsed < 30.0`. CI
   runners have wide variance; 30 s is a 100×+ margin over the
   measured cost (~50-200 ms in practice). Low risk.
   `test_circuit_breaker.py:57,73` uses `datetime.now(UTC) -
   timedelta(seconds=120)` to seed an "old" opened_at — that's
   monotonic-time-independent and not flaky.
2. **Ordering assumptions**: see F-01. The E2E suite's `== 1`
   assertions are the only real ordering risk in the new tests.
3. **Parallel-safety**: `pytest-xdist` is not in `dev` dependencies
   (`pyproject.toml:36-53`) — tests run serial. If a future
   contributor adds `-n auto`, the E2E `app` fixture (which mutates
   `production_app.dependency_overrides`, a process-global) will race
   between worker processes. The fixture clears overrides on teardown
   (line 142), but two parallel E2E tests would step on each other.
4. **`pytest-randomly` not in deps** — the file-order assumption
   shielding F-01 is currently safe. If `pytest-randomly` is added in
   the future, F-01 manifests as a flake.

---

## Coverage tool config (audit-prompt §6)

`pyproject.toml [tool.coverage.run]` is correct: `source = ["src"]`,
`branch = true`, `omit = ["tests/*"]`. `[tool.coverage.report]`:
`show_missing = true`, `skip_covered = false`, `fail_under = 70`,
`exclude_lines` covers `pragma: no cover`, `TYPE_CHECKING`,
`NotImplementedError`, `...`. Nothing excluded that shouldn't be. See
F-10 for a minor forward-looking note.

---

## CI gate change (audit-prompt §7)

**Realistic now?** Yes — all six modules pass with margin between
0.7 pp (`llm_gateway`) and 15 pp (`audit`, `rbac`).

**Sustainable?** Conditional:
- `llm_gateway`'s 0.7 pp margin is **not sustainable** — see F-02.
  Any minor refactor in `providers/` will red CI on what should be
  a no-op change. Either pad the margin (preferred) or temporarily
  drop the gate to 80 % until Phase 00.5 backfills provider tests.
- `iam`'s 1.74 pp margin is **borderline** — `resend_verification`
  + `update_user_profile` already exist as live uncovered code; the
  Phase 00.3 router additions are likely to drop the percentage by
  ~2-3 pp.
- `multitenancy` (88 pp), `mcp` (93 pp), `audit` (100 pp), `rbac`
  (100 pp) have comfortable margin and the gate will be sustainable
  for them through Phase 00.5.

**Will it cause CI red on minor refactors?** For `llm_gateway` — yes,
high probability. For other modules — low probability.

---

## Summary checklist

| Item | Status |
|---|---|
| All 6 per-module gates pass locally | PASS |
| New E2E suite is comprehensive within its declared scope | PARTIAL — F-01 (state-leak risk) |
| Router/repo coverage tests exercise real behaviour | YES (F-05 documents the not-yet-mounted caveat) |
| `BYOKProxyProvider` `_client()` real path covered | NO — F-04 |
| `gigachat` `_ensure_token` OAuth refresh covered | NO — F-02 contributor |
| Markers discipline | OK except F-01 marker-vs-fixture mismatch |
| Coverage config | OK |
| CI gate is sustainable for next phase | CONDITIONAL — F-02 |

---

**Recommended pre-merge actions**: F-01 (E2E cleanup) and F-02
(`llm_gateway` margin) are the only two findings that warrant blocking
a future PR on. F-03 / F-04 are quality improvements that can land in
a follow-up. The rest are documentation / forward-protection notes.

**Recommended PR-merge action**: this PR is mergeable. Open a tracking
issue for F-01 + F-02 + F-04 to be addressed in the first Phase 00.5
PR before the LLM router wiring lands.
