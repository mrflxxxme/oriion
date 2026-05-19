"""Unit tests for ProviderCircuit state machine.

Covers all four documented transitions per phase-spec 00.4:
    CLOSED    → OPEN       (3 consecutive failures)
    OPEN      → HALF_OPEN   (cooldown elapsed)
    HALF_OPEN → CLOSED      (successful probe)
    HALF_OPEN → OPEN        (failed probe, cooldown resets)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit


def test_initial_state_is_closed_and_allows_attempts() -> None:
    c = ProviderCircuit(provider="deepseek")
    assert c.state is CircuitState.CLOSED
    assert c.should_attempt is True


def test_three_consecutive_failures_trip_circuit_open() -> None:
    c = ProviderCircuit(provider="deepseek")
    c.record_failure()
    assert c.state is CircuitState.CLOSED
    c.record_failure()
    assert c.state is CircuitState.CLOSED
    c.record_failure()
    assert c.state is CircuitState.OPEN
    assert c.opened_at is not None


def test_success_resets_failure_counter_and_keeps_circuit_closed() -> None:
    c = ProviderCircuit(provider="deepseek")
    c.record_failure()
    c.record_failure()
    c.record_success()
    assert c.consecutive_failures == 0
    assert c.state is CircuitState.CLOSED


def test_open_circuit_blocks_attempts_before_cooldown() -> None:
    c = ProviderCircuit(provider="deepseek", cooldown_seconds=60)
    for _ in range(3):
        c.record_failure()
    assert c.state is CircuitState.OPEN
    # Just-opened — within cooldown window.
    assert c.should_attempt is False


def test_open_to_half_open_after_cooldown() -> None:
    c = ProviderCircuit(provider="deepseek", cooldown_seconds=60)
    for _ in range(3):
        c.record_failure()
    # Backdate opened_at so cooldown is considered elapsed.
    c.opened_at = datetime.now(UTC) - timedelta(seconds=120)
    assert c.should_attempt is True
    assert c.state is CircuitState.HALF_OPEN


def test_half_open_success_closes_circuit() -> None:
    c = ProviderCircuit(provider="deepseek", state=CircuitState.HALF_OPEN)
    c.record_success()
    assert c.state is CircuitState.CLOSED
    assert c.consecutive_failures == 0


def test_half_open_failure_reopens_circuit_and_resets_cooldown() -> None:
    c = ProviderCircuit(
        provider="deepseek",
        state=CircuitState.HALF_OPEN,
        opened_at=datetime.now(UTC) - timedelta(seconds=120),
    )
    c.record_failure()
    assert c.state is CircuitState.OPEN
    assert c.opened_at is not None
    # opened_at refreshed — within cooldown again.
    assert c.should_attempt is False
