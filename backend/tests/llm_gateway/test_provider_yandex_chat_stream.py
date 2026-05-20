"""F-P5-4 partial: YandexGPT chat_stream SSE coverage.

Phase 00.5b Commit 7. Yandex uses newline-delimited JSON for streaming
(NDJSON-style on the v1 completion endpoint), not SSE `data:` prefix.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.yandex import YandexGPTProvider


class _PatchedYandexProvider(YandexGPTProvider):
    def __init__(self, *, transport: httpx.MockTransport, **kwargs: Any) -> None:
        super().__init__(
            iam_token="test-iam",
            catalog_id="test-folder",
            **kwargs,
        )
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:  # type: ignore[override]
        return httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._iam_token}",
                "x-folder-id": self._catalog_id,
                "Content-Type": "application/json",
            },
        )


def _ndjson_body(chunks: list[dict]) -> bytes:
    return ("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_yandex_chat_stream_parses_ndjson_chunks() -> None:
    """Streaming yields per-chunk result.alternatives[].message.text content."""
    chunks = [
        {
            "result": {
                "alternatives": [
                    {"message": {"text": "Привет"}, "status": "ALTERNATIVE_STATUS_PARTIAL"}
                ]
            }
        },
        {
            "result": {
                "alternatives": [
                    {"message": {"text": ", мир!"}, "status": "ALTERNATIVE_STATUS_FINAL"}
                ]
            }
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/foundationModels/v1/completion"
        body = json.loads(request.content)
        assert body["completionOptions"]["stream"] is True
        return httpx.Response(200, content=_ndjson_body(chunks))

    provider = _PatchedYandexProvider(transport=httpx.MockTransport(handler))
    received: list[str] = []
    async for resp in provider.chat_stream(
        LLMRequest(
            model="yandexgpt-pro",
            messages=[{"role": "user", "content": "Hello"}],
        )
    ):
        received.append(resp.content)

    assert received == ["Привет", ", мир!"]


@pytest.mark.asyncio
async def test_yandex_chat_stream_skips_empty_alternatives() -> None:
    """Chunks lacking alternatives are silently skipped (no crash)."""
    chunks: list[dict] = [
        {"result": {}},
        {
            "result": {
                "alternatives": [{"message": {"text": "ok"}, "status": "ALTERNATIVE_STATUS_FINAL"}]
            }
        },
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_ndjson_body(chunks))

    provider = _PatchedYandexProvider(transport=httpx.MockTransport(handler))
    received = [
        r.content
        async for r in provider.chat_stream(
            LLMRequest(model="yandexgpt-pro", messages=[{"role": "user", "content": "x"}])
        )
    ]
    assert received == ["ok"]


@pytest.mark.asyncio
async def test_yandex_chat_stream_skips_malformed_chunk() -> None:
    """Malformed JSON lines are skipped."""

    def handler(_: httpx.Request) -> httpx.Response:
        good = json.dumps(
            {
                "result": {
                    "alternatives": [
                        {"message": {"text": "fine"}, "status": "ALTERNATIVE_STATUS_FINAL"}
                    ]
                }
            }
        )
        body = (f"not-json\n{good}\n").encode()
        return httpx.Response(200, content=body)

    provider = _PatchedYandexProvider(transport=httpx.MockTransport(handler))
    received = [
        r.content
        async for r in provider.chat_stream(
            LLMRequest(model="yandexgpt-pro", messages=[{"role": "user", "content": "x"}])
        )
    ]
    assert received == ["fine"]
