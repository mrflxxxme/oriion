# ADR-034: Async Dramatiq dispatch + Redis-Streams SSE + AC8 reframe

- **Status:** Accepted (Phase 01.1 infra-PR, 2026-06-16)
- **Supersedes (partially):** the inline-synchronous dispatch shipped in Phase 00.6 PR-B (closes AC-W1-16a + AC-W1-1; ties AC-W1-23).

## Decision

`POST /api/v1/cells/{cell_id}/tasks/{task_id}/run` no longer runs the
researcher→analyst→writer orchestration inline on the request thread. It now:

1. guards `status == 'queued'`, stamps `tasks.dispatched_at`, commits, then
2. enqueues a **Dramatiq actor** (`dispatch_task_actor.send(task_id, user_id)`) and
3. returns **202 `{status: "dispatched"}` in <1s** — **no `result` in the body**.

The orchestration runs **out-of-process in a Dramatiq worker** (`dramatiq
src.runtime.queue.worker`, run `-p1 -t1`). The worker streams its SSE ledger through
a **Redis-Streams-backed publisher**, so the web tier's `GET …/stream` receives the
events across the process boundary and the **`task.completed` frame carries the
`CoordinatorOutput`** (the result moved from the HTTP body to SSE — a deliberate
contract change).

### AC8 reframe

Because dispatch is now async, **AC8's hard gate is redefined to dispatch latency**
(`cohort p95 ≤ 1s`), and the end-to-end **generation wall-clock (~163s on funded
DeepSeek) becomes a tracked SLI, not a gate**. This is sanctioned by AC-W1-23 ("the
real fix is streaming + the Dramatiq actor so latency is decoupled from generation
length"): the founder-perceived latency drops to <1s + live SSE progress, while the
absolute generation time is a model-speed property tracked for trend, not a pass/fail.
`scripts/demo_market_brief.py` measures both; AC9/AC10 are read from the
`task.completed` payload. See note appended to [ADR-025](./ADR-025-acceptance-gate-format.md).

## Why these mechanisms

- **Dramatiq** (already a dependency) over inline: returns 202 immediately, decouples
  the request thread, gives each dispatch its own TX boundary, and is the AC-W1-16a /
  AC-W1-23 sanctioned path.
- **Redis Streams**, not pub/sub: once the producer (worker) and the `/stream`
  subscriber (web) live in different processes — and once SSE is Redis-backed the web
  tier can scale `gunicorn -w >1` — plain pub/sub would drop events for late
  subscribers, breaking the **drain-replay** contract the demo + frontend rely on. A
  Stream persists the per-task log, so a late subscriber `XREAD`s from id `0` (full
  replay) then blocks for new entries; the terminal event is the subscription sentinel;
  a per-task TTL self-cleans.
- **StubBroker under `DRAMATIQ_TESTING`**: the broker is chosen at import (before the
  actor module binds), so CI stays deterministic with no Redis/worker/network.

## Consequences

- **Breaking:** `POST /run` callers must read the result from the `task.completed` SSE
  frame on `/stream`. The demo harness + frontend migrate to SSE-driven retrieval.
- **No `'dispatched'` status:** the `tasks.tasks.status` CHECK has no such value, so
  the row stays `'queued'` + a `dispatched_at` marker until the worker flips it to
  `'running'`. No CHECK migration.
- **Idempotency / redelivery:** the worker guards on `status == 'queued'`, so a
  Dramatiq retry / duplicate delivery is a no-op (never double-runs / double-charges;
  budget reserve/refund is per-run).
- **Commit-then-enqueue** (outbox deferred = AC-W1-4): a crash between commit and
  `.send()` strands a task as `queued` + `dispatched_at` (recoverable by re-POST or a
  future reconciliation sweeper) — chosen over the worse enqueue-then-commit race.
- **Shared seam:** provider matrix + LLMRouter assembly extracted to
  `llm_gateway/factory.py::build_llm_router` so web + worker never drift.
- **Worker RLS:** the actor has no request middleware, so it resolves the tenant via
  the SECURITY-DEFINER membership lookup and sets the 3 GUCs itself before any query.
- **Backend selection:** `Settings.sse_backend` (default `inprocess` → CI + single-
  worker dev) selects the publisher; docker/staging set `SSE_BACKEND=redis` on **both**
  the backend and worker services.
- **Coupled hardening landed:** OTel `setup_otel` made thread-safe (AC-W1-12, the
  multi-worker re-entry this unlocks) + a span processor that redacts `Authorization`
  / subscription-token / api-key headers from spans (AC-W1-11).

## Deferred (documented, not silent)

- **AC-W1-13** (populate the 9 Prometheus metrics + real cost ledger): under async
  dispatch the orchestration runs in the worker, so real metric values now need
  worker-side Prometheus exposition + scrape config — a coherent chunk that ships with
  the other deferred observability pins (AC-W1-2/14/15) in a follow-up.
- **AC-W1-19 native web_search tool-call** → [ADR-035](./ADR-035-deepseek-gated-web-search-tool-call.md)
  (only the Settings `mock_mode` bug was fixed in this PR).

## Links

- [ADR-032](./ADR-032-coordinator-plan-then-execute.md) — plan-then-execute Coordinator
  (the orchestration this dispatches).
- [ADR-002](./ADR-002-llm-gateway.md) — LLM gateway + failover (the shared router seam).
- [ADR-025](./ADR-025-acceptance-gate-format.md) — acceptance-gate format (AC8 reframe note).
- Phase-spec: `../roadmap/wave-1-core-mvp/phases/01.1-retro.md` AC-W1-16a / AC-W1-1 /
  AC-W1-23 / AC-W1-11 / AC-W1-12 / AC-W1-21.
