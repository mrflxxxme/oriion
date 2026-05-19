"""Coverage tests for src.llm_gateway.events emitter wrappers.

Each helper wraps emit_cloudevent — we assert the ce_type lands on the
captured structlog record and that the data dict includes the documented
fields. Stub paths in events.py (lines 109, 134, 155, 176) are the bodies
of each emitter and are covered here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
import structlog
from src.llm_gateway import events as gw_events


@pytest.mark.asyncio
async def test_emit_byok_quota_warning() -> None:
    with structlog.testing.capture_logs() as logs:
        await gw_events.emit_byok_quota_warning(
            byok_key_id=uuid4(),
            workspace_id=uuid4(),
            percent_used=Decimal("80.5"),
            monthly_used_usd=Decimal("40.25"),
            monthly_quota_usd=Decimal("50.00"),
        )
    ce = next(log for log in logs if log.get("ce_type", "").endswith("byok.quota_warning.v1"))
    assert ce["data"]["percent_used"] == 80.5


@pytest.mark.asyncio
async def test_emit_byok_quota_exceeded() -> None:
    with structlog.testing.capture_logs() as logs:
        await gw_events.emit_byok_quota_exceeded(
            byok_key_id=uuid4(),
            workspace_id=uuid4(),
            monthly_used_usd=Decimal("55.00"),
            monthly_quota_usd=Decimal("50.00"),
        )
    ce = next(log for log in logs if log.get("ce_type", "").endswith("byok.quota_exceeded.v1"))
    assert ce["data"]["monthly_used_usd"] == 55.0


@pytest.mark.asyncio
async def test_emit_provider_degraded() -> None:
    with structlog.testing.capture_logs() as logs:
        await gw_events.emit_provider_degraded(
            provider_slug="deepseek",
            error_rate_pct=Decimal("12.5"),
            window_started_at=datetime.now(UTC).isoformat(),
            failover_to="yandexgpt",
        )
    ce = next(log for log in logs if log.get("ce_type", "").endswith("provider.degraded.v1"))
    assert ce["data"]["failover_to"] == "yandexgpt"


@pytest.mark.asyncio
async def test_emit_provider_health_change() -> None:
    with structlog.testing.capture_logs() as logs:
        await gw_events.emit_provider_health_change(
            provider_slug="deepseek",
            old_state="healthy",
            new_state="down",
            checked_at=datetime.now(UTC).isoformat(),
        )
    ce = next(log for log in logs if log.get("ce_type", "").endswith("provider.health_change.v1"))
    assert ce["data"]["new_state"] == "down"
