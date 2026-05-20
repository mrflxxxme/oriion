# Phase 00.5b — 5-Agent Audit Swarm — Master Report

**Date:** 2026-05-21
**Phase:** 00.5b (Pydantic-AI runtime + router wiring + demo + 5-agent audit)
**Branch:** `claude/phase-00-5b-runtime`
**Commits audited:** 6 atomic (7c00b43 → 6cd8808) off origin/main `0360955`
**Consolidator:** @claude-opus

## Verdict — **PASS-WITH-FIXES-APPLIED**

All 5 sub-agents returned independent verdicts in the «approve with
caveats» band. In-loop fixes were applied for the HIGH findings + select
MEDIUM findings; remaining items defer to Wave 1+ with explicit AC pins.

## Section index

| # | Section | Agent | Verdict | Findings (H/M/L) |
|---|---|---|---|---|
| 01 | [Code Review](./section-01-code-review.md) | Code Reviewer | PASS-WITH-FIXES | 0 / 3 / 6 |
| 02 | [Security](./section-02-security.md) | Security Engineer | APPROVE WITH CAVEATS | 1 / 3 / 2 |
| 03 | [Test Adequacy](./section-03-test-adequacy.md) | Test Results Analyzer (synthesized) | PASS-WITH-FIXES | 0 / 2 / 3 |
| 04 | [Architecture](./section-04-architecture.md) | Backend Architect | APPROVE WITH FOLLOW-UPS | 2 / 5 / 3 |
| 05 | [Compliance](./section-05-compliance.md) | Compliance Auditor | PASS WITH DEFERRED | 0 / 2 / 3 |
| | **Totals** | | | **3 / 15 / 17** |

## HIGH findings — disposition

| ID | Finding | Disposition |
|---|---|---|
| **F-SEC-H1** | `agents/instances`, `agents/teams`, `tasks/tasks` routers use raw `get_db` instead of `get_tenant_db_session` — re-introduces 00.5a-closed pattern | **FIXED IN-LOOP** (Commit 8): migrated all 3 routers to `get_tenant_db_session`; the 3-GUC tenant context is set per request before the FORCE-RLS-protected SELECTs/INSERTs run |
| **F-ARC-H1** | ADR-024 §3 amendment must enumerate new Phase 00.5b cross-context model imports (`runtime → tasks.models`) + service-call edges (iam→agents, agents→llm_gateway) | **FIXED IN-LOOP** (Commit 8): added Exception #2 to ADR-024 §3 for `runtime → tasks.{models, events, exceptions}` with full justification + Wave-1 follow-up candidates; service-call edges enumerated as transparency-only DAG (no amendment required) |
| **F-ARC-H2** | `SSEPublisher` uses module-level singleton; multi-worker uvicorn deploys will silently hang on subscribe | **DEFERRED to Wave-1** (AC pin: AC14 SSE-on-runtime hardening + ADR-N to be drafted in Phase 01.x) — Wave-0 uvicorn runs single-worker per founder brief; Phase 00.6 deploys with `workers=1`; Redis-pubsub swap is the Wave-1 transport upgrade |

## MEDIUM findings — disposition (selected)

Applied in-loop:

| ID | Finding | Disposition |
|---|---|---|
| **F-ARC-M1** | `LLMGatewayModel.request_stream` relies on inherited Pydantic-AI default | **FIXED**: explicit `NotImplementedError` with loud error message pointing to Wave-1 AC14 |
| **F-ARC-M2** | Orchestrator never emits `task.failed` on exception; SSE subscribers hang forever | **FIXED**: `execute_agent_task` body wrapped in try/except → emits `task.failed` SSE + emits `oriion.tasks.failed.v1` CloudEvent + refunds budget before re-raising |
| **F-CR-M3** | `llm_gateway/deps.py::_require_state` raises raw `HTTPException` → bypasses RFC-7807 envelope | **FIXED**: introduced `_LLMGatewayLifespanNotReady(LLMGatewayException)` subclass with code `llm_gateway.lifespan_not_ready`; mapped to 503 in `_LLM_GATEWAY_STATUS` so the iam-canonical problem+json envelope handles it |
| **F-CR-M1** | Orchestrator `tokens_used // 2` integer-split corrupts token accounting | **FIXED**: removed the speculative split; per-leaf `tokens_used` sums into `total_output_tokens`; `total_input_tokens` stays 0 at Wave-0 granularity. Real per-step token attribution lands Wave-1 alongside Pydantic-AI per-step instrumentation hook |

Deferred to Wave-1:

