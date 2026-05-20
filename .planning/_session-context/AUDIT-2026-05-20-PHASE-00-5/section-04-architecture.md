# Phase 00.5b — Section 04 · Backend Architecture Audit

**Auditor:** Backend Architect
**Date:** 2026-05-20
**Worktree:** `.planning/.claude/worktrees/phase-00-5b-runtime`
**Branch:** `claude/phase-00-5b-runtime`
**Commits in scope:** `7c00b43..6cd8808` (6 atomic commits off `origin/main`)
**Anchors:** ADR-003, ADR-016, ADR-017 (rev 2026-05-15), ADR-022, ADR-024 (§3 pending Commit 8), ADR-029

---

## Verdict

**APPROVE WITH FOLLOW-UPS — architectural shape is sound; layering is clean; the DAG holds.**

Phase 00.5b lands the three new bounded contexts (`agents/`, `tasks/`, `runtime/`) with the same models / schemas / exceptions / events / services / routers layering as the established `iam/`, `multitenancy/`, `llm_gateway/` triad. The Pydantic-AI Model adapter is a tight, single-purpose bridge; the lifespan provider DI seam is correctly stashed on `app.state`; the SSE drain-replay pattern is adequate for the demo-flow CI test and has an explicit Wave-1 Redis swap path. The cross-context import graph is a strict DAG with **one** new edge (`iam → agents`) that needs the ADR-024 §3 amendment to legitimize — exactly the surface Commit 8 will codify.

Findings below are mostly MEDIUM/LOW papercuts. One HIGH (F-ARC-H1) flags the `iam → agents` service-call hop as the load-bearing edge for the ADR-024 §3 amendment — it is architecturally well-contained but **not** yet sanctioned in ADR text.

---

## Findings

### F-ARC-H1 · HIGH — `iam → agents.services` service-call edge needs ADR-024 §3 amendment to land in Commit 8

**Files:**
- `backend/src/iam/deps.py:17` — `from src.agents.services.team_provisioning_service import TeamProvisioningService`
- `backend/src/iam/services/auth_service.py:29` — same import + `__init__` parameter (line 97) + call site (lines 179–196)

**Problem:**
`AuthService.register()` now reaches into the `agents` bounded context to call `TeamProvisioningService.provision_team(...)`. This is a **synchronous, in-TX, cross-context service-method invocation**, not an event emission or a model-only import. Today the ADR-024 list of «Sanctioned cross-context model imports» does not cover service-method calls between IAM and agents (it only covers FK model references like `multitenancy.cells.id`). The amendment commit (Commit 8) **must** explicitly list this hop or the next compliance auditor will mark it as drift.

**Why this is the right shape architecturally** (independent of the ADR text):

1. The «auto-spawn productivity-core team on first cell» AC1 is a **business invariant tied to the registration TX** — if the team fails to provision, the registration must roll back. Async event-based provisioning would break the atomicity that the same-TX comment at `auth_service.py:175–176` correctly preserves.
2. The dependency direction is **iam → agents** (not the reverse), so the import graph stays a DAG.
3. The optional `team_provisioning_service: TeamProvisioningService | None = None` keyword on `AuthService.__init__` (line 97) gives unit tests a clean opt-out — but see F-ARC-M3 below for the invariant concern.

**Recommendation for Commit 8:**
Add a §3.2 «Sanctioned cross-context service calls» list to ADR-024 containing exactly:
- `iam.services.auth_service.AuthService.register` → `agents.services.team_provisioning_service.TeamProvisioningService.provision_team` (synchronous, same-TX, AC1 anchor)

No other cross-context service calls exist today (verified — see import graph table below).

---

### F-ARC-H2 · HIGH — Lifespan does NOT construct `sse_publisher` on `app.state`; production worker isolation will surprise

**Files:**
- `backend/src/main.py:116–169` (lifespan) — stashes `settings, kms_provider, llm_providers, llm_circuits, llm_router` but **not** `sse_publisher`
- `backend/src/runtime/sse_publisher.py:79–88` — module-level `_singleton` accessed via `get_sse_publisher()`
- `backend/src/tasks/routers/stream.py:37` — `publisher = get_sse_publisher()` (module singleton, not request.app.state)

