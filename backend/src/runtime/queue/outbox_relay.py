"""Transactional-outbox relay (AC-W1-4).

Drains unpublished ``tasks.outbox`` rows and republishes each domain CloudEvent
**at-least-once**: ``publish`` runs BEFORE ``published_at`` is stamped + the TX
commits, so a crash between the two leaves the row unpublished and it is
re-published next run. Downstream consumers dedupe on the stable ``ce_id``.
Concurrent relays don't collide — rows are claimed ``FOR UPDATE SKIP LOCKED``.

Scheduling: ``relay_outbox_actor`` is a Dramatiq actor; the worker entrypoint
enqueues it periodically (and ``trigger_outbox_relay`` lets a producer nudge it
after a commit) so created/cancelled events are published promptly.
"""

from __future__ import annotations

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
    """Publish up to ``batch_size`` unpublished outbox rows; return the count.

    At-least-once ordering is deliberate: every row is published before its
    ``published_at`` is stamped and the TX commits. If ``publish`` raises, the
    stamp + commit never happen and the row is retried on the next run.
    """
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list((await session.execute(stmt)).scalars().all())
    now = datetime.now(UTC)
    for event in events:
        await publish(event)
        event.published_at = now
    await session.commit()
    if events:
        logger.info("runtime.outbox.relay.published", count=len(events))
    return len(events)


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


@dramatiq.actor(max_retries=3, queue_name="outbox")
def relay_outbox_actor() -> None:
    """Sync Dramatiq actor wrapping the async relay; one fresh loop per message."""
    import asyncio

    asyncio.run(_run_relay())


def trigger_outbox_relay() -> None:
    """Enqueue a relay run (call after committing producer state changes)."""
    relay_outbox_actor.send()
