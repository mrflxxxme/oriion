"""CloudEvents 1.0 emitter — log-only Wave 0 backend.

Per ADR-024 §3 every domain event uses the CloudEvents 1.0 envelope. Wave 0
transport is structlog-tagged log records (consistent with Phase 00.2 impl);
Wave 1+ swaps the same emit-API to Redis Streams `XADD` without touching
callers. Tests assert log records via `caplog` / `structlog.testing.capture_logs`.

Usage::

    from src._shared.cloudevents import emit_cloudevent

    await emit_cloudevent(
        ce_type="oriion.multitenancy.workspace.created.v1",
        source="oriion://contexts/multitenancy",
        data={
            "workspace_id": str(workspace.id),
            "slug": workspace.slug,
            "plan_tier": workspace.plan_tier,
            "created_by_user_id": str(user.id),
        },
    )

The function is `async def` so callers can swap the implementation to a real
async pub/sub (Redis Streams, NATS, Kafka) in Wave 1+ without an interface
change. Wave 0 simply emits a structlog record and returns.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

__all__ = ["emit_cloudevent"]

_logger = structlog.get_logger(__name__)


async def emit_cloudevent(
    *,
    ce_type: str,
    source: str,
    data: dict[str, Any],
    subject: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Emit a CloudEvents 1.0-shaped record.

    Args:
        ce_type: CloudEvent type (e.g. ``oriion.multitenancy.cell.created.v1``).
            Must match the canonical type in ``contracts/<context>/events.yaml``.
        source: Logical source URI (e.g. ``oriion://contexts/multitenancy``).
        data: Event payload — should validate against the schema declared in
            the relevant events.yaml. Validation is currently caller's
            responsibility; Wave 1+ swap may introduce JSON-Schema validation.
        subject: Optional CloudEvents ``subject`` discriminator.
        correlation_id: Optional caller-supplied id for tying multi-event
            transactions together (e.g. provisioning workflow). Defaults to a
            fresh uuid4 string.

    Returns:
        None — emission is fire-and-log Wave 0 (no provider ack).
    """
    _logger.bind(
        cloudevent=True,
        ce_specversion="1.0",
        ce_id=str(uuid4()),
        ce_type=ce_type,
        ce_source=source,
        ce_subject=subject,
        ce_time=datetime.now(UTC).isoformat(),
        ce_correlation_id=correlation_id or str(uuid4()),
        ce_datacontenttype="application/json",
    ).info("cloudevent.emitted", data=data)