**Problem:**
The other expensive process-wide resources (LLMRouter, providers, KMS) follow the lifespan-on-app.state DI seam documented in `llm_gateway/deps.py::_require_state`. The `InProcessSSEPublisher` deliberately uses a module-level singleton instead. That works under uvicorn single-worker dev, but:

1. Under multi-worker uvicorn / gunicorn (Wave 0 deploy posture per ADR-009 deployment notes), each worker has its own `_singleton` — a task started in worker A and streamed from worker B will simply hang on subscribe with no events. The orchestrator code path in tests masks this because `pytest-asyncio` runs everything in one process.
2. `reset_sse_publisher_for_tests()` (line 91) is the only escape hatch. Test fixtures that swap publishers between cases must remember to call it — easy to forget and the failure mode is silent (events go to the previous instance's queues).

**The docstring already calls this out** (`sse_publisher.py:5-6` — «Wave 1 swaps the backing store to Redis pub/sub without changing the SSEPublisher Protocol or call sites»). That deferral is sound, but the multi-worker caveat should be on `STATUS.md`'s known-limitations list, and the Redis swap should be **the same lifespan-built singleton pattern** as the LLMRouter, not a module global.

**Recommendation (defer to Wave 1, document now):**
- Wave 0: add a `STATUS.md` known-limitation entry: «SSE streaming is single-worker only; deploy uvicorn with `--workers 1` until Wave 1 Redis swap.»
- Wave 1: build `RedisSSEPublisher` in lifespan, stash on `app.state.sse_publisher`, update `tasks/routers/stream.py` to read from `request.app.state.sse_publisher` (mirrors `llm_gateway/deps.py::_require_state`).

---

### F-ARC-M1 · MEDIUM — `LLMGatewayModel` claims streaming sibling is deferred but does not override the base class default loudly

**File:** `backend/src/llm_gateway/pydantic_ai_model.py:102–103`

The `request()` method docstring says «Streaming sibling lives in `request_stream` (inherited default raises until Wave 1 SSE-on-runtime lands)». Pydantic-AI's `Model.request_stream` does indeed raise `NotImplementedError` by default — but if a future Pydantic-AI minor changes that default (e.g. to a "no-op empty iterator"), the silent regression would emit zero tokens to the SSE stream without an obvious failure. The Wave 1 commitment should be locked by an explicit override that raises with a clear message pointing at the Wave-1 ticket — same fail-loud pattern the `delegate_task` no-runner branch uses (`delegate.py:132–137`).

**Patch (one-line):**
```python
async def request_stream(self, *args, **kwargs):
    raise NotImplementedError(
        "LLMGatewayModel streaming is deferred to Wave 1 (SSE-on-runtime). "
        "Use request() for one-shot completions; see ADR-003."
    )
```

---

### F-ARC-M2 · MEDIUM — `orchestrator.execute_agent_task` never emits `task.failed` on exception; CoordinatorOutput path is happy-only

**File:** `backend/src/runtime/orchestrator.py:155–191`

The state-machine docstring at the top of `runtime/orchestrator.py:1–16` says transitions are «queued → running → succeeded/failed/cancelled». The orchestrator currently only writes the `succeeded` transition (line 162). If `coordinator_agent.run(...)` raises (e.g. `BudgetExceeded` from `check_budget`, or a `LLMProviderUnavailable` bubbling out of the LLMRouter), the function lets the exception propagate without:

1. Setting `task.status = "failed"`
2. Emitting `task.failed` SSE event
3. Calling `refund_unused(...)` to release the budget reservation
4. Calling `tasks_events.emit_task_failed(...)`

The `InProcessSSEPublisher` doesn't see `task.failed` either, so subscribers on `/stream` will hang on the queue forever (the publisher only marks tasks done on `task.{completed,cancelled,failed}` — see `sse_publisher.py:52`).

**Recommendation (Commit 7 or follow-up before Commit 8):**
Wrap the body in `try/except`:
```python
try:
    run_result = await coordinator_agent.run(user_prompt, deps=deps)
    # ... happy path ...
except Exception as exc:
    if task is not None:
        task.status = "failed"
        task.completed_at = datetime.now(UTC)
        task.total_cost_credits = ctx.accumulated_cost
    await sse_publisher.publish(TaskStreamEvent(
        event_type="task.failed",
        task_id=task_id,
        payload={"error_code": getattr(exc, "code", "runtime.unknown"),
                 "error_message": str(exc)},
    ))
    refund_unused(ctx.accumulated_cost, reserved)
    await tasks_events.emit_task_failed(task_id=task_id, error_code=...)
    raise
```

Pin this to phase-spec AC10 (per-task cap) + AC12 (cancel cascade).

---

### F-ARC-M3 · MEDIUM — `team_provisioning_service=None` default on `AuthService.__init__` is a subtle prod-invariant break

**Files:**
- `backend/src/iam/services/auth_service.py:97` — `team_provisioning_service: TeamProvisioningService | None = None`
- `backend/src/iam/services/auth_service.py:179` — `if self._team_provisioning_service is not None:`

**Problem:**
The optional kwarg lets unit tests skip the cross-context call, which is fine in isolation. But the **only** thing standing between «unit-test bypass» and «prod silently doesn't provision the team» is whether `iam/deps.py` remembers to pass it. The architectural risk: a future refactor of `iam/deps.py::get_auth_service` (e.g. someone simplifying the constructor) could drop the kwarg and AC1 would silently regress — no AssertionError, no NotImplementedError, just a missing team.

**Lower-risk pattern (recommendation):**
Make the kwarg required (`team_provisioning_service: TeamProvisioningService | NullTeamProvisioningService`) and provide an explicit `NullTeamProvisioningService` for unit tests:

```python
class NullTeamProvisioningService:
    """Test-only no-op. Production code path uses TeamProvisioningService."""
    async def provision_team(self, **_kw): return []
```

That way the «skip team provisioning» intent is explicit at the call site rather than implicit in a None default.

This is a Wave-1 polish — not blocking Commit 8.

---

### F-ARC-M4 · MEDIUM — 3-GUC bootstrap inline in `auth_service.register()` should be extracted as a helper

**File:** `backend/src/iam/services/auth_service.py:179–191`

The three `SELECT set_config('app.current_*_id', :v, true)` calls are inline. Architecturally this is the **right place** (vs. a SECURITY DEFINER function) for two reasons:

1. The GUCs are session-local (`true` is the `is_local` arg → auto-reset at TX end) — wrapping in a SECURITY DEFINER function adds zero security benefit for session GUCs.
2. Phase 00.5a's `provision_initial_workspace` already runs as a SECURITY DEFINER bootstrap function; layering a second one for «set tenant context» would invert the cleanest mental model (workspace bootstrap is a privileged operation; setting tenant GUCs is the calling code's responsibility).

