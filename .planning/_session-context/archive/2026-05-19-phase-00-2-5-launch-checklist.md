# Phase 00.2.5 — Launch Checklist

> Prepared 2026-05-19 by @claude-opus after post-merge consistency audit
> of PR #30 (Phase 00.3 + 00.4 combined). Verdict: **FLAG, no blockers**
> — 4 doc-hygiene fixes applied. Phase 00.2.5 may start immediately after
> PR #30 merges into `main`.

## Phase 00.2.5 scope (one-liner)

Delete `backend/src/_stubs/{audit.py, multitenancy.py}`. Rewire all
3 production call-sites. Add testcontainers session fixture. Run E2E
smoke. Mark Phases 00.2 / 00.3 / 00.4 ✅ Complete.

---

## Section 1 — Pre-launch (founder action, ~5 min)

- [ ] PR #30 (`claude/cool-bell-0c74ba`) — all 4 CI checks green (`ci-backend`, `secrets`, `trivy`, `grype`).
- [ ] Review the consolidated audit reports under `.planning/_session-context/`:
  - `AUDIT-2026-05-19/AUDIT-REPORT.md` — pre-merge 5-agent independent audit.
  - `POST-MERGE-AUDIT-2026-05-19.md` — post-merge consistency audit (this checklist's basis).
- [ ] Squash-merge PR #30 to `main` via GitHub UI. **Do NOT rebase-merge** — keeps the 12-commit history readable.
- [ ] After merge: `git checkout main && git pull origin main` locally.
- [ ] Delete the spent worktree: `git worktree remove .planning/.claude/worktrees/cool-bell-0c74ba` (optional — frees disk).

---

## Section 2 — Worktree setup

```bash
# From repo root, on freshly-pulled main
git checkout main && git pull origin main

# New worktree for the integration phase
git worktree add .planning/.claude/worktrees/phase-00-2-5-integration -b claude/phase-00-2-5-integration

# Verify HEAD includes the 12 commits from PR #30
cd .planning/.claude/worktrees/phase-00-2-5-integration
git log main..HEAD --oneline | wc -l   # expect 0 (clean branch off main)
git log --oneline -3                    # last 3 should include PR #30 squash + Phase 00.2 squash + architect-PR squash

# Sync deps
cd backend
uv sync --frozen 2>/dev/null || uv sync
```

- [ ] `uv run pytest tests/ -q` passes (330 tests).
- [ ] `uv run ruff check src tests` clean.
- [ ] `uv run mypy --strict src` clean.

---

## Section 3 — Stubs inventory (3 swaps to perform)

Post-audit canonical list:

| Stub | Production callers | Swap kind |
|---|---|---|
| `backend/src/_stubs/audit.py::emit_audit_event` | `backend/src/iam/services/auth_service.py:23` <br> `backend/src/iam/services/consent_service.py:15` <br> `backend/src/multitenancy/services/cell_service.py:18` | **Pure import swap** — signatures match (real impl is strict superset, formally verified by `tests/audit/test_emit_audit_event_stub_compat.py`). |
| `backend/src/_stubs/multitenancy.py::provision_initial_workspace` | `backend/src/iam/services/auth_service.py:24,143` | **Call-site refactor** — stub takes `(user_id)`, real impl takes `(session, user_id, email_localpart)`. Update `register()` to derive `email_localpart` from `cmd.email` and pass current session. |

> NOTE: `_stubs/rls.py` was originally planned but never created — `set_tenant_context` real impl in `backend/src/_shared/db/rls.py` shipped in the same combined PR. 00.4 code already imports from the real module.

### Detailed swap targets

**For `emit_audit_event`** (pure import swap):
```python
# Before
from src._stubs.audit import emit_audit_event
# After
from src.audit.services.audit_service import emit_audit_event
```

**For `provision_initial_workspace`** (call-site refactor in `iam/services/auth_service.py`):
```python
# Before (line 23-24):
from src._stubs.audit import emit_audit_event
from src._stubs.multitenancy import provision_initial_workspace

# After:
from src.audit.services.audit_service import emit_audit_event
from src.multitenancy.services.workspace_service import provision_initial_workspace

# Before (line 143):
provision_result = await provision_initial_workspace(user.id)

# After:
provision_result = await provision_initial_workspace(
    session=session,
    user_id=user.id,
    email_localpart=cmd.email.split("@", 1)[0],
)
```

---

## Section 4 — testcontainers + conftest setup

The current `backend/tests/conftest.py` uses a function-scoped `db_engine` that connects to whatever `TEST_DATABASE_URL` points at. CI provides one via the service container; local dev needs `docker compose up` first. Phase 00.2.5 promotes this to testcontainers for session-scoped reuse + per-test SAVEPOINT pattern.

- [ ] Add a `pg_container` session-scoped fixture that boots `pgvector/pgvector:pg16` once per pytest session.
- [ ] `db_engine` becomes session-scoped again, but now bound to the testcontainers DSN.
- [ ] `db_session` switches to a SAVEPOINT-rollback pattern (nested transactions inside session-scope outer TX).
- [ ] Add `loop_scope="session"` to integration tests that need the session-scoped engine.
- [ ] Revert `asyncio_default_fixture_loop_scope` back to `"session"` in `pyproject.toml` — gain back the cross-test connection reuse.
- [ ] Apply `alembic upgrade heads` once at session start (autouse session fixture), not per test.

---

## Section 5 — E2E smoke test (new)

Add `backend/tests/integration/test_register_to_llm_flow.py`:

```
register → verify-email (capture token from outbox) → login → /api/v1/llm/chat → refresh → logout → assert access-token blacklisted
```

- [ ] Test covers all 6 steps end-to-end against real PG.
- [ ] Mock LLM provider response via respx (no real DeepSeek call).
- [ ] Assert SUM(credit_transactions.amount_rub) == SUM(llm_usage_log.cost_rub) for the LLM call.
- [ ] Assert audit_log has rows for register / login / refresh / logout actions.

---

## Section 6 — Coverage uplift

Phase 00.2.5 pushes the per-module gates closer to the AC9 target of ≥85% by exercising router glue via TestClient:

| Module | Pre-merge | Target after 00.2.5 |
|---|---|---|
| iam | 87% | ≥87% (no regress) |
| rbac | 100% | 100% |
| audit | 84% | ≥85% |
| multitenancy | 81% | ≥85% (router coverage) |
| llm_gateway | 79% | ≥85% (router coverage) |
| mcp | 85% | ≥85% |

- [ ] Add TestClient-based tests for each router in `multitenancy/routers/` and `llm_gateway/routers/`.
- [ ] Add repository-tier integration tests now that PG fixture is consistently available.
- [ ] CI gate config updated in `.github/workflows/ci-backend.yml` after coverage hits targets.

---

## Section 7 — Cleanup / debt-paydown candidates

Tracked from PR #30 audit report:

- [ ] Delete `backend/tests/audit/test_emit_audit_event_stub_compat.py` (no longer applicable post-swap).
- [ ] Delete `backend/tests/iam/unit/test_stubs.py` if present (same reason).
- [ ] Delete `backend/src/_stubs/` directory entirely (after both swaps complete).
- [ ] Refactor cross-context import `llm_gateway.services.billing_service → src.billing.models` to a port/adapter pattern OR move CreditTransaction model into llm_gateway (Architect-audit H1, defer if larger than 2 hrs).

---

## Section 8 — Exit ritual (per agent-handbook/05-PR-WORKFLOW.md)

- [ ] `.planning/STATUS.md` updated: Phase 00.2 / 00.3 / 00.4 → ✅ Complete (post 00.2.5 merge); Phase 00.2.5 → ✅ Complete; Phase 00.5 → 🔄 In progress.
- [ ] `.planning/HANDOFF.md` rewritten with 00.2.5 session snapshot.
- [ ] `.planning/JOURNAL.md` appended.
- [ ] Phase-spec status: `00.2-custom-jwt-auth.md`, `00.3-db-rls-multitenancy.md`, `00.4-llm-gateway.md` → `Code-complete → ✅ Complete`.
- [ ] Open PR `[00.2.5] refactor: integration — delete _stubs/, rewire to real impls, E2E smoke`.

---

## Section 9 — Risks for 00.2.5

| Risk | Mitigation |
|---|---|
| testcontainers boot time blows CI 8-min budget | Cache `pgvector/pgvector:pg16` image at job start (docker pull step before pytest). Measure first; downgrade to apt-installed `postgresql-16` if needed. |
| Call-site refactor of `provision_initial_workspace` breaks register flow | Add explicit test `test_register_creates_real_workspace_and_cell` BEFORE deleting stubs — bisect-safe rollback path. |
| RLS context not set on register's INSERT chain | Audit `register()` flow: do all writes happen before `set_tenant_context` is bound? If yes, that's safe because the new tables grant INSERT to oriion_app + write policies allow `current_user_id IS NOT NULL`. If register runs as superuser, RLS is bypassed anyway. Document the pattern. |
| Multitenancy 4-policy split (Round-11 fix) breaks production write paths | Smoke-test write paths in 00.2.5 E2E: `register` → cell creation → cell_member insert. Real call-paths exercise all FOR INSERT policies. |
| pg_partman not yet integrated | Wave 0 manual sentinel `audit_log_2026_06` keeps prod healthy through June. Wave 1+ ships pg_partman + cron. Add reminder in PHASE-00-6 (deploy) checklist. |

---

## Section 10 — Out of scope for 00.2.5

- Yandex KMS swap (Phase 00.6).
- pytest-xdist parallelism (Phase 00.6).
- pg_partman + automatic partition rolling (Wave 1).
- Live LLM provider tests (Phase 00.6 once API keys provisioned).
- Brave/Yandex Search real keys (Phase 00.5 — multi-agent tools).
- Refactor cross-context `billing_service → src.billing.models` (defer to Wave 1 if >2 hrs).
- Coverage rebuild of router glue if testcontainers boot pushes CI over 8 min.

---

## Section 11 — Estimated duration

- Setup (Section 2): 10 min
- Stub swaps (Section 3): 30 min
- testcontainers + conftest (Section 4): 60 min
- E2E smoke (Section 5): 60 min
- Coverage uplift (Section 6): 90 min
- Exit ritual + PR (Section 8): 30 min

**Total: ~5 hours of focused dev time.** Add 30 min buffer for surprises. Single autonomous session is feasible.

---

## Section 12 — Success criteria (Phase 00.2.5 DONE definition)

- ✅ `backend/src/_stubs/` directory removed.
- ✅ All 3 stub call-sites rewired to real impls.
- ✅ E2E smoke test passes (register → … → logout) against real PG.
- ✅ Per-module coverage ≥85% on iam, rbac, audit, multitenancy, llm_gateway, mcp.
- ✅ ruff clean, ruff-format clean, mypy --strict clean, bandit 0/0/0.
- ✅ CI all green (5 checks).
- ✅ Exit ritual artefacts updated.
- ✅ Phase-specs 00.2/00.3/00.4 → ✅ Complete.
- ✅ PR `[00.2.5]` opened and ready for founder review + merge.
