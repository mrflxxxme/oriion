"""Unit: llm_gateway.providers.byok_proxy — parse + transport branches.

Covers ``parse_byok_model``, the BYOKProxyProvider constructor's
upstream-provider validation, plus chat/embeddings/health_check via
httpx.MockTransport (mirrors the pattern in test_provider_deepseek_mock).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.byok_proxy import (
    BYOKProxyProvider,
    parse_byok_model,
)


def _patched_proxy(
    transport: httpx.MockTransport,
    *,
    plaintext_key: str = "sk-test-byok",  # gitleaks:allow
    upstream: str = "openai",
) -> BYOKProxyProvider:
    """Build a BYOKProxyProvider that uses MockTransport instead of net I/O."""

    class _Patched(BYOKProxyProvider):
        def _client(self) -> httpx.AsyncClient:  # type: ignore[override]
            return httpx.AsyncClient(
                transport=transport,
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": "application/json",
                },
            )

    return _Patched(plaintext_key=plaintext_key, upstream_provider_slug=upstream)


# ── parse_byok_model ─────────────────────────────────────────────────────


def test_parse_byok_model_happy_path() -> None:
    assert parse_byok_model("byok-openai/gpt-4o") == ("openai", "gpt-4o")
    assert parse_byok_model("byok-anthropic/claude-3") == ("anthropic", "claude-3")


def test_parse_byok_model_missing_prefix_raises() -> None:
    with pytest.raises(ValueError, match="not a BYOK model spec"):
        parse_byok_model("openai/gpt-4o")


def test_parse_byok_model_missing_slash_raises() -> None:
    with pytest.raises(ValueError, match="byok-<provider>/<model>"):
        parse_byok_model("byok-openai")


# ── Construction ─────────────────────────────────────────────────────────


def test_unknown_upstream_provider_raises() -> None:
    with pytest.raises(ValueError, match="not supported"):
        BYOKProxyProvider(
            plaintext_key="sk-x",  # gitleaks:allow
            upstream_provider_slug="lovable-fake-provider",
        )


def test_base_url_override_bypasses_known_map() -> None:
    provider = BYOKProxyProvider(
        plaintext_key="sk-x",  # gitleaks:allow
        upstream_provider_slug="lovable-fake-provider",
        base_url_override="https://example.com/v9",
    )
    assert provider._base_url == "https://example.com/v9"


# ── chat / embeddings / health_check via MockTransport ───────────────────


@pytest.mark.asyncio
async def test_chat_parses_openai_shape() -> None:
    fixture: dict[str, Any] = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "Hello!", "tool_calls": None},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json=fixture)

    provider = _patched_proxy(httpx.MockTransport(handler))
    resp = await provider.chat(
        LLMRequest(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
    )
    assert resp.content == "Hello!"
    assert resp.usage.tokens_input == 5
    assert resp.usage.tokens_output == 3
    assert resp.raw_provider_metadata["provider"] == "byok-openai"


@pytest.mark.asyncio
async def test_chat_raises_on_5xx() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"error": "bad gateway"})

    provider = _patched_proxy(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await provider.chat(LLMRequest(model="gpt-4o", messages=[{"role": "user", "content": "x"}]))


@pytest.mark.asyncio
async def test_embeddings_parses_vector_data() -> None:
    fixture: dict[str, Any] = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3]},
            {"embedding": [0.4, 0.5, 0.6]},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/embeddings")
        return httpx.Response(200, json=fixture)

    provider = _patched_proxy(httpx.MockTransport(handler))
    vectors = await provider.embeddings(["one", "two"], model="text-embedding-3-small")
    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


@pytest.mark.asyncio
async def test_health_check_reachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models")
        return httpx.Response(200, json={"data": []})

    provider = _patched_proxy(httpx.MockTransport(handler))
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_health_check_5xx_returns_false() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    provider = _patched_proxy(httpx.MockTransport(handler))
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_health_check_transport_error_returns_false() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("DNS failure (mock)")

    provider = _patched_proxy(httpx.MockTransport(handler))
    assert await provider.health_check() is False
