"""Unit tests for LLMRouter — circuit-skip + failover chain."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit
from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.services.router_service import LLMRouter


def _make_provider(name: str) -> AsyncMock:
    p = AsyncMock()
    p.name = name
    return p


@pytest.mark.asyncio
async def test_router_returns_primary_when_all_circuits_closed() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)

    provider, model = await router.route(
        workspace_id=uuid4(),
        role_key="coordinator",
        model_hint=None,
    )
    assert provider.name == "deepseek"
    assert model == "deepseek-chat"  # AC-W1-16b: coordinator on chat, not reasoner


@pytest.mark.asyncio
async def test_router_skips_open_circuit_and_failovers_to_yandex() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {
        "deepseek": ProviderCircuit(
            provider="deepseek",
            state=CircuitState.OPEN,
            opened_at=datetime.now(UTC),  # within cooldown
            cooldown_seconds=60,
        ),
        "yandexgpt": ProviderCircuit(provider="yandexgpt"),
        "gigachat": ProviderCircuit(provider="gigachat"),
    }
    router = LLMRouter(providers=providers, circuits=circuits)

    provider, model = await router.route(
        workspace_id=uuid4(),
        role_key="coordinator",
        model_hint=None,
    )
    assert provider.name == "yandexgpt"
    assert model.startswith("yandexgpt")


@pytest.mark.asyncio
async def test_router_skips_open_then_open_falls_through_to_gigachat() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    open_circ = lambda: ProviderCircuit(  # noqa: E731
        provider="x",
        state=CircuitState.OPEN,
        opened_at=datetime.now(UTC),
        cooldown_seconds=300,
    )
    circuits = {
        "deepseek": open_circ(),
        "yandexgpt": open_circ(),
        "gigachat": ProviderCircuit(provider="gigachat"),
    }
    router = LLMRouter(providers=providers, circuits=circuits)

    provider, _ = await router.route(
        workspace_id=uuid4(),
        role_key="specialist",
        model_hint=None,
    )
    assert provider.name == "gigachat"


@pytest.mark.asyncio
async def test_router_raises_when_all_circuits_open() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    open_circ = lambda: ProviderCircuit(  # noqa: E731
        provider="x",
        state=CircuitState.OPEN,
        opened_at=datetime.now(UTC),
        cooldown_seconds=300,
    )
    circuits = {slug: open_circ() for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)
    with pytest.raises(LLMProviderUnavailable):
        await router.route(workspace_id=uuid4(), role_key="default", model_hint=None)


@pytest.mark.asyncio
async def test_router_opens_circuit_promotes_to_half_open_after_cooldown() -> None:
    """OPEN circuit with expired cooldown should be probeable (half_open)."""
    providers = {"deepseek": _make_provider("deepseek")}
    circuits = {
        "deepseek": ProviderCircuit(
            provider="deepseek",
            state=CircuitState.OPEN,
            opened_at=datetime.now(UTC) - timedelta(seconds=120),
            cooldown_seconds=60,
        ),
    }
    router = LLMRouter(providers=providers, circuits=circuits)
    provider, _ = await router.route(
        workspace_id=uuid4(),
        role_key="default",
        model_hint=None,
    )
    assert provider.name == "deepseek"
    assert circuits["deepseek"].state is CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_failover_chain_skips_exclude_list() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)
    fallback = await router.failover_chain(role_key="default", exclude=["deepseek"])
    assert fallback.name == "yandexgpt"


@pytest.mark.asyncio
async def test_failover_chain_raises_when_all_excluded() -> None:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)
    with pytest.raises(LLMProviderUnavailable):
        await router.failover_chain(
            role_key="default",
            exclude=["deepseek", "yandexgpt", "gigachat"],
        )


@pytest.mark.asyncio
async def test_router_byok_model_routes_to_byok_proxy() -> None:
    byok_proxy = _make_provider("byok-openai")
    providers = {
        "deepseek": _make_provider("deepseek"),
        "byok-openai": byok_proxy,
    }
    circuits = {
        "deepseek": ProviderCircuit(provider="deepseek"),
        "byok-openai": ProviderCircuit(provider="byok-openai"),
    }
    router = LLMRouter(providers=providers, circuits=circuits)
    provider, model = await router.route(
        workspace_id=uuid4(),
        role_key="default",
        model_hint="byok-openai/gpt-4o",
    )
    assert provider is byok_proxy
    assert model == "gpt-4o"


@pytest.mark.asyncio
async def test_router_byok_provider_missing_raises() -> None:
    providers = {"deepseek": _make_provider("deepseek")}
    circuits = {"deepseek": ProviderCircuit(provider="deepseek")}
    router = LLMRouter(providers=providers, circuits=circuits)
    with pytest.raises(LLMProviderUnavailable):
        await router.route(
            workspace_id=uuid4(),
            role_key="default",
            model_hint="byok-openai/gpt-4o",
        )