**The actual papercut:** the same 3-GUC dance will appear in **every** future cross-context bootstrap that needs RLS-protected writes (e.g. when Phase 00.6 wires task creation with team context). Extract a tiny helper in `_shared/db/`:

```python
# src/_shared/db/tenant_context.py
async def set_tenant_context(
    session: AsyncSession, *, user_id: UUID, workspace_id: UUID, cell_id: UUID
) -> None:
    """Set the 3 RLS GUCs on the current session-local TX."""
    for name, value in [
        ("app.current_user_id", user_id),
        ("app.current_workspace_id", workspace_id),
        ("app.current_cell_id", cell_id),
    ]:
        await session.execute(
            text("SELECT set_config(:n, :v, true)"), {"n": name, "v": str(value)}
        )
```

Then `auth_service.register` becomes a one-liner. **Document architecturally that this is the Wave 0 pattern** (no SECURITY DEFINER funcs for tenant context) so future agents don't reinvent.

---

### F-ARC-M5 · MEDIUM — `delegate_task` raises `NotImplementedError` for the no-runner path; should be a domain exception

**File:** `backend/src/agents/tools/delegate.py:132–137`

The fail-loud pattern is correct in spirit. But Pydantic-AI tools that raise unhandled exceptions get wrapped as `tool_error` model responses by the framework — the user-facing error path becomes opaque. More importantly, `NotImplementedError` is a Python-builtin used by static analysis tools (mypy, pylint) to mark abstract methods; raising it from a concrete code path muddles that signal.

