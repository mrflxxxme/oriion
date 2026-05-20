# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-21 (Phase 00.5b — code-complete, audit passed, PR ready to merge)
- Session: `phase-00-5b-runtime` (worktree branch `claude/phase-00-5b-runtime`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — anchor flips at Phase 00.6 staging demo run
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (PR #25)
- **Architect-PR (pre-00.2)**: ✅ Complete (PR #27)
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (PR #28)
- **Phase 00.3 + Phase 00.4**: ✅ Complete (PR #30)
- **Phase 00.2.5 (integration)**: ✅ Complete (PR #32)
- **Pre-Phase-05 audit + nav cleanup**: ✅ Complete (PR #33)
- **Phase 00.5a (RLS foundation)**: ✅ Complete (PR #34, merge `0360955`)
- **Phase 00.5 (Pydantic-AI productivity-core team)**: ✅ **Complete** — combined 00.5a + 00.5b deliverable closed
- **Phase 00.5b (runtime + audit)**: ✅ **Code-complete + PR open** on branch `claude/phase-00-5b-runtime` (this session)

## What just happened (this session)

Phase 00.5b execution completed end-to-end in two passes:

### Pass 1 (2026-05-20) — mid-session checkpoint
- Commits 2-3 landed: router wiring + lifespan provider DI + CI per-module gate for billing + F-P5-5 router-test convention doc
- Exit-ritual checkpoint committed (`41baf7f`) marking «Commits 2-3 of 8 done; pause for continuation»
- Branch pushed to origin

### Pass 2 (2026-05-21) — completion run
- Commits 4-7 landed
- 5-agent audit swarm ran in parallel
- Commit 8 consolidates audit findings + applies in-loop fixes + lands ADR-024 §3 amendment expansion + Exit ritual
- Phase 00.5 ✅ Complete flip

## Phase 00.5b commit ledger

| # | Hash | Title | Files | +/- |
|---|---|---|---|---|
| 2 | `7c00b43` | `feat(main,llm_gateway)`: wire multitenancy+LLM routers + lifespan provider DI | 5 | +452/-32 |
| 3 | `e0aaba3` | `ci,docs`: per-module gate for billing + router-test convention | 2 | +35/-5 |
| (mid) | `41baf7f` | `docs(planning)`: Phase 00.5b mid-session checkpoint | 3 | +153/-74 |
| 4 | `8cbc7f7` | `feat(llm_gateway)`: Pydantic-AI Model adapter + canned fixture (T3) | 9 | +1041 |
| 5 | `3da3bac` | `feat(agents,iam)`: agents bounded context + productivity-core auto-spawn | 31 | +1733 |
| 6 | `fbf23d8` | `feat(tasks,runtime)`: tasks + runtime orchestrator + budget guard | 22 | +1320 |
| 7 | `6cd8808` | `test,scripts`: demo flow + 3 chat_stream tests + demo script | 6 | +1012 |
| 8 | _(this commit)_ | `chore(audit,docs)`: 5-agent audit + ADR-024 §3 expansion + Exit ritual | TBD | TBD |

**Final surface:** 39 mounted routes, 440 unit tests pass, ruff/format clean, 3 new bounded contexts (agents/tasks/runtime), 6 new alembic migrations, Pydantic-AI runtime wired, canned demo-flow CI test green.

## Decisions standing (no re-grill — verbatim from 2026-05-20)

| Topic | Decision | Status |
|---|---|---|
| **T1 — RLS Option** | Option A — SECURITY DEFINER `bootstrap_first_workspace` SQL function | ✅ Shipped 00.5a |
| **T2 — Cut-list** | MUST-LAND `F-P5-1/2/4(DS+Y+GC)/5/6`; SLIP `F-P5-3 + GigaChat-OAuth`; SKIP `M2` | ✅ MUST-LAND all closed; F-P5-3 + GigaChat-OAuth deferred to Wave-1 |
| **T3 — Mock pattern** | Custom stub at `LLMGatewayModel` level, `(role_key, scenario_id)` keying | ✅ Shipped 00.5b Commit 4 |
| **T4 — Demo shape** | Hybrid (b) — CI canned + `scripts/demo_market_brief.py` runs Phase 00.6 staging | ✅ Both halves shipped; AC8/AC10 PROVEN-IN-CI-canned / VALIDATED-IN-STAGING pending 00.6 |
| **T5 — Prompts** | First-pass alignment hardening; stays 0.x first-draft per ADR-010; v1.0.0 Phase 01.1 retro | ✅ Shipped (frontmatter + 9-section parse enforced; backlog pinned in AC14 / AC-W1) |
| **E1 — M2 refactor** | SKIP this PR — Phase 00.6 standalone | ✅ Skipped per decision |
| **E2 — ADR-024 amendment** | LAND 3-line amendment | ✅ Already-existed amendment touched-up + expanded to enumerate Phase 00.5b new cross-context import (`runtime → tasks.{models,events,exceptions}` Exception #2). Compliance audit F-CMP-N2 noted the framing was stale; the substance is sound. |
| **E3 — ADR-014 honesty-pass** | Lands in 00.5a | ✅ Shipped 00.5a (re-verified by Phase 00.5b Compliance Auditor F-CMP-H1) |
| **E4 — pytest-xdist** | DO NOT enable (F-12 preconditions unmet) | ✅ Not enabled |
| **E5 — Cross-context imports** | No new sanctioned exceptions without ADR-024 amendment in SAME PR | ✅ Honored: Exception #2 lands in same PR as the runtime → tasks import |

## Audit findings — final disposition

| ID | Severity | Status |
|---|---|---|
| F-SEC-H1 | HIGH | ✅ FIXED IN-LOOP (Commit 8) — 3 routers migrated to `get_tenant_db_session` |
| F-ARC-H1 | HIGH | ✅ FIXED IN-LOOP (Commit 8) — ADR-024 §3 Exception #2 added |
| F-ARC-H2 | HIGH | 🟡 DEFERRED Wave-1 (AC-W1-1) — SSEPublisher Redis-pubsub swap |
| F-CR-M1 | MEDIUM | ✅ FIXED IN-LOOP — orchestrator token-split bug removed |
| F-CR-M3 | MEDIUM | ✅ FIXED IN-LOOP — `_LLMGatewayLifespanNotReady` + 503 RFC-7807 envelope |
| F-ARC-M1 | MEDIUM | ✅ FIXED IN-LOOP — `LLMGatewayModel.request_stream` explicit NotImplementedError |
| F-ARC-M2 | MEDIUM | ✅ FIXED IN-LOOP — orchestrator emits `task.failed` on exception + refunds budget |
| F-CR-M2 / F-ARC-M4 | MEDIUM | 🟡 DEFERRED Phase 00.6 — extract 3-GUC helper into `_shared/db/rls.py` |
| F-ARC-M3 | MEDIUM | 🟡 DEFERRED Wave-1 (AC-W1-7) — `NullTeamProvisioningService` no-op default |
| F-ARC-M5 | MEDIUM | 🟡 DEFERRED Wave-1 — domain exception in delegate_task no-runner branch |
| F-SEC-M1/M2/M3 | MEDIUM | 🟡 DEFERRED Wave-1 (AC-W1-1 / AC-W1-8 / AC-W1-9) |
| F-TR-M1/M2 | MEDIUM | 🟡 DEFERRED Wave-1 (AC-W1-5 + suite reorganization) |
| F-CMP-M1/M2 | MEDIUM | 🟡 DEFERRED Phase 01.1 (Master-Agent schema extension parallel to ADR-029) |
| 17 LOW findings | LOW | 🟡 DEFERRED Wave-1 hygiene pass |

Master report: [`_session-context/AUDIT-2026-05-20-PHASE-00-5/AUDIT-REPORT.md`](./_session-context/AUDIT-2026-05-20-PHASE-00-5/AUDIT-REPORT.md)

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## Next agent — read first (bootstrap-4)

1. [`README.md`](./README.md)
2. [`STATUS.md`](./STATUS.md)
3. **this HANDOFF.md**
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md)

Then for Phase 00.6:

5. [`roadmap/wave-0-foundation/phases/00.6-deploy-observability.md`](./roadmap/wave-0-foundation/phases/00.6-deploy-observability.md)
6. [`_session-context/AUDIT-2026-05-20-PHASE-00-5/AUDIT-REPORT.md`](./_session-context/AUDIT-2026-05-20-PHASE-00-5/AUDIT-REPORT.md) — Wave-1 AC pin block lifts into Phase 01.1 retro
7. [`gates/wave-0-to-1.md`](./gates/wave-0-to-1.md) — D5 gate evidence collected by Phase 00.6 staging run via `backend/scripts/demo_market_brief.py --runs 10`

## Founder action

1. **Review + merge Phase 00.5b PR** (open after this commit lands). The PR squashes 8 commits worth of work + audit + Exit ritual into a single review session. Audit findings disposition table above is the source of truth — every HIGH is either fixed in-loop or has an explicit Wave-1 AC pin.
2. **Open Phase 00.6 worktree** post-merge:
   ```powershell
   git checkout main; git pull origin main
   git worktree add .planning/.claude/worktrees/phase-00-6-deploy -b claude/phase-00-6-deploy
   cd .planning/.claude/worktrees/phase-00-6-deploy
   # Bootstrap-4 reads, then phase-spec 00.6-deploy-observability.md
   # Then: scripts/demo_market_brief.py --runs 10 against staging
   # Collects AC8 (p95 ≤120s) + AC10 (cost ≤30¢) evidence → flips Wave-0 anchor
   ```
3. **Phase 00.6 deliverables** (per gates/wave-0-to-1.md D5):
   - Yandex Cloud staging deploy (Docker Compose → managed PG + Redis)
   - Live LLM provider keys provisioned (DeepSeek + YandexGPT + GigaChat OAuth)
   - 10× run of `demo_market_brief.py` against staging → JSON ledger + summary
   - AC8 + AC10 PROVEN-IN-STAGING; Wave 0 anchor flips
   - Phase 01.1 retro opens with AC-W1-1..10 from AUDIT-REPORT.md

## Known caveats (carryover + deferred)

- **AC8 + AC10 measurement** (p95 ≤120s; cost ≤30¢) — VALIDATED-IN-STAGING pending Phase 00.6. The runnable `scripts/demo_market_brief.py` is the gate-evidence collector; Phase 00.5b ships it but does NOT execute in CI (no live keys).
- **F-P5-3 (testcontainers PG migration)** — SLIP-candidate per Topic 2, deferred to Wave-1 AC-W1-5.
- **F-P5-4 GigaChat OAuth refresh-after-expiry test** — SLIP-candidate per Topic 2, deferred to AC-W1-10.
- **2026-06-09 Wave-0 deadline confidence**: was ~65% pre-Phase-05 / ~78% post-Phase-00.5b (Compliance Auditor estimate). Phase 00.5b chunking discipline (00.5a + 00.5b) added zero calendar overhead.
- **Slug-based cross-tenant linkage** (Wave-1 backlog) — unchanged.
- **TOCTOU SSRF in `read_url`** — Wave-1 hardening, unchanged.
- **`alembic.ini` cp1251 on Windows** — Phase 00.6 cleanup, unchanged.
- **Live LLM provider tests (`@pytest.mark.live`)** — Phase 00.6 once provider keys provisioned.
- **F-ARC-H2 SSEPublisher multi-worker** — Wave 0 deploys with `workers=1` per Phase 00.6 spec; Wave 1 Redis pubsub swap on AC-W1-1.

## Pitfalls confirmed (final)

- Worktree-prefixed absolute paths in Edit/Write.
- `oriion_app` role canary in CI (verified green in Phase 00.5b suite).
- `rbac.system_roles` natural key is `slug` (NOT `code`).
- ADR-024 §3 amendment lands in SAME PR as the cross-context import that needs sanction (verified for runtime → tasks Exception #2).
- pytest-xdist remains disabled.
- `.claude/settings.local.json` gitignored.
- Pip-audit `PYSEC-2025-183` ignore preserved in ci-backend.yml; no NEW ignores added by pydantic-ai 1.30 + opentelemetry transitive chain (verified by Compliance F-CMP-L2).
- **Lifespan + tests:** `tests/integration/test_e2e_auth_flow.py::app` fixture uses `dependency_overrides`-only path; demo-flow test bypasses lifespan via direct orchestrator invocation. Production handlers that depend on lifespan-built `app.state` (llm_gateway endpoints) hit the new `_LLMGatewayLifespanNotReady(LLMGatewayException)` → 503 RFC-7807 envelope if lifespan didn't run.

## Exit ritual completed (this session)

- [x] JOURNAL.md entry appended (top-of-file timestamped block)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md updated — Phase 00.5 + Phase 00.5b ✅ Complete; AC scoreboard final
- [x] AUDIT-REPORT.md master + 5 section files written to `_session-context/AUDIT-2026-05-20-PHASE-00-5/`
- [x] ADR-024 §3 amendment expanded with Phase 00.5b Exception #2
- [x] All HIGH findings either fixed in-loop or have explicit Wave-1 AC pin
- [x] Plan file persists at `C:\Users\KUklonskiy\.claude\plans\crispy-crunching-sunset.md`
- [ ] **PR opened** — final step of this session (after Commit 8 lands)
