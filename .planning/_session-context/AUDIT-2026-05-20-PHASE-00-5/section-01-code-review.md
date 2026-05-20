# Section 01 — Code Review

**Auditor:** Code Reviewer (canonical, per PR #30 / PR #32 handoff)
**Scope:** Phase 00.5b — 6 atomic commits on `claude/phase-00-5b-runtime` off `origin/main` (`0360955`)
**Worktree:** `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\phase-00-5b-runtime`

## Verdict
**PASS-WITH-FIXES**

Code quality is consistently high — well-layered DDD bounded contexts, faithful mirroring of the `iam` canonical patterns (exception envelope, deps factories, async session), strong docstrings, no files near the 500-line ceiling. Found two MEDIUM bugs in the orchestrator + one MEDIUM cross-cutting concern (handler 503-shape leak), plus a handful of LOW items. None are blockers for Phase 00.5b shippability — orchestrator token-split is cosmetic for Wave 0 since the ledger is canned-fixture-driven, and the SSE subscriber path is exercised end-to-end in `test_market_brief_demo_flow.py`.

## Per-commit verdicts

- **`7c00b43` Commit 2 (main router wiring + lifespan + deps.py):** PASS-WITH-FIXES — exception handlers duplicate ~25 lines of envelope-building across 5 classes (F-CR-L2); `deps.py` raises raw `HTTPException` instead of an `LLMGatewayException` subclass (F-CR-M3 — pattern drift from `iam.IamError`).
- **`e0aaba3` Commit 3 (per-module CI gate + convention doc):** PASS — billing gate is well-scoped; defer rationale for agents/tasks/runtime gates is explicit and correct (modules don't exist yet at that revision). No code changes to audit beyond yaml + markdown.
- **`8cbc7f7` Commit 4 (Pydantic-AI Model adapter + canned fixture):** PASS-WITH-FIXES — `LLMGatewayModel` is clean and well-documented, but `_normalize_finish_reason` (F-CR-L1) silently passes unknown reasons through despite the docstring claiming the Pydantic-AI vocabulary is `{'stop','length','content_filter','tool_call','error'}` (no normalization actually happens for non-'stop' values, contradicting the helper name).
- **`3da3bac` Commit 5 (agents bounded context + auto-spawn):** PASS-WITH-FIXES — overall solid. `auth_service.register()` performs the GUC SQL inline (3x `SELECT set_config(..., true)`) instead of delegating to the existing `_shared/db/rls.py` helpers (F-CR-M2 — duplicated GUC plumbing that already has a canonical location). `agents/routers/instances.py` reads via plain `get_db` not `get_tenant_db_session` and relies on docstring promise (F-CR-L4).
- **`fbf23d8` Commit 6 (tasks + runtime + budget):** PASS-WITH-FIXES — orchestrator has two correctness bugs: (a) `tokens_used // 2` integer-split for input/output tokens loses 1 token on odd values + misrepresents reality (F-CR-M1); (b) `refund_unused()` return value is discarded (F-CR-L3 — refund computed but never persisted, future Wave-1 ledger will silently lose data unless the call site changes).
- **`6cd8808` Commit 7 (tests + demo script):** PASS — out of code-reviewer primary scope (test adequacy = Test Results Analyzer), but spot-checked: provider-mock convention is consistent with existing `test_provider_*_mock.py`, `demo_market_brief.py` follows good script hygiene (exit codes, argparse, no globals).

## Findings

### HIGH

_(none)_

### MEDIUM

- **F-CR-M1: Orchestrator integer-split corrupts token accounting**
  - File: `backend/src/runtime/orchestrator.py:165-166`
  - ```python
    task.total_input_tokens = sum(r.tokens_used // 2 for r in ctx.leaf_outputs)  # rough split
    task.total_output_tokens = sum(r.tokens_used // 2 for r in ctx.leaf_outputs)
    ```
  - **Why it matters:** `DelegateResult.tokens_used` is the *combined* count from the leaf. Integer-halving (a) drops 1 token per odd-valued leaf (a 21-token leaf becomes 10+10=20 stored), (b) misattributes the real split since real input/output ratios are nowhere near 50/50 in practice (typically 80/20 for completion-style flows). For Phase 00.5b this is masked by canned fixtures; production billing rollup (ADR-024 + AC6) will be wrong once real providers report.
  - **Suggested fix:** Extend `DelegateResult` with `tokens_input: int` and `tokens_output: int` (the underlying `LLMResponse` already has both). Sum them directly. If you want to keep `tokens_used` as a backward-compat aggregate, derive it from the pair. Pin as Phase 01.1 if you'd rather not touch the schema in 00.5b, but at minimum drop the "rough split" comment from a `// 2` bug into a `# TODO(AC14): real input/output split` so reviewers know it's intentional debt.

- **F-CR-M2: `auth_service.register()` duplicates GUC plumbing already in `_shared/db/rls.py`**
  - File: `backend/src/iam/services/auth_service.py:180-191`
  - The 3x `SELECT set_config('app.current_*_id', :val, true)` block sets the tenant context inline. `backend/src/_shared/db/rls.py` already exposes a helper that does exactly this (per `Grep` it has its own `finally:` block to reset GUCs).
  - **Why it matters:** Two future risks. (1) When the canonical helper gains an extra GUC (e.g. `app.current_role_id` for ADR-016 role-aware RLS) or changes the `true` vs `false` (local vs session) semantics, this inline copy will silently drift. (2) Reviewers reading `auth_service.register()` see SQL where business logic should live — that's a layering smell that the rest of the file otherwise avoids.
  - **Suggested fix:** Replace the three `text(...)` calls with `await rls.set_tenant_context(session=self._session, user_id=user.id, workspace_id=provision.workspace_id, cell_id=provision.cell_id)` (or whatever the helper signature is). Single call site; one place to maintain.

- **F-CR-M3: `llm_gateway/deps.py` raises raw `HTTPException` — pattern drift from `iam` envelope**
  - File: `backend/src/llm_gateway/deps.py:36-55` (`_require_state`)
  - Every other domain raises typed subclasses of `IamError` / `MultitenancyError` / `LLMGatewayException` / `TasksError` / `AgentsError`, and `main.py` has a registered handler per base. The 503 thrown here bypasses the `LLMGatewayException` handler and produces a plain FastAPI `{"detail": "..."}` JSON body instead of the RFC-7807 `problem+json` envelope every other 5xx in this app uses.
  - **Why it matters:** The frontend (Phase 00.7+) will see a different error shape for "lifespan didn't run" vs every other LLM-gateway error. Test fixtures asserting envelope shape (per F-P5-5 router convention) will skip this path.
  - **Suggested fix:** Either add an `LLMGatewayStartupError(LLMGatewayException)` with `code = "llm_gateway.startup_incomplete"` mapped to 503 in `_LLM_GATEWAY_STATUS` (preferred), or extend the existing `llm_gateway.kms_error` semantics. Keep `HTTPException` only for transport-layer fail-loud (e.g. 401 from middleware before any domain handler can fire).

### LOW

- **F-CR-L1: `_normalize_finish_reason` is misnamed — it does not normalize**
  - File: `backend/src/llm_gateway/pydantic_ai_model.py:164-174`
  - Docstring promises coercion into `{'stop','length','content_filter','tool_call','error'}`; implementation only special-cases `None`/`'stop'` and otherwise returns the raw provider value unchanged. So `'tool_calls'` (DeepSeek OpenAI-shape) and `'ALTERNATIVE_FINISH_LIMIT'` (Yandex) both pass through.
  - **Suggested fix:** Either implement the mapping (DeepSeek `tool_calls` → `tool_call`, Yandex `ALTERNATIVE_FINISH_LIMIT` → `length`, GigaChat-specific → tabular dict) OR rename to `_passthrough_finish_reason` and rewrite the docstring to say "Wave 0 passthrough; mapping table lands Wave 1+". Current state misleads readers.

- **F-CR-L2: `main.py` exception handlers repeat the same 8-line envelope across 5 classes**
  - File: `backend/src/main.py:228-327`
  - The `IamError`, `TasksError`, `AgentsError`, `MultitenancyError`, `MCPError` handlers are byte-for-byte identical except for the type they catch + the optional Retry-After branch (only IAM and MCP need it).
  - **Suggested fix:** Extract `_problem_response(request, exc, *, retry_after: int | None = None) -> JSONResponse` once, then each handler is 2-3 lines. ~80 LoC saved + future "every domain error gets `correlation_id` added to the envelope" is a one-line change instead of 5. Not a bug, just maintenance debt.

- **F-CR-L3: `refund_unused()` return value silently discarded in orchestrator**
  - File: `backend/src/runtime/orchestrator.py:167`
  - `refund_unused(ctx.accumulated_cost, reserved)` is called for its side effect but it has none — it's a pure function returning the unused amount. Wave-0 docstring in `budget_guard.py:5-7` says "Reservation + refund semantics are accounting metadata rather than a separate ledger row in Wave 0", which is fine, but the call site looks like a bug to a future reader.
  - **Suggested fix:** Either capture as `unused = refund_unused(...)` and stamp it onto the task row (extend the model with `budget_refunded` Numeric column, deferred Wave 1+), or wrap in a `_ = refund_unused(...)` with a `# placeholder until ledger lands` comment. As-is the function call is dead code that the reader can't tell is intentional.

- **F-CR-L4: `agents/routers/instances.py` uses `get_db` not `get_tenant_db_session`**
  - File: `backend/src/agents/routers/instances.py:21,29`
  - The docstring (lines 23-29) acknowledges the gap: "RLS-protected via app.current_cell_id GUC — caller must run under `get_tenant_db_session` (Phase 00.5a middleware) for production. Wave 0 handler reads from get_db directly". This is documented debt rather than a bug, but it's the only `agents/tasks` cell-scoped router that doesn't go through tenant_context — `tasks/routers/tasks.py` has the same shape but the docstring there says "actual RLS filtering happens at the DB layer via app.current_cell_id GUC" which presumes a session that already has it set.
  - **Suggested fix:** Consistency. Either both routers use `get_tenant_db_session` (preferred — closes the documented gap), or both use `get_db` + an explicit `cell_id` filter (current `instances.py` shape) and `tasks.py` adds the same filter on `Task.cell_id`. Pick one; document the choice once.

- **F-CR-L5: `productivity_core_v1.py` uses `analyst` slug + `analyzer` role_category inconsistency**
  - File: `backend/src/agents/seed_data/productivity_core_v1.py:55-58`
  - The seed maps slug `analyst` (UI-facing) to `role_category='analyzer'` (schema enum). The mismatch is documented in the module docstring (lines 11-13) and inline comment, so this is intentional, but it's a footgun for anyone writing a CHECK constraint or filter against `role_category` — they'll write `WHERE role_category = 'analyst'` and get zero rows.
  - **Suggested fix:** Either rename the schema enum value to `analyst` (one migration), or add a sentence to `agents/models.py:AgentArchetype` class docstring pinning the mapping table. Not a bug for Phase 00.5b, just a tripwire for the next person.

- **F-CR-L6: `_LLM_GATEWAY_STATUS`/`_TITLES` belong on the exception classes, not `main.py`**
  - File: `backend/src/main.py:334-372`
  - The `LLMGatewayException` subclasses are defined in `llm_gateway/exceptions.py` without `status_code`/`title` class attrs (unlike `IamError`/`TasksError`/`AgentsError`). The mapping is reconstructed in `main.py` instead. This is the inverse of every other domain.
  - **Suggested fix:** Add `status_code` + `title` to each `LLMGatewayException` subclass in `llm_gateway/exceptions.py`, then `llm_gateway_error_handler` collapses to the same 3-line shape as `tasks_error_handler` (closes F-CR-L2 partially too). Pre-existing inconsistency, not introduced by 00.5b — but the new code in this commit (`llm_gateway/deps.py` + main wiring) is the right moment to fix it.

## Defer to Wave 1+ (explicit AC pin)

- **Pydantic-AI `request_stream()` implementation on `LLMGatewayModel`** — AC14 (Phase 01.1 hardening), per `pydantic_ai_model.py:103` "inherited default raises until Wave 1 SSE-on-runtime lands". Correctly scoped out; not a Phase 00.5b finding.
- **Tool-call (ToolCallPart) shape in `_messages_to_openai_shape`** — AC14, per `pydantic_ai_model.py:147-148` "tool-call wiring lands with Commit 5 when `delegate_task` ships". The delegate_task path goes through `OrchestratorContext.runner_with_orchestration` and the agent's tool call is dispatched in-Pydantic-AI; the missing piece is when a non-canned LLM responds with ToolCallPart from the wire. Phase 01.1 hardening pin is correct.
- **Real `task_step` row-per-LLM-call persistence** — AC14 per `orchestrator.py:13-15` "Full task_step persistence per LLM token + SSE token streaming lands in Wave 1+". Orchestrator only writes parent `Task`, not per-step `TaskStep` rows. Fine for Wave 0; pin holds.
- **Redis-backed `SSEPublisher`** — explicit per `sse_publisher.py:5-6` "Wave 1 swaps the backing store to Redis pub/sub without changing the SSEPublisher Protocol". The in-process queue won't survive multi-worker uvicorn. Pin holds for Wave 1+ multi-worker phase.
- **CreditTransaction(kind='reservation') ledger row at task start** — per `budget_guard.py:39-42`. Wave-1 billing ledger work. Pin holds.
- **Cell ownership / role checks on cell-scoped routers** (e.g. should `POST /cells/{cell_id}/teams` 403 when caller isn't a cell member?) — out of code-review scope, defer to Security Engineer audit. Not pinning here.

## Recommendation

Phase 00.5b is shippable. The code reads like one mind wrote it — same docstring tone, same DI seam, same exception envelope as `iam`. Bounded contexts respect ADR-024 (agents owns "what to delegate", tasks/runtime owns "how it executes"). Idempotent seeds, fail-loud DI factories, defensive `getattr` access to Pydantic-AI's version-tolerant `output`/`data` field — these are the marks of a Wave 0 that has thought about Wave 1 maintenance cost.

The two MEDIUM findings (F-CR-M1 orchestrator token-split, F-CR-M2 GUC plumbing duplication) and the MEDIUM cross-cutting (F-CR-M3 deps.py raw HTTPException) are worth landing as a follow-up commit before Phase 00.6 staging deployment — they're each <10 LoC and would close real maintainability/correctness gaps without changing public surfaces. The LOW findings are sweep-time housekeeping; none gate the shipping decision. Recommend the founder land the three MEDIUMs in a `chore(phase-00-5b): review fixes` commit on the same branch before merging to `main`, then file the LOWs as a Wave 1 hygiene pass.
