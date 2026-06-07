# Phase 00.6 FINAL — 5-Agent Retrospective Audit Report

**Date:** 2026-05-26
**Phase:** 00.6 (PR-A Stage A + PR-B Stage B — full surface)
**Branch audited:** `claude/gallant-lamport-f48eca` (PR-B commits 165b6ea→37bb934, off origin/main e8b5552)
**Auditor mode:** **Full 5-agent swarm** (per Phase 00.5b precedent template; corrects the PR-A Q7-IV departure to a consolidated self-audit)
**Run timing:** Audit executed **before** the founder gate (terraform apply + 10× demo), deliberately — so any code-level HIGH surfaces *before* money is spent on real infra + the 10× run.

## Verdict — **PASS** (PR-B code surface)

All 3 PR-B-specific HIGH findings were **fixed in-loop** in the same PR-B (commit C9). Per the founder G11 disposition («PR-B-specific HIGH → MUST fix in-loop before C9 commit; anchor flip proceeds if PR-B surface = PASS»), the PR-B code surface is now PASS.

> **Anchor flip is NOT yet substantiated** — it is blocked on the founder gate
> (F-CMP-2): the 10× demo evidence bundle (`summary.json` + `run_001..010.json`
> + screen-recording) must physically land in `.planning/gates/evidence/wave-0-to-1/`
> and the gate frontmatter (`actual=true, passed=true, evidence_url, measured_at`)
> must be populated **in the same commit that flips the anchor** (C9-flip, after C7).
> The audit clears the *code*; the founder run clears the *evidence*.

## Section index

| # | Section | Persona | Verdict | H/M/L |
|---|---|---|---|---|
| 01 | Code Review | Code Reviewer | PASS-WITH-FIXES → **PASS** (fixes applied) | 2 / 3 / 4 |
| 02 | Security | Security Engineer | APPROVE WITH CAVEATS | 0 / 3 / 4 |
| 03 | Test Adequacy | Test Results Analyzer | PASS-WITH-FIXES → **PASS** (fixes applied) | 1 / 2 / 2 |
| 04 | Architecture | Backend Architect | APPROVE WITH FOLLOW-UPS → **PASS** (fix applied) | 1 / 3 / 4 |
| 05 | Compliance | Compliance Auditor | PASS WITH DEFERRED | 0 / 3 / 2 |
| | **Totals** | | | **4 / 14 / 16** |

(Section files: `section-01-code-review.md` … `section-05-compliance.md`.)

## HIGH findings — disposition (ALL FIXED IN-LOOP)

| ID | Finding | Fix (in-loop, commit C9) |
|---|---|---|
| **F-CR-1 / F-TR-1** (same defect, found by 2 agents independently) | Demo AC9 content-plan parser `^\s*\d+\.\s+\*\*` did not match the writer role-prompt's real idiom `### Пост N — <channel> — <day>` (H3 headers, writer.md §6 few-shot). Real 10× run → `content_plan_posts == 0` → **AC9 FAIL on every run**. The unit test passed only because its fixture was synthetic ("test asserts the wrong contract"). Would have wasted the founder's terraform apply + 10× run. | `demo_market_brief.py::_count_content_plan_posts` now matches BOTH `^###\s+Пост\s+\d+` (real) and the numbered-bold fallback. Test fixture `_content_plan_block()` rewritten to the **real H3 idiom** (proves real shape) + a backward-compat test for the numbered form. Belt-and-suspenders: the `dispatch.py` writer sub-prompt now **pins** the `### Пост N` format explicitly. |
| **F-CR-2** | Orchestrator failure-path DB state silently rolled back: `run_task`'s `await db.commit()` was unreachable on exception (orchestrator sets `status='failed'` then re-raises → propagates past the commit → `get_db` rolls back) → row stays `queued` while SSE says `failed` (DB/stream divergence + lost failure audit trail). | `run_task` wraps `dispatch_task` in `try/except`; on exception it `await db.commit()`s the failed-state write **before** re-raising. New test `test_run_task_dispatch_failure_commits_then_propagates` asserts commit-then-propagate. |
| **F-ARC-1** | ADR-024 §3 Exception #2 governance rule requires every file on a sanctioned cross-context edge to be recorded with file:line. PR-B added `runtime/dispatch.py` on the existing `runtime → tasks.models.Task` edge but didn't record it; the Status line still claimed "no new sanctioned imports as of Phase 00.5b". | ADR-024 §3 Exception #2 now lists `runtime/dispatch.py` (same blessed edge, no new justification) + records the reverse `tasks/routers → runtime` function-import edge as sanctioned-by-default. Status line bumped with the 2026-05-26 amendment. |

## MEDIUM findings — disposition

**Fixed in-loop (cheap + high-value):**
- **F-CR-8** — AC9 matrix check was column-blind (counted rows, not the ≥4-column requirement). Added `_matrix_max_cols` + `AC9_MATRIX_MIN_COLS=4` gate + `matrix_cols` evidence field + test `test_evaluate_ac9_rejects_too_few_matrix_columns`.
- **F-CR-4** — Documented (one-line note in `ScriptedCoordinator.run`) that it intentionally bypasses the `delegate_task` tool guards (safe for the fixed 3-step pipeline; real Coordinator re-enables them — AC-W1-16).
- **F-TR-2** — Added `test_run_task_unknown_id_returns_404` (the TaskNotFound→404 branch was untested).
- **F-CMP-4** — Resolved the `AUDIT-2026-05-XX` placeholder → `AUDIT-2026-05-26` in `01.1-retro.md` provenance.

