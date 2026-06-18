# ADR-036: Transactional-outbox relay — self-rescheduling actor (Wave-0 bridge)

- **Status:** Accepted (Phase 01.1-retro closeout, 2026-06-18)
- **Deciders:** Tech Lead, Founder
- **Closes:** the AC-W1-4 relay-scheduling gap surfaced by the post-merge #58–61
  adversarial audit (the relay was written + unit-tested but never invoked by any
  running process — outbox rows committed with `published_at = NULL` forever).

## Context

AC-W1-4 (PR #60) shipped the transactional-outbox **write** path correctly: a
`task.created` / `task.cancelled` CloudEvent is INSERTed in the **same TX** as the
state change (`SqlAlchemyTaskRepository.add_outbox_event`). But the **drain** half
— `relay_outbox_actor` / `trigger_outbox_relay` in `runtime/queue/outbox_relay.py`
— was dead code: `worker.py` imported only `dispatch_task_actor`, no producer
called `trigger_outbox_relay()`, and there is **no periodic scheduler** in the
stack. So the AC acceptance *"a relay publishes them"* was unmet (the audit's only
non-dormant-but-real P1).

Forces:
- Wave-0 has **no downstream consumer** yet — `emit_cloudevent` is a log-only
  structlog sink; the real consumer is the Wave-1 Redis-Streams swap. So the relay
  must *run* (drain rows at-least-once) but does not yet need delivery guarantees
  beyond the log.
- The worker runs `dramatiq … -p1 -t1` (single global-budget invariant F-ARC-H2).
- We do **not** want to add a `periodiq`/APScheduler dependency + a second
  scheduler process for a Wave-0 bridge that Wave-1 will replace.

## Decision

The relay drains itself via a **self-rescheduling Dramatiq actor**:
`relay_outbox_actor` runs `_run_relay()`, then **re-enqueues itself** with a fixed
delay (`schedule_next_relay()` → `send_with_options(delay=OUTBOX_RELAY_INTERVAL_MS)`,
default 2000 ms) in a `finally`. `worker.py` kicks off **one** chain at boot
(`relay_outbox_actor.send()`, guarded out of the `DRAMATIQ_TESTING` StubBroker
path). `trigger_outbox_relay()` is retained for an optional low-latency nudge after
a producer commit. No new dependency, no second process.

Coupled hardening (same change): the batch publishes with **per-row failure
isolation** — a row whose publish raises is left unpublished and retried next run
while siblings still commit, so one poison row neither rolls back already-published
rows (no duplicate storm) nor blocks newer rows (no head-of-line starvation). The
drain order is the deterministic `(created_at, id)`.

## Consequences

- ✅ AC-W1-4 acceptance now holds end-to-end: rows are written in-TX **and** a relay
  publishes them at-least-once on a fixed cadence (default 2 s).
- ✅ `max_retries=0` on the actor: a failed run does not fork a second drain chain —
  at-least-once is carried by `WHERE published_at IS NULL`, not by Dramatiq retries;
  the `finally` re-arm keeps the chain alive across a transient DB/publish outage.
- ⚠️ A worker **restart starts a fresh chain** while the previous chain's last
  delayed message may still be pending → transiently >1 overlapping chain. Harmless
  (extra drains are idempotent via `SKIP LOCKED` + `published_at`), bounded by how
  often the single worker restarts.
- ⚠️ A permanently-failing ("poison") row is retried every sweep (bounded log noise);
  a durable dead-letter (attempt counter + quarantine column + a small migration) is
  deferred to Wave-1, when a real downstream consumer makes publish failures meaningful.
- 🔮 **Wave-1:** replace the self-reschedule with a proper periodic scheduler and swap
  `emit_cloudevent` for the Redis-Streams XADD consumer; add the dead-letter column
  + an after-commit `trigger_outbox_relay()` in the producer paths for low latency.

## Alternatives Considered

| Альтернатива | Pro | Contra | Почему отклонили |
|---|---|---|---|
| `periodiq` / APScheduler beat | Real cron semantics | New dependency + a 2nd process for a Wave-0 bridge Wave-1 replaces | Premature infra; over-weight for a log-only sink |
| After-commit `trigger_outbox_relay()` only (no periodic) | Lowest latency, simplest | A lost trigger (crash between commit + send) leaves a row undrained forever → breaks at-least-once | Insufficient as the sole mechanism |
| Leave dead + mark AC-W1-4 PARTIAL, defer to obs/IaC follow-up | Smallest diff now | Ships an AC the suite claims green but doesn't meet | Founder chose fix-to-green at the 01.1-retro grill |
| Dead-letter columns + per-row TX now | Most robust | Migration + schema churn for a sink with no real consumer yet | Deferred to Wave-1 with the Redis-Streams consumer |

## Links

- [ADR-034](./ADR-034-async-dispatch-redis-sse-ac8-reframe.md) — async dispatch + the
  "outbox deferred = AC-W1-4" note this closes.
- Phase-spec: [`../roadmap/wave-1-core-mvp/phases/01.1-retro.md`](../roadmap/wave-1-core-mvp/phases/01.1-retro.md) AC-W1-4.
- Risk: [R-04](../risks/REGISTER.md) (runaway costs — event-driven budget signals ride this bus in Wave-1).
