"""AC7 — failover detection ≤ 5s.

Simulate 3 consecutive DeepSeek failures → circuit OPEN → next router.route
call selects YandexGPT. The whole sequence runs in microseconds since
providers are mocked; the test asserts wall-clock < 5s as documented.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit
from src.llm_gateway.services.router_service import LLMRouter


def _provider(name: str) -> AsyncMock:
    p = AsyncMock()
    p.name = name
    return p


@pytest.mark.asyncio
async def test_failover_to_yandex_under_5s() -> None:
    """Three failures on deepseek → circuit OPEN → routing falls to yandex < 5s."""
    deepseek = _provider("deepseek")
    yandex = _provider("yandexgpt")
    gigachat = _provider("gigachat")
    providers = {"deepseek": deepseek, "yandexgpt": yandex, "gigachat": gigachat}
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}

    router = LLMRouter(providers=providers, circuits=circuits)

    t0 = time.perf_counter()

    # Simulate 3 failures on deepseek.
    for _ in range(3):
        circuits["deepseek"].record_failure()
    assert circuits["deepseek"].state is CircuitState.OPEN

    # Route subsequent request — should land on yandex.
    provider, _model = await router.route(
        workspace_id=uuid4(),
        role_key="coordinator",
        model_hint=None,
    )

    elapsed = time.perf_counter() - t0
    assert provider.name == "yandexgpt"
    assert elapsed < 5.0, f"Failover took {elapsed:.3f}s (>5s budget per AC7)"
