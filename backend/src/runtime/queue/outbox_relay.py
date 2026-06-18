"""Transactional-outbox relay (AC-W1-4).

Drains unpublished ``tasks.outbox`` rows and republishes each domain CloudEvent
**at-least-once**: every row is published BEFORE its ``published_at`` is stamped
and the batch commits, so a crash before the commit leaves the row unpublished
and it is re-published next run. Downstream consumers dedupe on the stable
``ce_id``. Concurrent relays don't collide — rows are claimed
``FOR UPDATE SKIP LOCKED``.

**Per-row failure isolation (AC-W1-4 hardening):** publish is wrapped per row.
A row whose publish raises is left unpublished (``published_at`` stays NULL) and
is retried on the next run, while the rows around it still commit — so one
failing ("poison") row neither rolls back already-published siblings
(no duplicate storm) nor blocks the newer rows behind it (no head-of-line
starvation). A row that fails permanently is retried each sweep and logged;
a durable dead-letter (attempt counter + quarantine column) is a Wave-1 item
once a real downstream consumer (Redis-Streams) replaces the log-only sink.

**Scheduling:** ``relay_outbox_actor`` is a Dramatiq actor that re-schedules
itself with a fixed delay after each run (a self-perpetuating periodic drain
that needs no ``periodiq``/cron dependency — the Wave-0 bridge per
[ADR-036](../../../../.planning/decisions/ADR-036-outbox-relay-self-scheduling.md));
the worker entrypoint kicks off one chain at boot. ``trigger_outbox_relay``
lets a producer nudge an extra run after a commit for lower latency. Wave-1
swaps the self-reschedule for a proper scheduler + Redis-Streams consumer.
"""

from __future__ import annotations

import os
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import dramatiq
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src._shared.cloudevents import emit_cloudevent
from src._shared.config import get_settings
from src.runtime.queue import broker  # noqa: F401 — installs the broker before @actor binds
from src.tasks.models import OutboxEvent

logger = structlog.get_logger(__name__)

PublishFn = Callable[[OutboxEvent], Awaitable[None]]
OUTBOX_RELAY_BATCH = 100
# Self-reschedule interval for the periodic drain (ms). Operator-tunable via env
# for Wave-0; a longer interval = higher event latency, lower DB poll rate.
OUTBOX_RELAY_INTERVAL_MS = int(os.environ.get("OUTBOX_RELAY_INTERVAL_MS", "2000"))

# Strip ``user:password@`` from a DSN before it can reach a log. A connection
# error from a future Redis-Streams publisher (or the engine build) can carry the
# DSN; the proper fix is SecretStr DSN fields (tracked follow-up), this is the
# cheap belt-and-braces for the relay's own log sites.
_DSN_CREDS_RE = re.compile(r"://[^@/\s]+@")


def _safe_error(exc: Exception) -> str:
    return _DSN_CREDS_RE.sub("://<redacted>@", str(exc))


async def _publish_event(event: OutboxEvent) -> None:
    """Default publisher — re-emits the CloudEvent with its STABLE ce_id so
    at-least-once redelivery is idempotent downstream (Wave-1 swaps emit_cloudevent
    for Redis-Streams XADD without touching this relay)."""
    await emit_cloudevent(
        ce_type=event.ce_type,
        source=event.ce_source,
        data=event.data,
        subject=event.ce_subject,
        correlation_id=event.correlation_id,
        ce_id=str(event.ce_id),
    )


async def relay_outbox_batch(
    session: AsyncSession,
    *,
    publish: PublishFn = _publish_event,
    batch_size: int = OUTBOX_RELAY_BATCH,
) -> int:
    """Publish up to ``batch_size`` unpublished outbox rows; return the count
    actually published.

    Failure isolation is per-row: each row is published before its
    ``published_at`` is stamped; if ``publish`` raises, that row is left
    unpublished (retried next run) and the loop CONTINUES to the next row, then
    the successfully-published rows are committed once at the end. This means a
    transient or permanent failure on one row does not roll back the rows
    already published in the same batch (no duplicate re-publish) and does not
    block the rows behind it (no head-of-line starvation).
    """
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        # (created_at, id) is a deterministic total order so the downstream
        # publish order is stable for rows sharing a created_at tick.
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list((await session.execute(stmt)).scalars().all())
    now = datetime.now(UTC)
    published = 0
    failed = 0
    for event in events:
        try:
            await publish(event)
        except Exception as exc:  # isolate one row's failure from the rest of the batch
            failed += 1
            logger.warning(
                "runtime.outbox.relay.publish_failed",
                ce_id=str(event.ce_id),
                ce_type=event.ce_type,
                error=_safe_error(exc),
            )
            continue
        event.published_at = now
        published += 1
    await session.commit()
    if published or failed:
        logger.info("runtime.outbox.relay.published", count=published, failed=failed)
    return published


async def _run_relay() -> int:
    """Worker-side entry: a fresh NullPool engine + session per run (each
    asyncio.run gets its own loop, so a pooled engine would bind to a dead one)."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
        async with maker() as session:
            return await relay_outbox_batch(session)
    finally:
        await engine.dispose()


def schedule_next_relay() -> None:
    """Enqueue the next periodic relay tick after ``OUTBOX_RELAY_INTERVAL_MS``.

    This is what makes ``relay_outbox_actor`` self-perpetuating: one boot-time
    ``send()`` starts a chain that re-arms itself after every run, so the outbox
    is drained on a fixed cadence with no external scheduler (ADR-036).
    """
    relay_outbox_actor.send_with_options(delay=OUTBOX_RELAY_INTERVAL_MS)


@dramatiq.actor(max_retries=0, queue_name="outbox")
def relay_outbox_actor(*, periodic: bool = True) -> None:
    """Sync Dramatiq actor wrapping the async relay; one fresh loop per message.

    ``max_retries=0`` so a failed run does not fork a second drain chain — the
    next scheduled tick re-reads any rows left unpublished (at-least-once is
    carried by ``WHERE published_at IS NULL``, not by Dramatiq retries).

    ``periodic`` controls the self-reschedule: a **periodic** run re-arms the
    chain in its ``finally`` (so the cadence survives a transient DB/publish
    outage); a **nudge** run (``trigger_outbox_relay`` → ``periodic=False``) does
    NOT re-arm, so an after-commit nudge drains once without forking a SECOND
    perpetual chain. Exactly one periodic chain exists per worker boot.
    """
    import asyncio

    try:
        asyncio.run(_run_relay())
    except Exception as exc:  # never break the self-reschedule chain on a transient failure
        # Redacted error + type instead of logger.exception's full traceback: a
        # DB connection error can carry the DSN, and the chain re-runs in seconds.
        logger.error(
            "runtime.outbox.relay.run_failed",
            error=_safe_error(exc),
            exc_type=type(exc).__name__,
        )
    finally:
        if periodic:
            schedule_next_relay()


def trigger_outbox_relay() -> None:
    """Enqueue a one-shot relay run (call after committing producer state changes
    for lower latency than waiting for the next periodic tick). ``periodic=False``
    so the nudge does not start its own perpetual self-reschedule chain — only the
    boot-time chain re-arms itself."""
    relay_outbox_actor.send(periodic=False)