**Recommendation:**
Add `DelegateRunnerNotConfigured(AgentsError)` in `agents/exceptions.py` and raise that instead. The `AgentsError` exception handler in `main.py:270–285` then surfaces it as RFC-7807 JSON with `code=agents.delegate.runner_not_configured`.

This also lets Phase 00.6 retry-policy work catch the specific case without a `try/except NotImplementedError` (which is a code smell).

---

### F-ARC-L1 · LOW — `LLMGatewayModel.workspace_id` defaults to `UUID("00...")` placeholder

**File:** `backend/src/llm_gateway/pydantic_ai_model.py:81`

The docstring (line 64–65) acknowledges this is «a UUID placeholder is fine — the router currently ignores it» — but the LLMRouter's per-cell BYOK lookup **does** read workspace_id (`router_service.py` per Phase 00.5a). If an agent is constructed with `workspace_id=None`, the BYOK path silently falls back to the platform keys instead of the cell's BYOK keys — security-correct but billing-incorrect.

Either (a) make `workspace_id` a required positional arg or (b) emit a `_logger.warning` when the placeholder is used. Defer to Wave 1 when BYOK-on-agent lands; flag in STATUS.md known limitations.

---

### F-ARC-L2 · LOW — `tasks_router` and `task_stream_router` are siblings under `tasks/routers/` but `stream.py` reaches into `runtime/`

**Files:** `backend/src/tasks/routers/stream.py:19`, `backend/src/tasks/routers/tasks.py`

The `stream.py` router imports `from src.runtime.sse_publisher import get_sse_publisher`. Architecturally this is a `tasks → runtime` edge (DAG-OK), but it means the «public HTTP surface for tasks» depends on the «private runtime infrastructure». In stricter DDD this would live in `runtime/routers/stream.py` and be mounted under the `/cells/{cell_id}/tasks/{task_id}/stream` path from there — keeping `tasks/routers/` for the tasks-context contracts only.

This is a packaging nit — not worth a re-org now. Document in the audit log: when Wave 1 adds the Redis publisher, consider moving the stream router under `runtime/routers/` to mirror the bounded-context ownership.

---

### F-ARC-L3 · LOW — `cost_rollup_service` exists but orchestrator reimplements rollup inline

**Files:**
- `backend/src/tasks/services/cost_rollup_service.py:16` (imports `Task, TaskStep`)
- `backend/src/runtime/orchestrator.py:165–166` (inline `sum(...)` over `ctx.leaf_outputs`)

The orchestrator's «cost rollup + completion stamp» block computes `total_input_tokens` / `total_output_tokens` via a rough `tokens_used // 2` split (line 165–166) rather than calling into the dedicated `cost_rollup_service`. The split heuristic is fine for Wave 0 (the demo-flow test doesn't assert per-token splits), but it bypasses the service abstraction that exists specifically for this purpose. Move the rollup math into `cost_rollup_service.rollup_task_costs(...)` and have the orchestrator call it.

Defer to Wave 1 when real per-step token attribution lands.

---

## Cross-Context Import Graph

Every `from src.X import` where the importing module's bounded context ≠ X. Source context → target context, classification, line ref.

