"""Per-provider health monitor — Wave 0 single-check (no background loop).

Wave 1+ will spawn a 30s asyncio background task per provider; Wave 0
exposes only `check_provider(...)` so tests can assert state-transition
cloudevents without orchestrating a background scheduler.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from src.llm_gateway import events as gateway_events
from src.llm_gateway.providers.base import LLMProvider

ProviderHealthState = str  # one of 'healthy' | 'degraded' | 'down'


class HealthMonitor:
    """Single-call provider health checker with state-transition emission."""

    def __init__(self) -> None:
        # Last observed state per provider; missing key == 'healthy' (assume).
        self._state: dict[str, ProviderHealthState] = {}

    async def check_provider(
        self,
        provider: LLMProvider,
    ) -> tuple[ProviderHealthState, int]:
        """Run a single health-check. Returns (new_state, latency_ms).

        Emits ``provider.health_change.v1`` if the state changed since the
        last observation.
        """
        slug = provider.name
        old_state = self._state.get(slug, "healthy")
        t0 = time.perf_counter()
        try:
            ok = await provider.health_check()
        except Exception:
            ok = False
        latency_ms = int((time.perf_counter() - t0) * 1000)
        new_state: ProviderHealthState = "healthy" if ok else "down"
        self._state[slug] = new_state

        if new_state != old_state:
            await gateway_events.emit_provider_health_change(
                provider_slug=slug,
                old_state=old_state,
                new_state=new_state,
                checked_at=datetime.now(UTC).isoformat(),
            )

        return new_state, latency_ms

    def current_state(self, provider_slug: str) -> ProviderHealthState:
        """Last observed state — defaults to 'healthy' if never checked."""
        return self._state.get(provider_slug, "healthy")
