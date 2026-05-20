# Section 03 — Test Adequacy

> Synthesized by the consolidator after the Test Results Analyzer agent
> completed its investigation (152 passed in the agents+llm_gateway slice,
> 440 total in the unit suite) but did not flush a section file. The agent's
> intermediate findings + the consolidator's spot-checks against the new
> test surface inform this report.

## Verdict

**PASS-WITH-FIXES** — the new test surface is honestly sized for the
demo-flow contracts it covers, but two coverage-theater risks land as
explicit Wave-1 AC pins rather than in-loop fixes.

## Per-suite verdicts

| Suite | Tests added in 00.5b | Status | Notes |
|---|---|---|---|
| `tests/agents/` | 11 (role_prompt_loader, delegate_tool, market_brief_demo_flow, cancel_cascade) | PASS | 9-section parsing + DAG-depth + SSE-order + cost-rollup + 3-artifact AC9 ledger all green |
| `tests/llm_gateway/` (chat_stream) | 8 (3 providers × 2-3 tests) | PASS | SSE + NDJSON parsing + OAuth refresh + malformed-chunk tolerance |
| `tests/llm_gateway/test_pydantic_ai_model_adapter.py` | 12 (adapter + fixture + AC9 invariants) | PASS | Fail-loud T3 invariants exercised (RuntimeError / KeyError / IndexError) |
| `tests/llm_gateway/test_budget_cap.py` | 7 (F-P5-2 closure) | PASS | `test_record_llm_cost_raises_budget_exceeded_above_50_credits` lands as named |
| `tests/integration/test_main_app_routes.py` | 17 (+ 4 from 00.5b mount-smoke extension) | PASS | 13 routes + aggregate + /health probe; full mount-smoke coverage |
| Aggregate suite | 440 PASS, 23 deselected | PASS | clean ruff + format; no flake markers |

## Findings

### HIGH

_None._ The fail-loud invariants on `pydantic_ai_test_model` (T3 founder
decision) are exercised; AC9 artifact-shape invariants are gated by
single-source-of-truth ledger functions (`writer_brief_word_count` etc.);
F-P5-2 canonical test name lands per audit-named contract.

### MEDIUM

- **F-TR-M1** — `tests/agents/test_market_brief_demo_flow.py` is in the
  default unit suite (`not integration` filter) but instantiates
  `InProcessSSEPublisher` with `asyncio.Queue` + drain-replay semantics.
  The boundary between «unit» (no I/O) and «integration» (real subsystems)
  is blurred here. Suggest re-marking as `@pytest.mark.asyncio` only and
  keeping it unit-scoped — the publisher is in-process so no I/O escape —
  but add a code-comment justification. Alternative: split the SSE-order
  test into a separate `tests/runtime/` suite with explicit unit marker.
- **F-TR-M2** — `tests/agents/test_cancel_cascade.py` uses an in-memory
  `_StubSession` shim with a queued `_StubResult` ledger. The BFS walker
  logic is exercised but the «atomic UPDATE» SQL semantic isn't tested
  against real PG. F-P5-3 SLIP-candidate (testcontainers migration) covers
  the gap, but until that lands the test is logic-only smoke. Document
  the deferral in the test file docstring (already present — verified).

### LOW

- **F-TR-L1** — `tests/integration/test_main_app_routes.py` lives in
  `tests/integration/` directory but uses static `app.routes`
  introspection — no HTTP, no DB, no I/O. Runs in the default unit
  filter regardless. Directory placement is a minor convention drift
  vs. F-P5-5 docs (mount-smoke pattern). Either relocate to
  `tests/_shared/` or update the convention doc to bless integration-dir
  for static smoke.
- **F-TR-L2** — F-P5-4 GigaChat OAuth `_ensure_token` token-refresh-after-
  expiry test (test_token_refresh_after_expiry_uses_new_credentials) is a
  SLIP-candidate per Topic 2 cut-list — verified NOT shipped in Commit 7.
  This is correct per founder-resolved cut-list (only ships «if headroom
  exists»). Defer to Phase 00.6 or 00.5c.
- **F-TR-L3** — `_shared/db` + `_shared/middleware` per-module ≥85%
  gates deferred to Commit 5/6 follow-up. Integration test
  `test_e2e_auth_flow.py::override_get_db` already exercises
  `tenant_context.py` under `oriion_app` role (Phase 00.5a canary);
  unit-test surface for `set_tenant_context` + `get_tenant_db_session`
  would close the deferred gate. Pin as Wave-1 AC.

## Coverage-theater spot-checks

The consolidator manually verified the «would this test fail if I broke
the production code» smell test for the most claim-heavy assertions:

1. **`test_demo_flow_emits_expected_sse_order`** — if you reorder the
   publisher.publish calls inside `_drive_three_parallel_delegations`,
   the parametrised expected-list assertion fails. ✅ Real ordering test.
2. **`test_record_llm_cost_raises_budget_exceeded_above_50_credits`** —
   the test pushes accumulated to 49 then asserts the next 5.0-credit
   call trips. Drop the cap to 60 in `budget_guard.DEFAULT_TASK_CAP_TCREDITS`
   and the test would still PASS (because the 11th call accumulates to
   53.9 + 5.0 = 58.9). ⚠️ Mild theater: the test asserts the cap value
   indirectly. Not a blocker — the cap is enumerated literally in the
   function default arg.
3. **`test_canned_brief_word_count_meets_ac9`** — if the canned brief
   loses sections, the word count drops below 1500 and the AC9 test
   fails. ✅ Real shape test.
4. **`test_fake_model_unknown_key_raises`** — if you change the KeyError
   to silent-default-return in `FakeLLMGatewayModel.request`, the
   `with pytest.raises(KeyError)` block fails. ✅ Real fail-loud test.

## Defer to Wave 1+ (explicit AC pin)

- AC14: real Pydantic-AI Agent.run() tool-call path exercise — drives
  `_messages_to_openai_shape` ToolCallPart branch. Test extension:
  add canned ModelResponses with `parts=[ToolCallPart(...)]` in
  `market_brief_demo.py`, exercise Coordinator → tool-call →
  delegate_task path through real Agent.run(). Currently the orchestrator
  is driven directly with canned DelegateResults — honest scope per the
  test file's docstring «Scope clarification (audit anchor)».
- F-P5-3: testcontainers PG migration for `test_byok_flow_full` +
  `test_cost_ledger_sum_match` + `test_cancel_cascade` (move from
  in-memory stubs to real DB).
- F-P5-4 GigaChat OAuth refresh-after-expiry test.
- `_shared/db` + `_shared/middleware` per-module ≥85% gates (unit-test
  additions for rls.py + tenant_context.py).
- `agents`/`tasks`/`runtime` per-module ≥85% gates (add to CI loop
  alongside their unit-test surface coverage in Phase 00.6).

## Recommendation

Merge as-is. The 440 unit-test green + 8 chat_stream + 12 adapter + 7
budget-cap + 17 mount-smoke surface is honest for the demo-flow contracts
Phase 00.5b ships. Pin the 5 Wave-1 deferrals as explicit AC anchors so
Phase 01.1 retro picks them up rather than rediscovering them.
