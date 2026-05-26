# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-26 (C0 catch-up — rewrites HANDOFF + STATUS из Phase 00.2 era к post-Phase-00.6-PR-A baseline. Stage B PR-B in flight on branch `claude/gallant-lamport-f48eca`).
- Session: `gallant-lamport-f48eca` (worktree branch `claude/gallant-lamport-f48eca`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — **closing** (Stage B PR-B closes anchor `internal_demo_passed=true`)
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (merged 2026-05-17 via [PR #25](https://github.com/mrflxxxme/oriion/pull/25), `b192c6b`)
- **Architect-PR (pre-00.2)**: ✅ Complete (merged 2026-05-17 via [PR #27](https://github.com/mrflxxxme/oriion/pull/27))
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (merged via PR `[00.2] feat(iam)...` 2026-05-18; 14 atomic commits, src.iam coverage 86.69%, AC1-AC10 green)
- **Phase 00.3 (DB+RLS+multitenancy)**: ✅ Complete (merged in parallel with 00.2 + 00.4)
- **Phase 00.4 (LLM gateway+MCP)**: ✅ Complete (merged in parallel with 00.2 + 00.3)
- **Phase 00.2.5 (integration)**: ✅ Complete (merged 2026-05-19 via [PR #32](https://github.com/mrflxxxme/oriion/pull/32), 8 atomic commits; deleted `backend/src/_stubs/` and rewired imports к real impls)
- **Phase 00.5 / 00.5a (Pydantic-AI runtime)**: ✅ Complete (anchor branch merged 2026-05-20)
- **Phase 00.5b (runtime + tasks + orchestrator)**: ✅ Complete (merged via [PR #35](https://github.com/mrflxxxme/oriion/pull/35) 2026-05-21; 6 commits + Commit 8 (audit fixes + Exit ritual) + mandatory 5-agent audit swarm; 3 HIGH/15 MEDIUM/17 LOW; AC-W1-1..10 pin block to Phase 01.1 retro)
- **Phase 00.6 PR-A (Stage A: local-first validation infra)**: ✅ Complete (merged 2026-05-25 via [PR #36](https://github.com/mrflxxxme/oriion/pull/36); 22 atomic commits eb31ff8 → 0f125bd; consolidated self-audit 0H/9M/10L PASS-WITH-FIXES; new AC-W1-11..15 pin block extension)
- **Phase 00.6 PR-B (Stage B: YC staging deploy + 10× demo + Wave-0 anchor flip)**: 🔄 In Progress on `claude/gallant-lamport-f48eca` (this session)
- **Phase 00.7 (frontend skeleton)**: ⏳ Pending — opens после Phase 00.6 closure
- **Phase 01.1 retro (Wave-1 hardening)**: ⏳ Pending — created в PR-B C8 commit с AC-W1-1..17 pins lifted

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## What just happened (Phase 00.6 PR-A + start of PR-B)

### Phase 00.6 PR-A (PR #36, merged 2026-05-25)

**22 атомарных коммитов** (см. `git log e8b5552 --oneline | head -22`):

```
eb31ff8 — Phase 00.6 spec amendment к 2-stage version [C1]
dd9fa2d — alembic.ini UTF-8 force via env.py patch (cp1251 Windows fix) [C2]
588e979 — auth_service.register uses async-with set_tenant_context (GUC helper) [C3]
f5a937f — mid-session checkpoint
4af82e6 — founder-action provisioning complete + env state matrix
29fcbf1 — _shared/observability OTel SDK + auto-instrumentation [C4]
eb96039 — _shared/observability/metrics.py 9-metric family + /metrics ASGI mount [C5]
b5a0f6c — _shared/logging.py OTel correlation processor + LOG_FORMAT override [C6]
8c70f50 — infra/docker-compose.staging.yml 9-service stack + observability configs [C7]
55e2ae1 — infra/docker-compose.staging-local.override.yml + Caddyfile.staging env-driven [C8]
a518621 — infra/observability/grafana provisioning + 3 dashboards [C9]
6773dad — tests/tasks/ 35 unit tests (src/tasks 47% → 95.82%) [C10]
4801891 — tests/runtime/ 28 unit tests (src/runtime 49% → 94.92%) [C11]
d462532 — ci-backend.yml per-module gate ≥85% для agents/tasks/runtime (AC13 strict) [C12]
30c0051 — observability unit tests + local-smoke runbook [C13]
e8e663d — Phase 00.6 PR-A self-audit + Exit ritual + PR open [C14]
b62ed50 — in-loop smoke-test fixes (Dockerfile, Caddy basic_auth, Loki 3.2 field, OTel port, pgvector image) [C15]
082b948 — alembic monkey-patch _ensure_version_table для varchar(128) [C16]
76c386f — document Phase 00.5b orchestrator-dispatch gap [C17]
0d9fa73 — ruff + mypy strict cleanups для CI green [C18]
3c661aa — src/ ruff cleanup + mypy AsyncPG ignore [C19]
2e58fad — defer src/agents per-module gate к Wave-1 AC-W1-17 [C20]
0f125bd — register PYSEC-2026-161 ignore + ADR-014 entry [C21]
```

**Decisions standing (verbatim из grill 2026-05-23, НЕ перегриливать в PR-B):**

| # | Branch | Resolution |
|---|---|---|
| Q1 | Scope envelope | B (spec + hygiene; GLM-5 silent defer без ADR-N) |
| Q2 | Execution model | D-extended (local-first then VM, 2-stage) |
| Q3 | PR strategy | ii (2 PRs — PR-A local + PR-B staging) |
| Q4 | Worktree | fresh PR-B worktree |
| Q5 | Compose pattern | A (base + local override) |
| Q6 | Local-pass acceptance | 3 (smoke + 1× real-LLM demo) |
| Q7 | Audit scope | IV (full на PR-A — DOWNGRADED к self-audit per context budget; lightweight на PR-B — UPGRADED к full 5-agent per founder PR-B brief) |
| Q8 | AC13 | i (strict honor — закрыто PR-A для tasks/runtime; agents deferred к Wave-1 AC-W1-17) |
| Q9 | GUC | A1 (async-with wrap — закрыто PR-A C3) |
| Q10 | Alembic | B1 (env.py utf-8 — закрыто PR-A C2) |
| Q11 | IaC | 1 (Terraform-only) |
| Q12 | Anchor-flip | α (10× founder run against staging URL) |
| Q13 | AC-tolerance | AC8 cohort p95; AC9/10 per-run all-pass |

### CRITICAL FINDING from PR-A live smoke (recap)

POST /api/v1/cells/{cell_id}/tasks создаёт queued task **но НЕ dispatches** к orchestrator. SSE stream `/tasks/{id}/stream` подключается к InProcessSSEPublisher pubsub queue, но никто события не публикует — клиент ждёт впустую. PR-B C1 closes via **Path #1 inline-dispatch endpoint**:

```
POST /api/v1/cells/{cell_id}/tasks/{task_id}/run
# Synchronously invokes orchestrator.run_task(task) — SSE стрим начинает работать end-to-end.
```

AC-W1-16 (NEW, this prompt): orchestrator-dispatch swap к Dramatiq actor (async dispatcher) tracked для Wave-1; inline approach acceptable для Wave-0 single-cell demo flow.

### Phase 00.6 PR-B commit ledger (in flight, 10 atomic commits)

**Phase A — AI autonomous (C0..C6 + C8):**

| # | Status | Commit | Type |
|---|---|---|---|
| C0 | 🔄 in flight | `docs(planning): catch-up HANDOFF + STATUS to Phase 00.6 PR-A baseline` | housekeeping |
| C1 | ⏳ pending | `feat(runtime,tasks): inline orchestrator-dispatch endpoint (POST /tasks/{id}/run)` | feature |
| C2 | ⏳ pending | `fix(scripts): demo_market_brief.py AC8 cohort-semantic + exit-code refactor` | bugfix |
| C3 | ⏳ pending | `feat(infra/terraform): YC Cloud baseline (VM + Managed PG + Redis + Lockbox + DNS)` | feature |
| C4 | ⏳ pending | `feat(ci): deploy-staging.yml workflow + scripts/deploy/{wait_healthy,rollback}.sh` | feature |
| C5 | ⏳ pending | `feat(infra,docs): Caddyfile.staging real-ACME + staging-bootstrap runbook` | feature |
| C6 | ⏳ pending | `docs(planning,gates): amend wave-0-to-1.md D5 verbatim per α + ADR-018 V4 drift` | docs |
| C8 | ⏳ pending | `chore(planning,roadmap): lift AC-W1-1..17 в phases/01.1-retro.md` (NEW) | docs |

**Founder gate (between C6 and C7):** terraform apply + DNS A-record `staging.oriion.dev` + `gh secret set` (4 secrets + 3 vars) + first deploy + manual register/login curl + 10× demo run `python -m scripts.demo_market_brief --runs 10` + screen-recording. Evidence handed back в `.planning/gates/evidence/wave-0-to-1/`.

**Phase B — AI resumes (C7 + C9):**

| # | Status | Commit | Type |
|---|---|---|---|
| C7 | ⏳ pending | `chore(gates,evidence): 10× founder demo run evidence` | evidence |
| C9 | ⏳ pending | `chore(audit,docs): FULL 5-agent Phase 00.6 retro + Exit ritual + Wave-0 anchor flip` | audit |

### AC-W1 pin block (lift verbatim в Phase 01.1 retro C8)

**Phase 00.5b inherited (Phase 01.1 retro target):**
- AC-W1-1 — SSEPublisher Redis-pubsub bridge (multi-worker invariant, F-ARC-H2)
- AC-W1-2 — Per-step TaskStep persistence + per-callsite metrics
- AC-W1-3 — Master-Agent schema extension
- AC-W1-4 — TaskRepository port + outbox
- AC-W1-5 — cancel_cascade real-PG testcontainers + SSE-stream proper test (extended за F-TR-M1)
- AC-W1-6 — GUC tenant-context helper extract ✅ **CLOSED PR-A C3** (remove from active list)
- AC-W1-7 — NullTeamProvisioningService no-op default
- AC-W1-8 — DelegateInput.target_agent_slug pattern constraint
- AC-W1-9 — Provider key rotation via YC Lockbox (partial — Stage B Terraform ships Lockbox provisioning)
- AC-W1-10 — GigaChat OAuth refresh-after-expiry test

**Phase 00.6 PR-A new pins:**
- AC-W1-11 — OTel header-sanitization processor (drop Authorization spans) — F-SEC-M2
- AC-W1-12 — OTel SDK thread-safety (atomic _instrumented flag) — F-ARC-M1
- AC-W1-13 — Per-callsite metric instrumentation (orchestrator + LLMRouter + cost_recorder) — F-ARC-L1
- AC-W1-14 — Loki retention 90d + audit_log archival — F-CMP-M2 (ФЗ-152 compliance)
- AC-W1-15 — Alertmanager Telegram/PagerDuty receivers — F-CMP-L1

**Phase 00.6 PR-B new pins (this prompt):**
- AC-W1-16 — orchestrator-dispatch swap к Dramatiq actor (replace inline synchronous endpoint от PR-B C1)
- AC-W1-17 — proper src/agents unit tests (per PR-A C20 per-module gate deferral)

## Pre-flight readiness (validated 2026-05-26)

| Item | Status | Notes |
|---|---|---|
| Worktree base | ✅ `gallant-lamport-f48eca` @ `e8b5552` (= origin/main HEAD post-PR #36) | working tree clean |
| `backend/.env` | ✅ copied 3793 bytes from `great-engelbart-8aa6fc/backend/.env` | YANDEX_IAM_TOKEN refreshed via `yc iam create-token` (length=309) |
| Docker | ✅ Desktop 28.5.1 / 8.2 GiB RAM | sufficient для 10-service stack |
| Terraform | ✅ v1.15.4 on PATH | ready для `terraform init/plan/apply` |
| yc CLI | ✅ auth'd | folder-id = `b1g74vf7snhebom5avhu` |
| gh CLI | ✅ auth'd as `mrflxxxme` | ready для `gh secret set` + `gh pr create` |
| Russian Trusted Root CA | ✅ installed в OS trust store | GigaChat OAuth работает |
| Stale main checkout | ⚠️ DEFERRED housekeeping | `0a9eee8` (Phase 00.1 era) vs origin/main `e8b5552`; не блокирует PR-B work (worktree base correct) |
| Stale worktrees (13 ea) | ⚠️ DEFERRED housekeeping | cleanup pin для post-PR-B-merge |

## Carryover к next session (если PR-B paused mid-flight)

Read first:
1. [`README.md`](./README.md)
2. **this HANDOFF.md** — current PR-B snapshot
3. [`STATUS.md`](./STATUS.md) — wave-progress
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md)
5. `C:\Users\KUklonskiy\.claude\plans\expressive-jumping-thimble.md` — full PR-B plan with commit ledger
6. `.planning/_session-context/AUDIT-2026-05-25-PHASE-00-6-PR-A/AUDIT-REPORT.md` — Phase 00.6 PR-A consolidated audit (input для PR-B C9 5-agent retro)

Resume point: check `git log -10 --oneline` against ledger в this HANDOFF; pick next C[N] not yet committed; mark TaskList task in_progress; execute per plan.

## Founder action queue

1. **Now (autonomous)**: PR-B C0..C6+C8 ship without founder hands (~hours of AI work).
2. **Founder gate**: see `docs/runbooks/staging-bootstrap.md` (created в C5).
3. **After 10× demo evidence hand-back**: AI ships C7+C9 + opens PR-B via `gh pr create`.
4. **Post-merge housekeeping**: update local main checkout + cleanup 13 stale worktrees.

## Exit ritual partial (this commit C0)

- [x] HANDOFF.md rewritten — full Phase 00.6 PR-A snapshot + PR-B ledger
- [x] STATUS.md rewritten — sibling C0 commit
- [ ] PR-B C1..C9 execution — pending
- [ ] JOURNAL.md PR-B entry — appended в C9 Exit ritual
- [ ] Wave-0 anchor flip — C9
- [ ] PR-B opened — C9
