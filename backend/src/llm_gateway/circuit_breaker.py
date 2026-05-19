"""Per-provider circuit-breaker state machine.

Per phase-spec 00.4 inline definition. State transitions:

    CLOSED    → OPEN       : 3 consecutive failures (5xx OR timeout >30s)
    OPEN      → HALF_OPEN  : after `cooldown_seconds` (default 60s)
    HALF_OPEN → CLOSED     : single successful probe request
    HALF_OPEN → OPEN       : failed probe (reset cooldown)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum


class CircuitState(str, Enum):
    """Per-provider circuit state."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProviderCircuit:
    """Mutable per-provider circuit state.

    Single-process, in-memory. Multi-instance coordination is Wave 1+ (Redis-
    backed shared state). For Wave 0 each gateway instance maintains its own
    circuit; degraded events still propagate via cloudevents.
    """

    provider: str
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_at: datetime | None = None
    opened_at: datetime | None = None
    cooldown_seconds: int = 60

    # -- queries --------------------------------------------------------------
    @property
    def should_attempt(self) -> bool:
        """Whether the circuit allows the next request.

        Side-effect: if OPEN and cooldown has elapsed, transitions to HALF_OPEN
        and returns True so the caller can probe the upstream once.
        """
        if self.state is CircuitState.CLOSED:
            return True
        if self.state is CircuitState.OPEN:
            return self.try_half_open()
        # HALF_OPEN — one probe attempt allowed.
        return True

    def try_half_open(self) -> bool:
        """If cooldown has elapsed since OPEN, transition to HALF_OPEN.

        Returns True iff the transition happened (caller may now probe).
        Returns False if still cooling down (caller must skip this provider).
        """
        if self.state is not CircuitState.OPEN or self.opened_at is None:
            return False
        elapsed = datetime.now(UTC) - self.opened_at
        if elapsed >= timedelta(seconds=self.cooldown_seconds):
            self.state = CircuitState.HALF_OPEN
            return True
        return False

    # -- mutations ------------------------------------------------------------
    def record_success(self) -> None:
        """Successful request — close the circuit, reset failure counter."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_at = None
        self.opened_at = None

    def record_failure(self, consecutive_threshold: int = 3) -> None:
        """Failed request. Trip OPEN at the threshold (default 3).

        If currently HALF_OPEN, a single failure trips OPEN again (reset cooldown).
        """
        now = datetime.now(UTC)
        self.last_failure_at = now

        if self.state is CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = now
            # Probe failed — bump counter but the trip already happened.
            self.consecutive_failures += 1
            return

        self.consecutive_failures += 1
        if self.state is CircuitState.CLOSED and self.consecutive_failures >= consecutive_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = now
