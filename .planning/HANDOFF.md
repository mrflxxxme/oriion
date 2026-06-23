# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-22 (**Phase 01.3 — Billing core, ADR-008**)
- Session: `kind-goldstine-ba713f`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. 01.1-retro ✅ · 01.2 Master-Agent core ✅ · **01.3 Billing core ✅ code-complete + locally verified (this PR).**
- **What this PR delivers:** the billing **account layer** on top of the 01.2 cost-ledger — tariffs, idempotent Trial-14d/500 grant, balance/usage read API, per-cell + per-day caps (R-04), BYOK skip-debit plumbing, and the `/api/v1/billing/*` surface. **Focused-split scope** (grill 2026-06-22): enforced Trial+Solo; ЮKassa → follow-up **01.3b**; rollover/overage deferred.
- **Branch:** `claude/kind-goldstine-ba713f` (off `origin/main` = `fcbeb2c`). Focused PR → `main` → founder-merge.
- ⚠️ **Dual-tree guard:** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`.

## Active blockers (none block 01.3 billing-core)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## What just happened — Phase 01.3 (2026-06-22)

Founder-process: bootstrap-from-worktree + dual-tree guard → grill (6 forks via AskUserQuestion) → plan (pinned in-session) → execute (8 atomic commits) → local CI green → exit ritual → focused PR.

**Grill decisions (2026-06-22):** Trial+Solo enforced (Команда catalog-only — multitenancy single-cell) · ЮKassa → focused follow-up 01.3b · caps per-cell hard-block + per-day kill-switch (overage-fee deferred) · BYOK plumbing-only · rollover deferred · credit-rate fixed-config + endpoint.

**Implemented (ADR-008 Wave-1 slice):**
- `billing/0002_plans.py` (catalog, no-RLS, seed 6 tiers) + `billing/0003_subscriptions.py` (RLS `sub_cell_isolation`, partial-unique one-active-per-cell).
- `billing.models` `Plan`/`Subscription` + `billing/repositories/` + `billing/services/{subscription,balance,quota,credit_rate}_service.py` + `billing/exceptions.py` + `billing/schemas.py` + `billing/routers/billing.py`.
- Trial grant wired into `iam.auth_service.register` via a `TrialProvisioning` Null-object port (mirrors `agents.TeamProvisioning`), inside register's existing `set_tenant_context` block; real impl in `iam/deps.py`.
- Caps: `enforce_quota_admission` injected into `runtime/orchestrator.execute_agent_task` + `dispatch_task` as an optional `quota_admission` seam (default None ⇒ unit-test no-op); the **worker** (`runtime/queue/actor.py`) wires the real check. `Cell/DailyQuotaExceeded` → `task.failed`.
- BYOK: `record_llm_cost` skips the credit-debit when `byok_key_id` is set (usage_log audit row kept); sum-check refined managed-only.
- `main.py`: billing router + `BillingError` RFC-7807 handler. `_shared/middleware/tenant_context.get_current_cell_id` dep.
- `tests/conftest.py`: `billing.plans` excluded from the `db_session_committed` TRUNCATE (seed reference table, like rbac).
- CI: `src/billing` ≥85% per-module gate now runs `tests/billing -m "not live"` (was the stale `tests/llm_gateway` line).

## Verification state

- **CI-equivalent, all green (local):** `ruff check src tests` + `ruff format --check src tests` ✓ (333) · `mypy --strict src` **175 files** ✓ · unit `pytest -m "not integration and not live"` **746 passed, 1 skipped** · integration `pytest -m "integration and not live"` **40 passed** (real testcontainers PG; +11 billing incl. RLS-isolation + register→trial e2e) · per-module **billing 92% / iam 87% / llm_gateway 89% / runtime 86%** (≥85) · `bandit -r src` **0 issues**.
- **Adversarial audit (3 lenses):** 0 P0 / 0 P1 — SOUND / SECURE / NO-REGRESSIONS. Caught + fixed a **real bug** (soft-warn SSE `task.budget_warning` wasn't in the `TaskStreamEventType` Literal → would crash the soft-cap branch in prod; +2 orchestrator seam tests) + dropped cell_id from the 404 body. Deferred-as-mitigated: `start_trial` TOCTOU, quota no-op for sub-less cells, BYOK-excluded-from-caps, subscriptions column-grant (→ Wave-2).
- **9 AC-01.3.x green** — see [`phases/01.3-billing.md`](./roadmap/wave-1-core-mvp/phases/01.3-billing.md).
- **Billing-инвариант сохранён:** step-sum = cost authority (no `rollup_task_cost`); 01.2 cost-authority suites still green.
- **Live-валидация — ✅ DONE (2026-06-23, funded DeepSeek):** Master in-process golden **7/7**; **worker-path golden** (Dramatiq + **Redis-SSE** + RLS-billing) — Trial **500** live; worker run `succeeded` cost ~**5.06** (3 debits persisted, balance 500→~495); **Redis-SSE** `/stream` replayed 8 frames cross-process; per-day cap → `task.failed` `billing.daily_quota_exceeded` at admission. **01.3 billing live-proven end-to-end (trial+debit+cap)** via `scripts/live_golden_worker_billing.py` + `live_cap_check.py`.
- **Worker-infra fix (pre-existing 01.2, not 01.3) — ✅ FIXED:** the worker rebuilt the DB engine per message but reused a process-global redis SSE client bound to the first `asyncio.run()` loop → 2nd message crashed `Event loop is closed`. Now builds+closes the redis SSE publisher/client per message (`build_sse_publisher`/`build_redis_client`/`aclose`) + Selector loop policy on Windows → enabled the Redis-SSE run above (unit-pinned `test_worker_sse_lifecycle`). **Residual:** local-Windows worker *intermittently* stalls on a 2nd task's redis publish (Windows-asyncio-redis flakiness; each golden runs against a fresh worker — definitive multi-task run → CI/Linux). See `[[teamly-worker-asyncio-loop-redis-finding]]`.
- The PR's GitHub Actions (ci-backend / ci-security) is the binding gate at founder-merge.
- **NOT run:** Master-through-worker (needs vertical-cell provisioning + the worker redis fix; Master contract proven in-process); F1-B ADR-026 evaluator (separate Phase 01.2-eval).

## Next actions (founder)

1. **Merge** the focused PR (`claude/kind-goldstine-ba713f` → `main`).
2. **Live golden (Docker + funded DeepSeek):** register a cell → `GET /api/v1/billing/balance` = 500 trial; run a task → debit + balance drops; drive over hard-cap → `task.failed` `billing.cell_quota_exceeded`. Create `backend/.env` with `DEEPSEEK_API_KEY` first.
3. **OQ-02 (ООО/ИП) + OQ-19 (open ЮKassa)** → unblock **01.3b** ЮKassa test-mode top-up.
4. Carry-over from 01.2 (still open): Master live-golden (F1-A) + ADR-026 evaluator promote (F1-B).

## Next phase

**Phase 01.4 — Memory** (ADR-011): cell + role two-level memory (manual control) + conversation history (FIFO + summarization).
