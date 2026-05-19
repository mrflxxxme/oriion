"""Mocked DeepSeek provider tests via httpx MockTransport.

Uses httpx.MockTransport (built-in, no extra deps) so the unit suite runs
without `respx` / `pytest-httpx`. If/when those are added to pyproject by
the main agent, additional tests can be migrated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.deepseek import DeepSeekProvider

_FIXTURE = Path(__file__).parent / "fixtures" / "deepseek_chat_response.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


class _PatchedDeepSeekProvider(DeepSeekProvider):
    """Subclass that injects a MockTransport — keeps prod surface untouched."""

    def __init__(self, *, transport: httpx.MockTransport, **kwargs: Any) -> None:
        super().__init__(api_key="test-fake-key", **kwargs)
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:  # type: ignore[override]
        return httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )


@pytest.mark.asyncio
async def test_deepseek_chat_returns_parsed_response() -> None:
    fixture = _load_fixture()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "deepseek-chat"
        assert body["stream"] is False
        return httpx.Response(200, json=fixture)

    provider = _PatchedDeepSeekProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat(
        LLMRequest(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Привет"}],
        )
    )
    assert resp.content == "Привет! Чем могу помочь?"
    assert resp.usage.tokens_input == 12
    assert resp.usage.tokens_output == 8
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_deepseek_chat_raises_on_5xx() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "service unavailable"})

    provider = _PatchedDeepSeekProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await provider.chat(
            LLMRequest(model="deepseek-chat", messages=[{"role": "user", "content": "x"}])
        )


@pytest.mark.asyncio
async def test_deepseek_embeddings_not_implemented() -> None:
    provider = DeepSeekProvider(api_key="x")
    with pytest.raises(NotImplementedError):
        await provider.embeddings(["x"], model="text-embedding-3-small")
