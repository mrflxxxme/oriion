"""Unit tests for HealthMonitor — state-transition emission."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import structlog
from src.llm_gateway.services.health_service import HealthMonitor


def _provider(name: str, *, healthy: bool) -> AsyncMock:
    p = AsyncMock()
    p.name = name
    p.health_check = AsyncMock(return_value=healthy)
    return p


def _provider_raising(name: str) -> AsyncMock:
    p = AsyncMock()
    p.name = name
    p.health_check = AsyncMock(side_effect=RuntimeError("upstream nuked"))
    return p


@pytest.mark.asyncio
async def test_health_monitor_initial_healthy_check_no_emission() -> None:
    """First check returning healthy keeps state healthy — no transition event."""
    monitor = HealthMonitor()
    with structlog.testing.capture_logs() as logs:
        state, latency = await monitor.check_provider(_provider("deepseek", healthy=True))
    assert state == "healthy"
    assert latency >= 0
    # No state change → no health_change.v1 event.
    assert not any(log.get("ce_type", "").endswith("health_change.v1") for log in logs)


@pytest.mark.asyncio
async def test_health_monitor_emits_event_on_state_transition() -> None:
    monitor = HealthMonitor()
    # Prime as healthy.
    await monitor.check_provider(_provider("deepseek", healthy=True))
    # Now upstream goes down.
    with structlog.testing.capture_logs() as logs:
        state, _ = await monitor.check_provider(_provider("deepseek", healthy=False))
    assert state == "down"
    ce = next(log for log in logs if log.get("ce_type", "").endswith("health_change.v1"))
    assert ce["data"]["provider_slug"] == "deepseek"
    assert ce["data"]["old_state"] == "healthy"
    assert ce["data"]["new_state"] == "down"


@pytest.mark.asyncio
async def test_health_monitor_catches_exception_from_provider() -> None:
    monitor = HealthMonitor()
    state, _ = await monitor.check_provider(_provider_raising("yandexgpt"))
    assert state == "down"
    # Subsequent state query reflects observed state.
    assert monitor.current_state("yandexgpt") == "down"


def test_current_state_defaults_to_healthy() -> None:
    monitor = HealthMonitor()
    assert monitor.current_state("never-checked") == "healthy"