| Source ctx       | File                                          | Imports                                                                      | Classification                              | Sanctioned by              |
|------------------|-----------------------------------------------|------------------------------------------------------------------------------|---------------------------------------------|----------------------------|
| `agents`         | `coordinator.py:26`                           | `src.llm_gateway.pydantic_ai_model.LLMGatewayModel`                          | DI seam (agent factory takes Model)         | **DEFERRED ADR-024 §3 amendment (Commit 8)** |
| `agents`         | `researcher.py:15`                            | `src.llm_gateway.pydantic_ai_model.LLMGatewayModel`                          | DI seam                                     | **DEFERRED ADR-024 §3 amendment** |
| `agents`         | `writer.py:9`                                 | `src.llm_gateway.pydantic_ai_model.LLMGatewayModel`                          | DI seam                                     | **DEFERRED ADR-024 §3 amendment** |
| `agents`         | `analyst.py:17`                               | `src.llm_gateway.pydantic_ai_model.LLMGatewayModel`                          | DI seam                                     | **DEFERRED ADR-024 §3 amendment** |
| `agents`         | `routers/teams.py:19`                         | `src.iam.middleware.{AuthenticatedUser, get_current_user}`                   | Auth DI seam (middleware-as-shared-kernel)  | Sanctioned (existing pattern, matches multitenancy/routers) |
| `iam`            | `deps.py:17`                                  | `src.agents.services.team_provisioning_service.TeamProvisioningService`     | Service DI wire-up                          | **DEFERRED ADR-024 §3 amendment (load-bearing for F-ARC-H1)** |
| `iam`            | `services/auth_service.py:29`                 | `src.agents.services.team_provisioning_service.TeamProvisioningService`     | Service call (same-TX, AC1 anchor)          | **DEFERRED ADR-024 §3 amendment (load-bearing for F-ARC-H1)** |
| `iam`            | `services/auth_service.py:30`                 | `src.audit.services.audit_service.emit_audit_event`                          | Event emission (shared audit kernel)        | Sanctioned (existing pattern, Phase 00.2) |
| `iam`            | `services/auth_service.py:61`                 | `src.multitenancy.services.workspace_service.provision_initial_workspace`    | Service call (same-TX bootstrap, Phase 00.5a) | Sanctioned ADR-024 (existing) |
| `iam`            | `services/consent_service.py:17`              | `src.audit.services.audit_service.emit_audit_event`                          | Event emission (shared audit kernel)        | Sanctioned (existing) |
| `tasks`          | `routers/tasks.py:11`                         | `src.iam.middleware.{AuthenticatedUser, get_current_user}`                   | Auth DI seam                                | Sanctioned (middleware-as-shared-kernel) |
| `tasks`          | `routers/stream.py:18`                        | `src.iam.middleware.{AuthenticatedUser, get_current_user}`                   | Auth DI seam                                | Sanctioned |
| `tasks`          | `routers/stream.py:19`                        | `src.runtime.sse_publisher.get_sse_publisher`                                | Infrastructure import (publisher access)    | Sanctioned (runtime is infra for tasks; F-ARC-L2 nit) |
| `runtime`        | `orchestrator.py:29`                          | `src.agents.tools.delegate.{CoordinatorDepsLike, DelegateInput, DelegateResult}` | Type-only contract import                   | Sanctioned (orchestrator drives agents) |
| `runtime`        | `orchestrator.py:38`                          | `src.tasks` events                                                           | Event emission                              | Sanctioned (runtime owns task lifecycle events) |
| `runtime`        | `orchestrator.py:39`                          | `src.tasks.models.Task`                                                      | Cross-context model write (status updates)  | **DEFERRED ADR-024 §3 amendment** |
| `runtime`        | `budget_guard.py:13`                          | `src.tasks.exceptions.BudgetExceeded`                                        | Exception import (shared error vocabulary)  | Sanctioned |
| `multitenancy`   | `routers/{workspaces,cells}.py`               | `src.iam.middleware.*`                                                       | Auth DI seam                                | Sanctioned (existing) |
| `llm_gateway`    | `services/billing_service.py:26`              | `src.billing.models.CreditTransaction`                                       | Cross-context model write (cost rollup)     | Sanctioned ADR-024 (existing, Phase 00.5a) |

**Edges introduced in Phase 00.5b that need ADR-024 §3 amendment to land in Commit 8:**

