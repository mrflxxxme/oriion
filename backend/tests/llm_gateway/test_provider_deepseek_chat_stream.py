"""F-P5-4 partial: DeepSeek chat_stream SSE coverage.

Phase 00.5b Commit 7. Validates that DeepSeekProvider.chat_stream()
correctly parses SSE-formatted incremental chunks (`data: {...}` lines
terminated by `data: [DONE]`).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.deepseek import DeepSeekProvider


class _PatchedDeepSeekProvider(DeepSeekProvider):
    """Override _client() to inject MockTransport for httpx streaming."""

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


def _sse_body(chunks: list[dict]) -> bytes:
    lines: list[str] = []
    for chunk in chunks:
        import json

        lines.append(f"data: {json.dumps(chunk, ensure_ascii=False)}")
    lines.append("data: [DONE]")
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_deepseek_chat_stream_parses_sse_chunks() -> None:
    """Streaming yields one LLMResponse per `data:` line; [DONE] ends."""
    chunks = [
        {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": ", "}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "world!"}, "finish_reason": "stop"}]},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        import json

        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(
            200,
            content=_sse_body(chunks),
            headers={"Content-Type": "text/event-stream"},
        )

    provider = _PatchedDeepSeekProvider(transport=httpx.MockTransport(handler))
    received: list[str] = []
    finish_reason: str | None = None
    async for resp in provider.chat_stream(
        LLMRequest(model="deepseek-chat", messages=[{"role": "user", "content": "hi"}])
    ):
        received.append(resp.content)
        finish_reason = resp.finish_reason

    assert received == ["Hello", ", ", "world!"]
    assert finish_reason == "stop"


@pytest.mark.asyncio
async def test_deepseek_chat_stream_skips_non_data_lines() -> None:
    """SSE keepalive (`:keepalive`) and non-`data:` lines are skipped."""

    def handler(_: httpx.Request) -> httpx.Response:
        body = (
            ":keepalive\n"
            "\n"
            'data: {"choices": [{"delta": {"content": "ok"}, "finish_reason": null}]}\n'
            "data: [DONE]\n"
        )
        return httpx.Response(200, content=body.encode("utf-8"))

    provider = _PatchedDeepSeekProvider(transport=httpx.MockTransport(handler))
    received = [
        r.content
        async for r in provider.chat_stream(
            LLMRequest(model="deepseek-chat", messages=[{"role": "user", "content": "x"}])
        )
    ]
    assert received == ["ok"]


@pytest.mark.asyncio
async def test_deepseek_chat_stream_handles_malformed_chunk() -> None:
    """Malformed JSON chunks are skipped (logged warning, no crash)."""

    def handler(_: httpx.Request) -> httpx.Response:
        body = (
            "data: not-json-at-all\n"
            'data: {"choices": [{"delta": {"content": "fine"}, "finish_reason": "stop"}]}\n'
            "data: [DONE]\n"
        )
        return httpx.Response(200, content=body.encode("utf-8"))

    provider = _PatchedDeepSeekProvider(transport=httpx.MockTransport(handler))
    received = [
        r.content
        async for r in provider.chat_stream(
            LLMRequest(model="deepseek-chat", messages=[{"role": "user", "content": "x"}])
        )
    ]
    assert received == ["fine"]