**Deferred to Wave-1 (named pins):**
- **F-CR-3** — redundant double-commit + RLS-GUC teardown ordering (harmless; nothing runs after the commit) → tidy in AC-W1-16 (Dramatiq owns its TX boundary).
- **F-CR-5 / F-TR-3** — parent `total_input_tokens` zeroed + heuristic brief-word/matrix parsing → AC-W1-13 (real per-callsite billing + typed artifact fields).
- **F-SEC-M1/M2/M3** (per section-02) → existing AC-W1 security pins (header sanitization AC-W1-11; SSH ingress tightening; etc.).
- **F-ARC-2/3/4** — inline dispatch blocks request thread / no auto-pickup after POST /tasks / single-TX failure divergence → AC-W1-16 (Dramatiq actor with its own TX boundary + 202-immediate).
- **F-CMP-1** — Object Storage explicit residency pin → AC-W1-14 (Loki archival wiring).

## LOW findings (16 total)

All deferred to Wave-1 hygiene passes / Phase 01.1 retro per their section dispositions. Notable: **F-CR-9** (`get_task`/`run_task`/`cancel_task` ignore the path `cell_id`, relying solely on RLS — pre-existing, not PR-B-introduced) → Wave-1 pin to add a `task.cell_id == cell_id` assertion for honest path semantics. **F-CR-7** (`wait_healthy.sh` treats no-healthcheck containers as healthy) → deploy-hardening pin. **F-CMP-3** (screen-recording has no format spec) → add a one-line evidence spec to the runbook before recording. **F-CMP-5** (SSH 0.0.0.0/0) → already in-code Wave-1 note.

## Dimension highlights (validated, no blocker)

- **Security** (APPROVE WITH CAVEATS): `terraform.tfvars` + `*.tfstate*` gitignored (verified); Lockbox sources all secrets from `sensitive` vars; managed PG/Redis no public IP; ФЗ-152 zone validation is a hard `terraform plan` fail; GHA secrets not echoed beyond the documented `docker login --password-stdin` pattern.
- **Architecture** (PASS post-fix): inline-synchronous + ScriptedCoordinator are the correct minimal Wave-0 calls given the deferred LLMGatewayModel tool-call path; `workers=1` invariant is **enforced** in compose, not just documented; AC-W1-16 is a correct + sufficient Wave-1 pin; Terraform 7-file decomposition sound (state chicken-and-egg handled, DNS count-gated, ФЗ-152 enforced).
- **Test** (PASS post-fix): AC13 per-module gate holds (runtime 95.88%, tasks 96.13%); new tests are behavioural, not coverage-padding; AC8 cohort + AC10 (provisional pricing, AC-W1-13) provable; AC9 now provable post-F-TR-1 fix.
- **Compliance** (PASS WITH DEFERRED): gate D5 amendment does **NOT** drift from ADR-026 Level B (disjoint scopes — horizontal demo vs vertical-template anti-hallucination); AC7 deferral traceable across 3 artifacts; anchor-flip evidence **design** is audit-grade; ADR-018 V4 amendment governance-complete.

## Post-fix verification

```
ruff check src tests scripts        → All checks passed
mypy --strict src                   → Success (145 files)
pytest tests/runtime --cov=src/runtime --cov-fail-under=85 → 95.88% PASS
pytest tests/tasks   --cov=src/tasks   --cov-fail-under=85 → 96.13% PASS
pytest tests -q -m 'not integration and not live'         → 539 passed, 23 deselected
```

## Cross-phase audit-history rollup

| Audit cycle | High | Carried | Closed | New deferred |
|---|---|---|---|---|
| Pre-Phase-05 (2026-05-19) | 6 | — | — | F-P5-1..6 |
| Phase 00.5a (2026-05-20) | 3 | F-P5-1 | H1+H2+H-1 | F-P5-3/4 |
| Phase 00.5b (2026-05-21) | 3 | F-P5-2/4/5/6 | F-SEC-H1 + F-ARC-H1; F-ARC-H2 deferred | AC-W1-1..10 |
| Phase 00.6 PR-A (2026-05-25) | 0 | — | F-CR-M2/cp1251 | AC-W1-11..15 |
| **Phase 00.6 FINAL (2026-05-26)** | **4 → 0** | — | **F-CR-1/F-TR-1, F-CR-2, F-ARC-1 fixed in-loop** | AC-W1-16/17 + the M/L pins above |

## Recommendation

**Phase 00.6 PR-B code surface is PASS.** Remaining path to Wave-0 anchor flip:
1. **Founder gate** (task #10) — `terraform apply` + DNS + `gh secret/var set` + first deploy + seed demo user + 10× demo run + screen-recording, per `docs/runbooks/staging-bootstrap.md`. The F-CR-1 fix means the 10× run should now score AC9 correctly on real writer output.
2. **C7** — commit the 10× evidence bundle.
3. **C9-flip** — flip `internal_demo_passed: actual=true, passed=true` (with `evidence_url` + `measured_at`) in the SAME commit, finalize the Exit ritual (HANDOFF/STATUS/JOURNAL + phase-spec status → Complete), mark PR #37 ready-for-review.