1. `agents.{coordinator,researcher,writer,analyst} → llm_gateway.pydantic_ai_model.LLMGatewayModel` (×4 — DI seam, Wave 0 happy path)
2. `iam.{deps,services.auth_service} → agents.services.team_provisioning_service.TeamProvisioningService` (×2 — service call, AC1 anchor)
3. `runtime.orchestrator → tasks.models.Task` (×1 — cross-context model write, status flips)

**FK edges in models.py (already covered by ADR-024 §2):**

- `agents.AgentInstance.cell_id → multitenancy.cells.id` (FK, ON DELETE CASCADE)
- `tasks.Task.cell_id → multitenancy.cells.id` (FK)
- `tasks.Task.agent_instance_id → agents.agent_instances.id` (FK)
- `tasks.TaskStep.agent_archetype_id → agents.agent_archetypes.id` (FK)
- `tasks.Task.parent_task_id → tasks.tasks.id` (self-FK)

---

## DAG-ness Verdict

**The cross-context import graph is a strict DAG.** Verified by inspection of all edges above:

```
billing ←── llm_gateway
                ↑
                │ (Model adapter)
                │
audit ←── iam ──→ multitenancy ←── agents ──→ llm_gateway
          │       (workspace      (FK refs       (Model adapter)
          │        bootstrap)      cell_id)
          ↓
        agents (TeamProvisioningService — NEW Phase 00.5b)
          │
          ↑
        runtime ──→ tasks (models + events)
                     ↑
                     │ (Task model write)
                     │
                  tasks ──→ runtime (SSE publisher access via routers/stream.py)
```

**Wait — is `tasks ↔ runtime` a cycle?**

No. Looking again:
- `tasks/routers/stream.py:19` → `runtime.sse_publisher.get_sse_publisher` (one direction: `tasks → runtime`)
- `runtime/orchestrator.py:39` → `tasks.models.Task` (one direction: `runtime → tasks`)
- `runtime/budget_guard.py:13` → `tasks.exceptions.BudgetExceeded` (one direction: `runtime → tasks`)
- `runtime/orchestrator.py:38` → `tasks` events (one direction: `runtime → tasks`)

The `tasks/routers/stream.py → runtime` edge is at the **router layer**, which sits ABOVE the service+model layer where `runtime → tasks.{models,events,exceptions}` lives. There's no in-process import cycle (Python module-load works), and no logical cycle in the architecture (routers depend on services/infra; services/infra do not depend on routers). The dependency graph is partitioned by layer:

```
Layer 4 — routers       : tasks/routers/stream.py     ──→ runtime.sse_publisher
Layer 3 — services      : runtime/orchestrator.py     ──→ tasks.{models, events, exceptions}
Layer 3 — services      : runtime/budget_guard.py     ──→ tasks.exceptions
Layer 2 — models/events : (no cross-context imports in tasks/runtime)
```

**DAG confirmed. ADR-024 §3 amendment scope is correctly bounded.**

---

## Defer-to-Wave-1 (with AC pins)

| Item                                                                                  | AC pin                       | Rationale                                                                                              |
|---------------------------------------------------------------------------------------|------------------------------|--------------------------------------------------------------------------------------------------------|
| `LLMGatewayModel.request_stream` explicit override (F-ARC-M1)                         | F-P5-3 (streaming readiness) | Pydantic-AI default already raises; add explicit override when SSE-on-runtime lands.                   |
| `RedisSSEPublisher` swap + lifespan-built singleton (F-ARC-H2)                        | F-P5-4 (multi-worker SSE)    | Protocol already in place; switch backing store + read from `request.app.state`.                      |
| `cost_rollup_service.rollup_task_costs(...)` real per-step attribution (F-ARC-L3)     | F-P5-2 / AC10 (cost cap)     | Wave 0 rough split is sufficient for demo-flow assertions.                                             |
| `LLMGatewayModel.workspace_id` BYOK-aware enforcement (F-ARC-L1)                      | F-P5-5 (BYOK-on-agent)       | Router currently ignores; will read in Wave 1.                                                          |
| Move `tasks/routers/stream.py` into `runtime/routers/` (F-ARC-L2)                     | n/a (packaging)              | Cosmetic — defer until Redis swap forces a re-touch.                                                    |
| `NullTeamProvisioningService` for explicit test-bypass (F-ARC-M3)                     | n/a (polish)                 | Wave-1 polish; not blocking.                                                                            |
| `_shared.db.tenant_context.set_tenant_context(...)` helper (F-ARC-M4)                 | AC1 / AC12                   | Extract pattern as soon as a second call site appears (Phase 00.6 task-create with team context).      |

