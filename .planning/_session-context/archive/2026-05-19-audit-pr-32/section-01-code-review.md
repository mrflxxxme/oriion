# Section 01 — Code Review (Phase 00.2.5 Integration PR)

**Auditor:** Code-Reviewer subagent
**Date:** 2026-05-19
**Branch:** `claude/heuristic-rhodes-f7a3ef` (6 commits ahead of `b3837f0` — the PR #30 merge)
**Scope:** stub-swap correctness, test infra (conftest + E2E), coverage uplift, `Base.type_annotation_map` fix
**Method:** read-only review of `git diff b3837f0..HEAD` plus cross-reference of unchanged call sites that depend on the swap

---

## Top-Level Verdict: **FLAG**

**0 BLOCK** — nothing in this PR breaks correctness of production code paths.
**1 HIGH** — E2E test isolation bug that will flake or false-pass under `-m integration` ordering.
**4 MEDIUM** — narrow correctness / observability gaps + one unit-test gap that hides whether audit emissions actually happen.
**5 LOW** — stale references / minor consistency / counting nits.

The production stub-swap itself (Steps 3 + 5 secondary) is **correct** — all 8 `emit_audit_event` call sites in `auth_service`, both calls in `consent_service`, and all 5 calls in `cell_service` correctly pass `session=self._session`. The `provision_initial_workspace` call-site refactor at `auth_service.py:156-160` matches the real impl's signature exactly. The `Base.type_annotation_map` fix is correctly scoped — every model uses `Mapped[datetime]` only (no `Mapped[date]` anywhere in `src/`), so adding `date` to the map would be dead code.

The single HIGH issue is in test infra, not production code — but it will cause CI to fail or pass non-deterministically depending on test order under `pytest -m integration`. It must be fixed before merge.

---

## HIGH-severity findings

### H-1 — E2E test suite has no per-test DB cleanup; assertions are order-dependent

**File:** `backend/tests/integration/test_e2e_auth_flow.py:64`, `196`, `319`, `369`, `397`
**Marker:** `pytestmark = [pytest.mark.integration, pytest.mark.commit_required]`

The whole file is marked `commit_required`, but **no test in the file actually requests the `db_session_committed` fixture** that performs the TRUNCATE cleanup (`backend/tests/conftest.py:274-315`). The marker is metadata only; the fixture is the side-effect carrier. Each test:

1. Builds its own `app` fixture that overrides `get_db` to commit-per-request against a session-scoped `pg_container`.
2. Reads back rows via `assertion_session` (also bound to the session-scoped container).
3. Asserts row counts via `_count_audit_rows(session, action)` filtered ONLY by `action`, not by `email` / `user_id`.

Concrete failure path under `pytest -m integration` (alphabetical test order inside the file):

| Order | Test | Side effect |
|---|---|---|
| 1 | `test_consent_pdn_missing_blocks_register_before_provision` | 422 — no row written. OK. |
| 2 | `test_forgot_and_reset_password_flow` | Registers `e2e-reset@example.com`, verifies, resets → +1 `iam.user.registered`, +1 `iam.user.email_verified`, +1 `iam.user.password_reset`. |
| 3 | `test_llm_chat_endpoint_is_not_yet_wired` | No writes. |
| 4 | `test_register_idempotency_replay` | Registers `e2e-replay@example.com` → +1 `iam.user.registered` (and the 409 attempt is rejected pre-write). Total now: 2 `iam.user.registered` rows. |
| 5 | `test_register_through_logout_flow` | Asserts `_count_audit_rows(..., "iam.user.registered") == 1` (line 246) — **will fail with count == 3**. Same fate for `iam.user.email_verified == 1` (line 265), `iam.auth.login == 1` (line 275), `iam.auth.refresh == 1` (line 293), `iam.auth.logout == 1` (line 307). |

The `test_forgot_and_reset_password_flow` test has the same brittleness in reverse: line 359 `_count_audit_rows(..., "iam.user.password_reset") == 1` is fine on first run, but a re-run of just this test (no cleanup between runs of the same `pytest` invocation against a kept container) explodes.

**Why this didn't show up in the validation block of commit `567c524`:** the commit message reports `21/21 integration tests pass`. That could be true on a single clean run; what the report doesn't reveal is whether it's true on the *second* run against the same kept container, or under `pytest --randomly` / `-p no:randomly` shuffles, or when the integration suite is run inside the same pytest invocation as previous suites that exercised the same paths.

**Fix (recommended):** make each E2E test consume `db_session_committed` so its teardown TRUNCATE fires. The simplest mechanical change:

```python
@pytest_asyncio.fixture
async def app(db_engine: AsyncEngine, db_session_committed: AsyncSession) -> AsyncIterator[FastAPI]:
    ...
```

Adding `db_session_committed` to the `app` fixture signature pulls the truncate-teardown into scope without modifying any of the assertions. (The session itself isn't used by the test — what we need is its teardown side-effect.)

Alternative: use unique random suffixes in test emails so action-by-actor_id filtering is possible — but this requires every assertion to also filter, which is invasive. The fixture approach is cleaner.

**Severity rationale:** HIGH not BLOCK because the bug is in a test added by this PR (not pre-existing production code) and CI may still happen to pass on a fresh container, masking it. But the bug will surface the first time CI keeps a warm container, or anyone runs `pytest -m integration` twice locally, or pytest-randomly is added. The PR's own commit message claims 21/21 integration passes — that result is not reproducible.

---

## MEDIUM-severity findings

### M-1 — `iam.auth.logout` audit row writes `UUID(int=0)` as actor_id when the actual user is known

**File:** `backend/src/iam/services/auth_service.py:276-300`

```python
async def logout(self, refresh_token: str, ...) -> None:
    token_hash = self._token_service.hash_refresh_token(refresh_token)
    row = await self._refresh_repo.find_by_hash(token_hash)
    if row is None:
        return  # logout is idempotent

    await self._session_repo.revoke(row.session_id)
    ...
    await emit_audit_event(
        actor_type="user",
        actor_id=UUID(int=0),  # actor unknown post-logout (refresh-token unauthenticated)
        ...
        resource_id=row.session_id,
        ...
        session=self._session,
    )
```

The justification in the inline comment is wrong as written. The refresh-token row carries `session_id`, and `SessionRepository.find_by_id(row.session_id)` returns a row with `.user_id`. The original Phase 00.2 comment ("replaced in 00.3 audit") signaled an intent to fix this; the Phase 00.2.5 commit replaced the comment text but left the `UUID(int=0)` synthetic — losing the audit-trail fidelity for `iam.auth.logout` events. `audit_log.actor_id` is `UUID | None` per `AuditRepository.insert(actor_id: UUID | None, ...)`, so passing `None` would actually be more honest than `UUID(int=0)` (which is a real-looking UUID and will collide with anyone else who also uses sentinel zeros).

**Suggested fix:** Look up the session row and pass the real `user_id`:

```python
session = await self._session_repo.find_by_id(row.session_id)
actor_id = session.user_id if session else None
...
await emit_audit_event(actor_type="user", actor_id=actor_id, ...)
```

Or — if the policy is genuinely "treat logout as unauthenticated" — pass `actor_type="system"` and `actor_id=None`. The current shape (`actor_type="user"` + `UUID(int=0)`) is internally contradictory.

---

### M-2 — Unit tests don't verify `emit_audit_event` is called; autouse-patch silently masks regressions

**File:** `backend/tests/iam/unit/conftest.py:25-38` + `backend/tests/iam/unit/test_auth_service.py:137-167`

The autouse fixture replaces `emit_audit_event` with an `AsyncMock()` at both iam-service import sites. The fixture is necessary (the unit-tier mock sessions can't satisfy `audit_repository.insert → session.add → session.flush`), but it also means **no unit test in `tests/iam/unit/` verifies that AuthService actually calls `emit_audit_event` for register / login / logout / rotate / verify / reset**. If a future refactor accidentally drops one of the 8 audit emits in `auth_service`, every unit test still passes; only the integration suite catches it — and only if H-1 hasn't already caused that test to flake first.

**Suggested fix:** Make the autouse fixture YIELD the mock so individual tests can opt-in to asserting on it. Two-line change:

```python
@pytest.fixture(autouse=True)
def _stub_emit_audit_event() -> Iterator[AsyncMock]:
    auth_mock = AsyncMock()
    consent_mock = AsyncMock()
    with (
        patch("src.iam.services.auth_service.emit_audit_event", auth_mock),
        patch("src.iam.services.consent_service.emit_audit_event", consent_mock),
    ):
        yield auth_mock  # or a (auth_mock, consent_mock) pair
```

Then `test_register_happy_path_sends_email_and_returns_workspace` can add one assertion (`_stub_emit_audit_event.assert_awaited()`) to pin the contract — and similarly for the 7 other call sites.

---

### M-3 — `change_role` + `remove_member` audit emits omit `workspace_id` despite being trivially derivable

**File:** `backend/src/multitenancy/services/cell_service.py:227-240` (change_role), `264-273` (remove_member)

The diff shows that 3 of the 5 cell_service audit emits pass `workspace_id=cell.workspace_id`, but the 2 member-mutating ones omit it because the local variable is `member` (a `CellMember`) not `cell` (a `Cell`). The omission is functionally OK — `audit.audit_log.workspace_id` is nullable — but it's inconsistent and removes a useful filter dimension for security investigations ("show me all member-role changes inside workspace X").

The cell is one cheap lookup away:

```python
async def change_role(...) -> CellMember:
    member = await self._member_repo.find_by_cell_user(cell_id, user_id)
    if member is None:
        raise MemberNotFound()
    cell = await self._cell_repo.find_by_id(cell_id)  # <-- add
    ...
    await emit_audit_event(
        ...
        workspace_id=cell.workspace_id if cell else None,  # <-- add
        cell_id=cell_id,
    )
```

The extra round-trip is a single PK lookup inside the same TX (asyncpg, no network).

**Suggested fix:** Add the cell lookup in both `change_role` and `remove_member` so all 5 cell_service audit emits carry workspace scope. Alternative: extend `CellMemberRepository.find_by_cell_user` to JOIN cells and surface workspace_id on the returned object.

---

### M-4 — `archive_cell` reads `cell.workspace_id` after the archive UPDATE; double-check ORM state survives

**File:** `backend/src/multitenancy/services/cell_service.py:105-126`

```python
async def archive_cell(self, *, cell_id: UUID, archived_by: UUID) -> None:
    cell = await self._cell_repo.find_by_id(cell_id)
    if cell is None:
        raise CellNotFound()
    await self._cell_repo.archive(cell_id)   # UPDATE cells SET archived_at = now()
    archived_at = datetime.now(UTC)
    ...
    await emit_audit_event(
        ...
        workspace_id=cell.workspace_id,   # reading attr after the UPDATE
        cell_id=cell_id,
    )
```

If `CellRepository.archive(cell_id)` performs a non-ORM UPDATE that doesn't touch `cell` (likely — it's a `UPDATE ... WHERE id = :id`), then `cell.workspace_id` is still valid. If it ever changes to use `session.merge()` or expires the row, the read would re-issue a SELECT and could break under RLS context if archived rows aren't visible to the user's context. The Phase 00.2.5 diff doesn't change `CellRepository.archive` — but the new audit-emit becomes the first call site to depend on this invariant.

**Suggested fix:** Either snapshot `workspace_id` into a local before the archive call:

```python
cell = await self._cell_repo.find_by_id(cell_id)
if cell is None:
    raise CellNotFound()
workspace_id = cell.workspace_id  # snapshot before archive
await self._cell_repo.archive(cell_id)
...
await emit_audit_event(..., workspace_id=workspace_id, cell_id=cell_id)
```

Or add a regression test that archives + asserts the audit row's workspace_id matches.

---

### M-5 — `Base.type_annotation_map` is correct but undertested

**File:** `backend/src/_shared/db/base.py:30-32`

```python
type_annotation_map: ClassVar[dict[type, DateTime]] = {
    datetime: DateTime(timezone=True),
}
```

The fix is correct. I verified via `Grep "Mapped\[date\]"` that **no model uses `Mapped[date]`** (calendar date without time) anywhere in `src/`, so the map doesn't need to grow. Every datetime column in iam / multitenancy / rbac / audit / llm_gateway / billing / mcp uses `Mapped[datetime]` or `Mapped[datetime | None]` and lands as `timestamptz` in the migrations — all 36 grep hits confirmed.

**However:** the fix has zero direct test coverage. The bug (offset-naive default with tz-aware Python values) only manifests against real PG. There's no test that does, say:

```python
def test_base_datetime_columns_are_tz_aware() -> None:
    from src._shared.db.base import Base
    from sqlalchemy import inspect
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, DateTime):
                assert col.type.timezone is True, f"{table.name}.{col.name} is tz-naive"
```

The E2E suite will catch a regression once H-1 is fixed and counts are correct. Without H-1's fix, the E2E itself is unreliable — meaning the only safety net for the type_annotation_map fix is a flaky test.

**Suggested fix:** Add the 6-line metadata-introspection test above to `tests/_shared/test_base.py`.

---

## LOW-severity findings

### L-1 — Stale `_stubs` references in 5 production docstrings

**Files:**
- `backend/src/audit/__init__.py:8-9`
- `backend/src/audit/services/__init__.py:5-6`
- `backend/src/audit/services/audit_service.py:5-6`, `40` (3 references in docstring), `185`
- `backend/src/multitenancy/services/workspace_service.py:5`, `55`

The `_stubs/` directory was deleted in commit `f264fc6`, but the contract-locked docstrings continue to reference it. Examples:

- `audit_service.py:5-6`: `Signature contract: emit_audit_event(...) is a strict superset of the stub at src/_stubs/audit.py::emit_audit_event`
- `audit_service.py:40`: `The compatibility test (test_emit_audit_event_stub_compat.py) asserts every stub parameter — name + default semantics — is present here.` ← the referenced test file was deleted in the same commit.
- `workspace_service.py:5`: `(currently wired to the stub in src._stubs.multitenancy). Phase 00.2.5 will swap the import to this module`

This isn't a bug — the code works — but it's misleading historical context that will confuse anyone reading the docstring six months from now ("where's the stub file? where's that compat test?"). Either rewrite to past-tense ("was contract-locked to the stub at...") or delete the references entirely now that the integration is done.

**Suggested fix:** s/`is contract-locked`/`was contract-locked`/g in those 5 docstrings; remove the `test_emit_audit_event_stub_compat.py` reference.

---

### L-2 — Plan documentation says "9 emit_audit_event calls in auth_service"; actual count is 8

**File:** `C:\Users\KUklonskiy\.claude\plans\phase-00-2-5-integration-squishy-llama.md` (referenced from HANDOFF) + commit message of `f264fc6` ("All 9 emit_audit_event calls in auth_service likewise carry session=self._session")

I verified by `Grep "emit_audit_event" src/iam/services/auth_service.py` — 8 call sites: 184 (register), 257 (login), 292 (logout), 322 (rotate_refresh reuse), 356 (rotate_refresh success), 384 (verify_email), 474 (reset_password reuse), 496 (reset_password success).

Not a code defect — but the commit message's "9" claim is wrong and will mislead anyone counting against the plan to verify completeness. Either the plan miscounted or one site was removed in an unrelated cleanup and the message wasn't updated.

**Suggested fix:** Cosmetic — note in PR body that the actual count is 8.

---

### L-3 — `db_session_committed` cleanup TRUNCATE may race with leaked connections from prior test

**File:** `backend/tests/conftest.py:274-315`

```python
@pytest_asyncio.fixture
async def db_session_committed(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(bind=db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        # TRUNCATE every table ... Run outside of any TX so this always succeeds
        # even if the test left state aborted.
        async with db_engine.begin() as conn:
            tables = await conn.execute(...)
            ...
            await conn.execute(text(f"TRUNCATE TABLE {', '.join(qualified)} RESTART IDENTITY CASCADE"))
```

`db_engine` is function-scoped (function-fixture), so when the fixture teardown finishes and pytest tears down `db_engine`, it calls `engine.dispose()`. Between the TRUNCATE inside `db_session_committed` teardown and the engine dispose, there's a narrow window where a leaked connection (e.g., from a handler that didn't close) could still hold a TX. In practice asyncpg connection-leak detection raises ResourceWarning and pytest's `filterwarnings = ["error"]` would promote it to error — so the race is observable, not silent. But it'd be cleaner to TRUNCATE *before* yielding (so the test always starts clean) rather than after (where leaks can interfere).

**Suggested fix:** Move TRUNCATE to the setup phase or duplicate it both sides:

```python
async def db_session_committed(db_engine):
    # Pre-clean (defensive against prior leaks).
    async with db_engine.begin() as conn:
        await _truncate_all(conn)
    session = AsyncSession(bind=db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        async with db_engine.begin() as conn:
            await _truncate_all(conn)
```

This also incidentally fixes H-1 if the E2E fixture pulls `db_session_committed` in (each test starts cleanly regardless of leaks from earlier tests).

---

### L-4 — `test_register_happy_path` mock for `provision_initial_workspace` doesn't enforce kw-only contract

**File:** `backend/tests/iam/unit/test_auth_service.py:147-167`

```python
fake_provision = AsyncMock(
    return_value=SimpleNamespace(workspace_id=fake_workspace_id, cell_id=fake_cell_id)
)
with patch("src.iam.services.auth_service.provision_initial_workspace", fake_provision):
    result = await svc.register(...)
...
fake_provision.assert_awaited_once()
_, kwargs = fake_provision.call_args
assert kwargs["user_id"] == new_user.id
assert kwargs["email_localpart"] == "new"
assert "session" in kwargs
```

This pins the call-site shape (good) but doesn't verify that the AuthService calls the function with **only** keyword args — i.e., a regression that switches from `provision_initial_workspace(session=..., user_id=..., email_localpart=...)` to `provision_initial_workspace(self._session, user.id, email_localpart="new")` would pass `("user_id" in kwargs)` checks because... wait, no, positional-then-keyword would put `user_id` into `args` not `kwargs`. So the assertion would fail. Actually the test is fine; just observing that if anyone changes the real function signature to accept positional params, the test silently relaxes.

**Suggested fix:** Add `args, kwargs = fake_provision.call_args; assert args == ()` — one extra line, makes the kw-only contract explicit.

---

### L-5 — Coverage gate bump from 70/80 → 85 isn't reproducibly verifiable from this PR alone

**File:** `.github/workflows/ci-backend.yml:155-160`

The bump is fine in principle (covered modules really do hit ≥85% per commit `2ac9111`'s message). The risk: the gate now lives downstream of subtle test changes, so a future PR that removes a single high-coverage router test (e.g., from `test_workspaces_router.py`) could drop multitenancy from 88.39% to 84.x% and break CI without anyone noticing in review. The bump itself is correct; the LOW finding is "no commit-time printed coverage breakdown that future PRs can diff against."

**Suggested fix:** Optional — add `-q --cov-report=term-missing:skip-covered` to the gate command so the per-module coverage % is visible in CI logs as a regression baseline.

---

## What I verified passes (no finding)

The following were explicitly checked and are correct:

| Item | Verdict | Note |
|---|---|---|
| `auth_service.register()` passes `session=self._session, user_id=user.id, email_localpart=cmd.email.split("@",1)[0]` to `provision_initial_workspace` | ✅ matches real impl signature (`workspace_service.py:135-139`) exactly | comment correctly flags the `alice@x` vs `alice@y` slug-collision risk for Wave 1 |
| All 8 `emit_audit_event` call sites in `auth_service` pass `session=self._session` | ✅ verified by Grep + line-by-line | extra workspace_id+cell_id on register call is correct |
| All 2 `emit_audit_event` call sites in `consent_service` pass `session=self._session` | ✅ both grant + revoke | |
| All 5 `emit_audit_event` call sites in `cell_service` pass `session=self._session` | ✅ | 3 of 5 also pass workspace_id; the other 2 are M-3 |
| `get_auth_service` passes `session=db`, `get_consent_service` passes `session=db` | ✅ | matches AsyncSession kw-only contract |
| `Base.type_annotation_map` covers every Mapped[datetime] in the codebase | ✅ | 0 `Mapped[date]`, 36 `Mapped[datetime]` — no other date types need mapping |
| `provision_initial_workspace` idempotency-on-slug protects the naive `split("@",1)[0]` derivation | ✅ | `workspace_service.py:166-179` |
| `conftest.py::pg_container` correctly defers Docker discovery when `TEST_DATABASE_URL` is set | ✅ | lazy `from testcontainers.postgres import ...` import |
| `conftest.py::db_session` SAVEPOINT-rollback pattern correctly uses outer TX + connection.close | ✅ | `outer_tx.is_active` guard handles already-rolled-back case |
| `_alembic_upgrade_heads` reformatted DSN substitution still preserves both branches (already-asyncpg vs need-asyncpg-prefix) | ✅ | pure formatting change in commit `3515bc4` |
| Unit-tier autouse `_stub_emit_audit_event` correctly patches at iam-service import sites (not the audit module) | ✅ | name-binding patch is the right choice; integration tests cover the real path |
| `httpx.AsyncClient + ASGITransport` choice over `TestClient` correctly avoids the asyncpg cross-loop-Future error | ✅ | docstring explains the constraint; pattern matches what conftest.py already does for `db_engine` |

---

## Suggested PR-merge decision

- **Required before merge:** Fix H-1 (one-line fixture addition to pull `db_session_committed` into the E2E `app` fixture). Without this fix, CI will flake or false-pass under load.
- **Recommended before merge:** M-1 (`logout` actor_id) — one extra `find_by_id` call to record the real user_id.
- **Defer to follow-up:** M-2, M-3, M-4, M-5, all LOW. Worth their own small PR; not gate-blocking.

Once H-1 is fixed, the rest of the PR is mergeable. The stub-swap correctness is solid — all call sites verified.