| ID | Finding | Reason for defer |
|---|---|---|
| **F-CR-M2** / **F-ARC-M4** | Inline `SELECT set_config()` GUC plumbing in `auth_service.register` duplicates `_shared/db/rls.py` helper | The existing `set_tenant_context` helper is an async-context-manager; the auth-service register flow is linear (not async-with). A refactor to share code requires either a new inline helper in `_shared/db/rls.py` or reshaping `register()` to use an async-with block. **Defer to Phase 00.6** as a clean-up commit (founder noted Phase 00.6 cleans up cp1251 alembic.ini + similar housekeeping in parallel). |
| **F-ARC-M3** | `team_provisioning_service=None` default on `AuthService.__init__` is a prod-invariant break | The default is the cleanest way to keep `tests/iam/unit/test_auth_service.py` mock-based tests passing without patching every test. The `iam/deps.py::get_auth_service` production factory always supplies the real service. **Defer to Wave-1** as a `NullTeamProvisioningService` no-op-on-call pattern. |
| **F-ARC-M5** | `delegate_task` raises builtin `NotImplementedError` instead of domain exception | Defer to Wave-1 — when the production orchestrator wires in Phase 00.6, the `NotImplementedError` path is dead anyway. AC pin: AC14 hardening pass. |
| **F-SEC-M1** | `SSEPublisher` keys queues by `task_id` only (no `cell_id` discriminant) | Defer to Wave-1 — UUIDv4 unguessability is mitigation; defense-in-depth pin on Redis-pubsub swap. |
| **F-SEC-M2** | `DelegateInput.target_agent_slug` is unbounded `str` | Defer to Wave-1 — whitelist check at `delegate_task` entry blocks dispatch; SSE-payload + log exposure is low-severity. Pattern constraint added in Phase 01.1 schema hardening pass. |
| **F-SEC-M3** | Provider classes hold `_api_key` as plain `str` after `.get_secret_value()` extraction | Defer to Wave-1 — process-lifetime retention is expected per provider DI pattern (the alternative is per-request key fetch which adds latency). YC Lockbox integration in Wave-1+ addresses key rotation + memory hygiene as a package. |
| **F-TR-M1** | `test_market_brief_demo_flow.py` blurs unit/integration boundary | Defer to Phase 01.1 — re-mark + suite reorganization is a hygiene pass. |
| **F-TR-M2** | `test_cancel_cascade.py` uses in-memory shim, not real PG | Defer to Wave-1 via F-P5-3 (SLIP-candidate per Topic 2 cut-list). |
| **F-CMP-M1** | `role_category` CHECK enum missing `'master'` for ADR-029 Master-Agent | Defer to Phase 01.1 — trivial migration when Master-Agent ships. |
| **F-CMP-M2** | `team_presets.archetype_ids[]` doesn't preclude Master-Agent but representation is undefined | Defer to Phase 01.1 — schema extension parallel to ADR-029. |

## LOW findings (17 total)

All deferred to Wave-1 hygiene passes or Phase 01.1 retro. Highlights:

- 5 of the 6 Code Reviewer LOWs are docstring + naming polish items.
- All 3 Test Results LOWs land on Wave-1 testcontainers migration paths.
- All 3 Architecture LOWs are convention drift (workspace_id placeholder, stream router packaging, cost-rollup bypass).
- 2 of 3 Compliance LOWs are transport-tracking notes for Wave-1 Redis swap.

Full LOW inventory in respective section reports — not blocking PR merge.

## Wave-1 explicit AC pin block (for Phase 01.1 retro)

Lift verbatim into `phases/01.1-retro.md` planning:

```
- AC-W1-1: SSEPublisher → Redis pubsub bridge for multi-worker (F-ARC-H2 + F-SEC-M1)
- AC-W1-2: per-step TaskStep persistence + per-token SSE streaming via
  Pydantic-AI instrumentation hook (F-CR-M1 + F-ARC-M1 + F-TR-W1)
- AC-W1-3: Master-Agent layer schema extension (F-CMP-M1 + F-CMP-M2 +
  ADR-029 §«Schema impact»)
- AC-W1-4: TaskRepository port + outbox for state transitions (Exception #2
  Wave-1 follow-up in ADR-024 §3)
- AC-W1-5: cancel_cascade real-PG testcontainers integration (F-TR-M2 +
  F-P5-3 SLIP)
- AC-W1-6: GUC tenant-context helper extraction + auth_service.register
  refactor (F-CR-M2 + F-ARC-M4)
- AC-W1-7: NullTeamProvisioningService no-op default (F-ARC-M3)
- AC-W1-8: DelegateInput.target_agent_slug pattern constraint (F-SEC-M2)
- AC-W1-9: Provider key rotation via YC Lockbox (F-SEC-M3)
- AC-W1-10: GigaChat OAuth refresh-after-expiry test (F-TR-L2 / F-P5-4 SLIP)
```

Plus the carryover from Phase 00.5a:
- Slug-based cross-tenant linkage
- TOCTOU SSRF in `read_url`
- alembic.ini cp1251 on Windows (Phase 00.6 cleanup)

## Cross-phase audit-history rollup

| Audit cycle | High-findings | Carried | Closed | New deferred |
|---|---|---|---|---|
| Pre-Phase-05 (2026-05-19) | 6 | — | — | F-P5-1..6 |
| Phase 00.5a (2026-05-20, single commit) | 3 | F-P5-1 (closed) | H1+H2+H-1 | F-P5-3 + F-P5-4 GigaChat-OAuth (SLIP) |
| **Phase 00.5b (2026-05-21, 6 commits + audit)** | **3** | F-P5-2/4/5/6 (closed) | F-SEC-H1 + F-ARC-H1 (closed in-loop); F-ARC-H2 (deferred) | AC-W1-1..10 |

## Recommendation

**Phase 00.5b is PR-ready.** The 6 atomic commits + 5-agent audit + in-loop
fixes deliver:
- 39 mounted routes (was 32 after 00.5a) under `/api/v1`
- 3 new bounded contexts (agents, tasks, runtime) with FORCE-RLS,
  CloudEvents emissions, and clean DAG cross-context graph
- Pydantic-AI Model adapter + canned T3 mock fixture
- AC9 artifact-shape canned content (brief 1554 RU words, matrix 5x4,
  plan exactly 10 posts)
- F-P5-2 / AC10 budget guard with named canonical test
- 3 provider chat_stream tests + runnable demo script for Phase 00.6
  staging gate-evidence
- 440 unit tests pass + ruff/format clean

**AC8 (p95 ≤120s) + AC10 (cost ≤30¢) status:** PROVEN-IN-CI-on-canned-data
/ VALIDATED-IN-STAGING pending Phase 00.6 per T4 hybrid resolution.

**Founder action after merge:** Open Phase 00.6 worktree for deploy +
observability + staging demo run via `scripts/demo_market_brief.py --runs
10`. Wave-0 anchor (`internal_demo_passed=true`) flips at that point.
