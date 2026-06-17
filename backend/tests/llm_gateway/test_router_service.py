"""Unit tests for LLMRouter — circuit-skip + failover chain."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from src.llm_gateway.circuit_breaker import CircuitState, ProviderCircuit
from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.providers.base import LLMResponse, LLMUsage
from src.llm_gateway.services.router_service import LLMRouter, provider_forwards_tools


def _make_provider(name: str) -> AsyncMock:
    p = AsyncMock()
    p.name = name
    return p


def _ds_response() -> LLMResponse:
    return LLMResponse(
        content="ok",
        finish_reason="stop",
        usage=LLMUsage(tokens_input=1, tokens_output=1),
    )


_TOOLS = [{"type": "function", "function": {"name": "web_search", "parameters": {}}}]


@pytest.mark.asyncio
async def test_acomplete_forwards_max_tokens_to_provider() -> None:
    """AC-W1-23a: the per-role max_tokens reaches the provider's LLMRequest."""
    provider = _make_provider("deepseek")
    providers = {
        "deepseek": provider,
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    router = LLMRouter(providers=providers, circuits=circuits)

    await router.acomplete(
        workspace_id=uuid4(),
        role_key="writer",
        model_hint=None,
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8192,
    )

    sent_request = provider.chat.await_args.args[0]
    assert sent_request.max_tokens == 8192


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


# ── native tool-call gating (ADR-035 / AC-W1-19) ──────────────────────────


def test_provider_forwards_tools_only_deepseek() -> None:
    assert provider_forwards_tools("deepseek") is True
    assert provider_forwards_tools("yandexgpt") is False
    assert provider_forwards_tools("gigachat") is False


def _three_providers() -> tuple[dict[str, AsyncMock], dict[str, ProviderCircuit]]:
    providers = {
        "deepseek": _make_provider("deepseek"),
        "yandexgpt": _make_provider("yandexgpt"),
        "gigachat": _make_provider("gigachat"),
    }
    circuits = {slug: ProviderCircuit(provider=slug) for slug in providers}
    return providers, circuits


@pytest.mark.asyncio
async def test_would_use_native_tools_true_when_deepseek_active() -> None:
    providers, circuits = _three_providers()
    router = LLMRouter(providers=providers, circuits=circuits)
    assert router.would_use_native_tools("researcher") is True


@pytest.mark.asyncio
async def test_would_use_native_tools_false_on_deepseek_open_failover() -> None:
    """DeepSeek circuit OPEN → the role would run on YandexGPT → no native tools."""
    providers, circuits = _three_providers()
    circuits["deepseek"] = ProviderCircuit(
        provider="deepseek",
        state=CircuitState.OPEN,
        opened_at=datetime.now(UTC),
        cooldown_seconds=60,
    )
    router = LLMRouter(providers=providers, circuits=circuits)
    assert router.would_use_native_tools("researcher") is False


@pytest.mark.asyncio
async def test_would_use_native_tools_false_for_byok() -> None:
    providers, circuits = _three_providers()
    router = LLMRouter(providers=providers, circuits=circuits)
    assert router.would_use_native_tools("researcher", model_hint="byok-openai/gpt-4o") is False


@pytest.mark.asyncio
async def test_acomplete_forwards_tools_to_deepseek() -> None:
    providers, circuits = _three_providers()
    providers["deepseek"].chat = AsyncMock(return_value=_ds_response())
    router = LLMRouter(providers=providers, circuits=circuits)

    _resp, _model, slug = await router.acomplete(
        workspace_id=uuid4(),
        role_key="researcher",
        model_hint=None,
        messages=[{"role": "user", "content": "x"}],
        tools=_TOOLS,
    )
    assert slug == "deepseek"
    sent = providers["deepseek"].chat.await_args.args[0]
    assert sent.tools == _TOOLS


@pytest.mark.asyncio
async def test_acomplete_drops_tools_on_failover_to_yandex() -> None:
    """DeepSeek errors → failover to YandexGPT, which must NOT receive tools
    (it would ignore them and stall the loop — ADR-035)."""
    providers, circuits = _three_providers()
    providers["deepseek"].chat = AsyncMock(side_effect=httpx.ConnectError("down"))
    providers["yandexgpt"].chat = AsyncMock(return_value=_ds_response())
    router = LLMRouter(providers=providers, circuits=circuits)

    _resp, _model, slug = await router.acomplete(
        workspace_id=uuid4(),
        role_key="researcher",
        model_hint=None,
        messages=[{"role": "user", "content": "x"}],
        tools=_TOOLS,
    )
    assert slug == "yandexgpt"
    # DeepSeek (the first candidate) DID receive the tools…
    assert providers["deepseek"].chat.await_args.args[0].tools == _TOOLS
    # …but the YandexGPT failover did not.
    assert providers["yandexgpt"].chat.await_args.args[0].tools is None


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