---

## Pinned Decisions for Commit 8 (ADR-024 §3 amendment)

The ADR-024 §3 «Sanctioned cross-context model imports» amendment **must** explicitly cover the following surfaces to legitimize Phase 00.5b:

### §3.1 — Sanctioned cross-context model + type imports (Wave 0)

1. `agents.{coordinator,researcher,writer,analyst}` imports `llm_gateway.pydantic_ai_model.LLMGatewayModel` — DI seam for Pydantic-AI agent construction. The Model class is the contract; no other `llm_gateway` types are exposed to `agents`.
2. `runtime.orchestrator` imports `tasks.models.Task` for status-flip writes (`queued → running → succeeded/failed/cancelled`). Wave 0 confined to status, started_at, completed_at, total_cost_credits, total_{input,output}_tokens columns.
3. `runtime.orchestrator` and `runtime.budget_guard` import `tasks.{events, exceptions}` for the task lifecycle event emission + shared exception vocabulary.
4. `runtime.orchestrator` imports `agents.tools.delegate.{CoordinatorDepsLike, DelegateInput, DelegateResult}` as type-only contracts — these are the wire-types for the agent ↔ orchestrator handshake.

### §3.2 — Sanctioned cross-context service calls (Wave 0)

1. `iam.services.auth_service.AuthService.register` → `agents.services.team_provisioning_service.TeamProvisioningService.provision_team` — synchronous, same-TX, AC1 anchor («auto-spawn productivity-core team on user's first cell»). Wired via `iam.deps.get_auth_service` factory; unit tests pass `team_provisioning_service=None` to skip.

### §3.3 — UNCHANGED — sanctioned existing edges from Phase 00.5a

- `iam.services.auth_service.AuthService.register` → `multitenancy.services.workspace_service.provision_initial_workspace` (workspace bootstrap)
- `llm_gateway.services.billing_service.record_llm_cost` → `billing.models.CreditTransaction` (cost rollup)
- `iam.services.{auth,consent}_service` → `audit.services.audit_service.emit_audit_event` (shared audit kernel)
- Auth middleware (`iam.middleware.{AuthenticatedUser, get_current_user}`) imported by all router layers as the auth DI seam.

---

## Recommendation

**APPROVE Phase 00.5b architecture for merge to main, conditional on Commit 8 landing the ADR-024 §3 amendment text described above.**

Of the 10 findings:
- **2 HIGH:** F-ARC-H1 (ADR amendment scope — addressable in Commit 8) and F-ARC-H2 (multi-worker SSE — Wave-1 deferral documented in `STATUS.md`)
- **5 MEDIUM:** all addressable as Wave-1 polish; F-ARC-M2 (task.failed emission) should land before Phase 00.6 task-orchestrator hardening
- **3 LOW:** packaging + nice-to-have refactors; defer to Wave 1

The Pydantic-AI Model adapter, the agent factories (`build_*_agent`), the seed_data idempotency, the lifespan provider DI, and the SSE drain-replay pattern all match phase-spec inline + ADR anchors. The cross-context import graph is a DAG and the new edges are well-bounded — the ADR-024 §3 amendment scope is small and precise.

One out-of-scope-but-worth-flagging architectural observation for the Compliance Auditor: the **only** load-bearing edge that needs ADR amendment is the `iam → agents` service-call hop. The other new edges (`agents → llm_gateway`, `runtime → tasks`) are pure dependency-direction extensions of the existing layer cake; the §3 amendment can list them as «infrastructure adapters» rather than «service-call exceptions». Whether to enumerate them individually or group them is a documentation choice, not an architectural one.
