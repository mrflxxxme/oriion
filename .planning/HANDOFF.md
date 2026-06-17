# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-16 (Phase 01.1 **infra-PR** — async Dramatiq dispatch + Redis-SSE + AC8 reframe)
- Session: `confident-lewin-169788`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. Phase 01.1 **Track A ✅** + **infra-PR MERGED** ([PR #51](https://github.com/mrflxxxme/oriion/pull/51), `fd02473`, 2026-06-17). Async-исполнение готово: `POST /run` → **202 <1s**, оркестрация в Dramatiq worker, SSE через Redis Streams. **AC8 RESOLVED by reframe** (dispatch p95 ≤1s hard-gate + generation SLI). Post-merge ci-security/TruffleHog (base==head) исправлен в PR #52 (`a7736a1`) — main снова зелёный.
- **infra-PR scope (11 атомарных коммитов off `5a0370b`):** AC-W1-16a ✅, AC-W1-1 ✅, AC-W1-21 ✅, AC-W1-11 ✅, AC-W1-12 ✅. **AC-W1-19 PARTIAL** (Settings-bug fixed; native → follow-up). **Deferred:** AC-W1-13 + AC-W1-2/3/4/5/9/10/14/15 → obs/IaC follow-up.
- **Phase 00.8 (design restyling):** code-complete, e2e:live pending staging (независимо, не блокирует 01.1).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — Phase 01.1 infra-PR MERGED ([PR #51](https://github.com/mrflxxxme/oriion/pull/51), `fd02473`, 2026-06-17)

Founder-process: bootstrap → AskUserQuestion (3 развилки) → Plan-агент (async-архитектура) → execute (C1–C11) → verify-bar → merge (PR #51). Post-merge hotfix PR #52 (`a7736a1`) — gate TruffleHog к pull_request (push-to-main base==head fail).

### Ключевое решение ([ADR-034](./decisions/ADR-034-async-dispatch-redis-sse-ac8-reframe.md))
`POST /run` enqueues a **Dramatiq actor** и возвращает **202 `{status:"dispatched"}` <1s** — result теперь в **`task.completed` SSE-фрейме** (breaking contract). Оркестрация в worker-процессе (`dramatiq src.runtime.queue.worker -p1 -t1`). SSE через **Redis Streams** (не pub/sub — нужен cross-process **drain-replay**: late subscriber XREAD from `0`). `tasks.dispatched_at` idempotency-marker (worker guard на `status=='queued'` → redelivery-safe; нет `'dispatched'` статуса → без CHECK-migration). Worker сам ставит 3-GUC RLS. **AC8 reframe** ([ADR-025](./decisions/ADR-025-acceptance-gate-format.md) amendment): hard-gate = dispatch p95 ≤1s; generation ~163s = SLI.

### Код (11 коммитов, verified green)
- **C1** config: `sse_backend` + `gigachat_verify_ssl`/`gigachat_ca_bundle`.
- **C2** `tasks.dispatched_at` миграция + model + schema.sql parity.
- **C3** `llm_gateway/factory.py::build_llm_router` (web+worker seam).
- **C4** `runtime/redis_sse_publisher.py` (Redis Streams; `get_sse_publisher` backend selector; default inprocess → CI детерминирован).
- **C5** `runtime/queue/{broker,actor,worker}.py` (StubBroker под `DRAMATIQ_TESTING`).
- **C6** endpoint cutover (`run_task` → 202 + enqueue; commit-then-enqueue).
- **C7** `web_search` Settings `mock_mode` fix (os.environ-bug → live Brave 422).
- **C8** Dockerfile RU Trusted Root CA + `GIGACHAT_CA_BUNDLE` + `.env.example`.
- **C9** thread-safe `setup_otel` (AC-W1-12) + span header-redaction (AC-W1-11).
- **C10** `demo_market_brief.py` AC8 reframe (dispatch-gate + generation-SLI).
- **C11** docker-compose `worker` service + `SSE_BACKEND=redis` + ADR-034/035 + README/ADR-025.

### Доки
- **ADR-034** (async + Redis-SSE + AC8 reframe, Accepted) + **ADR-035** (DeepSeek-gated web_search, Proposed/deferred). decisions/README + ADR-025 amendment.
- STATUS / JOURNAL / 01.1-retro обновлены.

## Verification state

- **CI-deterministic (green):** `ruff`(src tests scripts) ✓; `ruff format --check`(272) ✓; `mypy --strict` **151 files** ✓; `pytest` **588 passed, 23 deselected (@live/@integration), cov ≥87.9%** ✓.
- **+20 новых тестов:** Redis-SSE cross-process drain-replay (fakeredis, 2 publishers/1 server), StubBroker actor enqueue + run_task_dispatch guard/commit, web_search Settings-override, span header-redaction + thread-safe setup_otel, demo AC8-reframe (dispatch-gate / slow-dispatch fails / slow-generation does NOT gate).
- **Live-валидация — НЕ выполнена (founder-action, нужен полный стек + funded ключи).**

## Next actions

1. **Live-валидация на полном стеке** (docker `teamly-dev` up incl. новый `worker`, `SSE_BACKEND=redis`, funded DeepSeek + Yandex Api-Key):
   - `POST /run` → **202 <1s** (AC8 dispatch-gate);
   - `/stream` отдаёт `task.started → 3× delegation → task.completed` из **worker-процесса** в web-подписчика (cross-process; идеально проверить с `gunicorn -w 2`);
   - reframed `demo_market_brief.py --runs 3`: **AC8 dispatch p95 ≤1s ✅**, generation p95 = SLI, **AC9/AC10 ✅ preserved** (из `task.completed` payload);
   - GigaChat вызов в контейнере → **TLS verifies** (AC-W1-21);
   - web_search honours `.env WEB_SEARCH_MOCK_MODE`.
2. **Merge infra-PR** (founder, per ADR-027). Verify-bar = CI ✅ (588) + live golden.
3. **obs/IaC follow-up PR** (task-chip): AC-W1-13 (worker-process метрики + cost-ledger) + AC-W1-2/3/4/5/9/10/14/15.
4. **Native web_search follow-up PR** (task-chip, [ADR-035](./decisions/ADR-035-deepseek-gated-web-search-tool-call.md)): DeepSeek-gated tool-call для Researcher.
5. **GSD L2 spike** (отдельно): ROADMAP.md + config.json + layout-bridge.

## Exit ritual (this session)

- [x] ADR-034 (async + Redis-SSE + AC8 reframe) + ADR-035 (DeepSeek-gated web_search) созданы; decisions/README + ADR-025 amendment
- [x] JOURNAL.md — 2026-06-16 confident-lewin entry
- [x] STATUS.md — Wave 1 + infra-PR active-phase
- [x] HANDOFF.md rewritten (this file)
- [x] 01.1-retro.md — infra-PR status note + closed AC pins
- [x] CI-deterministic green (588) + mypy --strict (151)
- [ ] **Live-валидация** на полном стеке (founder-action)
- [ ] PR merge (founder, per ADR-027)
