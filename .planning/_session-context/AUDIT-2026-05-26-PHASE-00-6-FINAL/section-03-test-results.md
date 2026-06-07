## Section 03 — Test Adequacy

**Auditor:** Test Results Analyzer
**Scope:** Phase 00.6 PR-B test adequacy (runtime/dispatch, tasks/run endpoint, demo collector) + AC13 per-module strict-coverage gate + 10× demo cohort evidence sufficiency.
**Date:** 2026-06-07

---

### Verdict: **PASS-WITH-FIXES**

The AC13 per-module strict-coverage gate (≥85% for `agents`/`tasks`/`runtime`) **still holds** after PR-B's C1 changes — both gated runs cleared the bar with large margin and the full suite is green. The new tests are genuinely behavioural, not coverage-padding: they assert pipeline order, child-task persistence, cost arithmetic, version-tolerant extract helpers, the 202/409 dispatch gate, and the cohort-AC8 exit-code policy. The single material problem is **evidence-validity, not coverage**: the demo collector's AC9 content-plan parser is coupled to a markdown idiom (`N. **...**`) that the *production* writer role-prompt does not teach — the LLM is instructed to emit `### Пост N` (H3) headers. The unit test passes only because its fixture is hand-built in the parser's expected shape, so the green test does not prove the collector can score real staging output. That makes the AC9 leg of the 10× anchor **unprovable as currently wired** (H). Everything else is solid.

---

### Measured coverage (this run, win32 / py3.12.13)

| Module gate | Command | Result | Total cover | Notable misses |
|---|---|---|---|---|
| **runtime** | `pytest tests/runtime --cov=src/runtime --cov-fail-under=85` | **38 passed**, gate PASS | **95.88%** | `dispatch.py` 97% (lines 113, 304→307); `orchestrator.py` 94% (212, 216 = failure-path SSE); `sse_publisher.py` 93% |
| **tasks** | `pytest tests/tasks --cov=src/tasks --cov-fail-under=85` | **38 passed**, gate PASS | **96.08%** | `tasks.py` router 98% (line 25 docstring/def); `stream.py` 55% (SSE body, not PR-B scope); `task_service.py` 97% |
| **scripts** | `pytest tests/scripts -q` | **11 passed** | n/a (no gate) | — |
| **full suite** | `pytest tests -q -m 'not integration and not live'` | **534 passed, 23 deselected** | — | green |

`src/runtime/dispatch.py` itself: **97%** (98 stmts, 1 miss + 2 partial branches — line 113 `str(output)` final fallback in `_extract_output_text`, and the `304→307` branch where `task.input_jsonb` is not a dict). `src/tasks/routers/tasks.py` (the `/run` endpoint): **98%**. The AC13 gate is intact.

---

### Strengths

1. **AC13 gate genuinely honoured post-C1.** Both per-module strict runs pass with ~96% and the inline-dispatch surface (`dispatch.py` 97%, `run_task` endpoint 98%) is the *new* code carrying the coverage — not legacy padding.
2. **`test_dispatch.py` tests real seams, not trivia.** `test_scripted_coordinator_drives_pipeline_in_order` asserts exact `[researcher, analyst, writer]` call order AND the per-slug artifact-kind map (`matrix/analysis/brief`). `test_scripted_coordinator_chains_prior_output_into_sub_prompt` proves the chaining contract (researcher sees only the user prompt; writer sees both prior outputs). `test_build_leaf_runner_creates_child_task_and_costs` validates child-`Task` persistence (parent_task_id, cell_id, user_id, status='succeeded', token roll-in) AND that `cost_credits == estimate_credits(...)`. The version-tolerant `_extract_output_text`/`_extract_usage` helpers are tested against both the `.data` fallback and the old `request_tokens/response_tokens` aliases — exactly the defensive branches that exist for Pydantic-AI version drift.
3. **`dispatch_task` wiring is end-to-end tested** with an in-process publisher: `test_dispatch_task_runs_orchestrator_and_returns_output` asserts the SSE ledger order `[task.started, task.completed]` and `task.status == 'succeeded'`, using a no-delegation coordinator stand-in so it stays off the real LLM layer.
4. **The 202/409 dispatch gate is correctly tested.** `test_run_task_dispatches_queued_task_returns_202` patches `dispatch_task` and asserts the call + commit; `test_run_task_non_queued_returns_409` asserts a `running` task is NOT re-dispatched (`mock_dispatch.assert_not_awaited()`) and returns `tasks.not_dispatchable`. Idempotency-of-dispatch is honestly covered.
5. **Demo exit-code policy is well-tested.** `test_exit_code_one_ac_failure_strict_is_one_tolerant_is_zero` proves the strict-vs-`--tolerate-failures 1` (D5 «≥9/10» founder latitude) divergence; transport-error→2 and slow-cohort→1 are distinct cases. The cohort-p95 semantics (`statistics.quantiles n=20` index 18) and slow-cohort flagging are both asserted.
6. **The ScriptedCoordinator known-limitation is honestly documented** in `dispatch.py` module docstring, the `ScriptedCoordinator` class docstring, and `run_task`'s docstring — all three explicitly cite AC-W1-16 for the real LLM-driven Coordinator swap and state the full tool-call path is NOT exercised. This is disclosed, not hidden.

---

### Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| **F-TR-1** | **HIGH** | **AC9 content-plan parser cannot prove the anchor against real output.** `demo_market_brief.py::_count_content_plan_posts` matches `^\s*\d+\.\s+\*\*` (numbered + bold). The production writer role-prompt (`.planning/contracts/role-prompts/writer.md`, §6 few-shot) teaches the content-plan idiom as `### Пост N — <channel> — <day>` (H3 headers), with no numbered-bold list. The unit test `test_count_content_plan_posts` passes only because its `_content_plan_block()` fixture is hand-built in the regex's shape. On real staging output the parser will likely count **0 posts**, forcing `content_plan_posts == 10` to FAIL for every run → AC9 reports false-negative → demo exits 1 even on a correct brief. The collector therefore **cannot reliably prove AC9** for the Wave-0 anchor. | **FIX before 10× run.** Either (a) broaden the regex to also match `^###\s+Пост\s+\d+` (the prompt's actual idiom), or (b) add a fixture that mirrors the writer few-shot exactly and assert against it, or (c) tighten the writer prompt to mandate the numbered-bold list. Recommend (a)+(b): make the parser idiom-tolerant and pin a realistic fixture so the test proves the real shape. |
| **F-TR-2** | **MED** | **No 404 / cross-tenant path test for the `/run` endpoint.** `run_task` calls `service.get_task(task_id)` whose docstring says "raises TaskNotFound → 404", but no test exercises that branch (the `_FakeTaskService.get_task` never raises). Cross-tenant isolation (RLS) is also untested at this endpoint — `cell_id` is accepted in the path but discarded (`_ = cell_id`), with tenant scoping delegated entirely to the DB GUC, which the unit layer cannot see. A regression that swallows `TaskNotFound` or mis-binds the session would pass CI. | **FIX (follow-up).** Add `test_run_task_unknown_id_returns_404` (fake service raises `TaskNotFound`). Cross-tenant RLS is genuinely out of unit scope — note it explicitly as covered only by the integration/live tier (AC-W1 hardening) so the gap is on the record, not silent. |
| **F-TR-3** | **MED** | **AC9 brief-words + matrix-rows parsers share the same "tested against synthetic, not real" risk as F-TR-1, though lower.** `_count_matrix_rows` assumes a leading-pipe markdown table (researcher idiom) and `brief_words` is a naive `.split()` over the `brief` artifact — but the writer prompt's brief includes YAML frontmatter, headers, and the content-plan inside the same `brief` artifact, so `brief_words` counts frontmatter/markup tokens too (inflates toward passing) while matrix-row counting depends on the researcher emitting a pipe table (plausible but unverified against that role-prompt). The 1500-word threshold is thus measured loosely. | **ACCEPT with note** for Wave-0 (the inflation biases toward pass, and 1500 is a floor not a cap). Flag for AC-W1: replace heuristic parsing with structured artifact fields once the writer emits a typed `content_plan: list` instead of free markdown. |
| **F-TR-4** | **LOW** | **The orchestrator failure-path (`task.failed` SSE + budget refund, lines 167–192) is not exercised by the dispatch tests.** `orchestrator.py` shows 94% with misses at 212/216 (the `output is None` and `str(output)` fallbacks). The failure path IS covered by `tests/runtime/test_orchestrator.py` (per dispatch test docstring), so this is not a true gap for runtime, but `dispatch_task` never asserts a failed-run propagates `task.failed` through its own wiring. | **ACCEPT.** Covered at the orchestrator layer; a dispatch-level failure assertion would be additive, not blocking. |
| **F-TR-5** | **LOW** | **AC10 cost is an estimate, not a measurement, and the test only proves the estimate stays under cap — not that the real per-callsite cost will.** `estimate_credits` uses fixed 2026 DeepSeek list prices (`dispatch.py` lines 63–73); `test_estimate_credits_demo_scale_under_ac10_cap` asserts a 30k/20k-token run < 30 credits, which is arithmetic on the constants, not evidence the live run bills ≤30¢. The code honestly flags AC-W1-13 for real `billing_service` cost. The collector reads `total_cost_credits` from the orchestrator rollup (`orchestrator.py` line 217), so the plumbing is correct — only the *price source* is provisional. | **ACCEPT** for Wave-0; the estimate-vs-real swap is explicitly pinned to AC-W1-13. AC10 evidence is "provable but with provisional pricing" — acceptable for an anchor, document it as such. |

---

### Evidence-sufficiency verdict on the 10× demo collector

- **AC8 (cohort p95 ≤120s):** **PROVABLE.** Wall-clock is measured tightly around step 2 (the `/run` orchestration only), cohort p95 via `statistics.quantiles(n=20)[18]` with a `max()` fallback for n<5, written to `summary.json` with threshold + pass flag. Semantics are correct (cohort, not per-run). ✓
- **AC9 (per-run artifact shape):** **NOT PROVABLE as wired** — see F-TR-1. The content-plan count will systematically miss on real writer output. Brief-word and matrix-row parsing are loose (F-TR-3) but bias toward pass. **This is the blocking fix.**
- **AC10 (per-run cost ≤30¢):** **PROVABLE with provisional pricing** (F-TR-5). The cost flows correctly from per-leaf estimate → orchestrator rollup → `result.total_cost_credits` → collector; only the price table is an estimate pending AC-W1-13.
- **Honesty of the ScriptedCoordinator caveat:** **GOOD.** The deterministic stand-in (no LLM tool-call decomposition) is disclosed in three docstrings and pinned to AC-W1-16. The anchor measures real per-specialist LLM latency/cost but a *fixed* plan — this is stated, not oversold.

**Bottom line:** The tooling can produce audit-grade evidence for AC8 and AC10 today. AC9 evidence is currently a false-negative trap (F-TR-1) — fix the content-plan parser idiom (or pin a realistic fixture) before the founder 10× run, or the anchor will read FAIL on correct briefs.
