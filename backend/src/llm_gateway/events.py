"""CloudEvents emitters for llm_gateway per contracts/llm-gateway/events.yaml.

Each function wraps ``src._shared.cloudevents.emit_cloudevent`` with the
canonical event type + source URI for the bounded context. Data payload
fields match the data_schema declared in events.yaml — fields are passed as
kwargs and serialized as primitives (UUID -> str, Decimal -> str via float
cast — Decimal preserved as string to avoid silent float widening).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from src._shared.cloudevents import emit_cloudevent

_SOURCE = "oriion://contexts/llm-gateway"


def _maybe(uid: UUID | None) -> str | None:
    return str(uid) if uid is not None else None


def _dec(value: Decimal | int | float) -> float:
    """Decimal → float for JSON serialization.

    Monetary precision is preserved in the DB (numeric); cloudevents are
    log-only Wave 0 so float precision is sufficient for downstream consumers
    (they re-read the DB row for authoritative values).
    """
    return float(value)


async def emit_request_completed(
    *,
    request_id: str,
    workspace_id: UUID,
    cell_id: UUID,
    task_id: UUID | None,
    byok_key_id: UUID | None,
    provider_slug: str,
    model: str,
    status: str,
    cost_usd: Decimal,
    cost_rub: Decimal,
    fx_rate_usd_to_rub: Decimal,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Emit ``oriion.llm-gateway.request.completed.v1``."""
    data: dict[str, Any] = {
        "request_id": request_id,
        "workspace_id": str(workspace_id),
        "cell_id": str(cell_id),
        "task_id": _maybe(task_id),
        "byok_key_id": _maybe(byok_key_id),
        "provider_slug": provider_slug,
        "model": model,
        "status": status,
        "cost_usd": _dec(cost_usd),
        "cost_rub": _dec(cost_rub),
        "fx_rate_usd_to_rub": _dec(fx_rate_usd_to_rub),
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.request.completed.v1",
        source=_SOURCE,
        data=data,
        subject=request_id,
    )


async def emit_byok_created(
    *,
    byok_key_id: UUID,
    workspace_id: UUID,
    provider_slug: str,
    label: str,
    created_by: UUID,
) -> None:
    """Emit ``oriion.llm-gateway.byok.created.v1``."""
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.byok.created.v1",
        source=_SOURCE,
        data={
            "byok_key_id": str(byok_key_id),
            "workspace_id": str(workspace_id),
            "provider_slug": provider_slug,
            "label": label,
            "created_by": str(created_by),
        },
        subject=str(byok_key_id),
    )


async def emit_byok_quota_warning(
    *,
    byok_key_id: UUID,
    workspace_id: UUID,
    percent_used: Decimal,
    monthly_used_usd: Decimal,
    monthly_quota_usd: Decimal,
) -> None:
    """Emit ``oriion.llm-gateway.byok.quota_warning.v1`` (80% threshold)."""
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.byok.quota_warning.v1",
        source=_SOURCE,
        data={
            "byok_key_id": str(byok_key_id),
            "workspace_id": str(workspace_id),
            "percent_used": _dec(percent_used),
            "monthly_used_usd": _dec(monthly_used_usd),
            "monthly_quota_usd": _dec(monthly_quota_usd),
        },
        subject=str(byok_key_id),
    )


async def emit_byok_quota_exceeded(
    *,
    byok_key_id: UUID,
    workspace_id: UUID,
    monthly_used_usd: Decimal,
    monthly_quota_usd: Decimal,
) -> None:
    """Emit ``oriion.llm-gateway.byok.quota_exceeded.v1``.

    Per invariant #4 this does NOT fail-closed; emission is informational.
    """
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.byok.quota_exceeded.v1",
        source=_SOURCE,
        data={
            "byok_key_id": str(byok_key_id),
            "workspace_id": str(workspace_id),
            "monthly_used_usd": _dec(monthly_used_usd),
            "monthly_quota_usd": _dec(monthly_quota_usd),
        },
        subject=str(byok_key_id),
    )


async def emit_provider_degraded(
    *,
    provider_slug: str,
    error_rate_pct: Decimal,
    window_started_at: str,
    failover_to: str | None,
) -> None:
    """Emit ``oriion.llm-gateway.provider.degraded.v1`` (auto-failover trigger)."""
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.provider.degraded.v1",
        source=_SOURCE,
        data={
            "provider_slug": provider_slug,
            "error_rate_pct": _dec(error_rate_pct),
            "window_started_at": window_started_at,
            "failover_to": failover_to,
        },
        subject=provider_slug,
    )


async def emit_provider_health_change(
    *,
    provider_slug: str,
    old_state: str,
    new_state: str,
    checked_at: str,
) -> None:
    """Emit ``oriion.llm-gateway.provider.health_change.v1`` (state transition)."""
    await emit_cloudevent(
        ce_type="oriion.llm-gateway.provider.health_change.v1",
        source=_SOURCE,
        data={
            "provider_slug": provider_slug,
            "old_state": old_state,
            "new_state": new_state,
            "checked_at": checked_at,
        },
        subject=provider_slug,
    )
