"""Mocked YandexGPT provider tests via httpx MockTransport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from src.llm_gateway.providers.base import LLMRequest
from src.llm_gateway.providers.yandex import YandexGPTProvider

_FIXTURE = Path(__file__).parent / "fixtures" / "yandex_completion_response.json"


class _PatchedYandexProvider(YandexGPTProvider):
    def __init__(self, *, transport: httpx.MockTransport, **kwargs: Any) -> None:
        super().__init__(
            iam_token="test-iam-token",
            catalog_id="test-catalog",
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


@pytest.mark.asyncio
async def test_yandex_chat_returns_parsed_response() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/foundationModels/v1/completion")
        body = json.loads(request.content)
        assert body["modelUri"].startswith("gpt://test-catalog/")
        return httpx.Response(200, json=fixture)

    provider = _PatchedYandexProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat(
        LLMRequest(
            model="yandexgpt-pro",
            messages=[{"role": "user", "content": "Привет"}],
        )
    )
    assert "Здравствуйте" in resp.content
    assert resp.usage.tokens_input == 15
    assert resp.usage.tokens_output == 9


@pytest.mark.asyncio
async def test_yandex_embeddings_returns_vectors() -> None:
    embedding_payload = {"embedding": [0.1, 0.2, 0.3], "numTokens": "3"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/foundationModels/v1/textEmbedding")
        return httpx.Response(200, json=embedding_payload)

    provider = _PatchedYandexProvider(transport=httpx.MockTransport(handler))
    vectors = await provider.embeddings(["hello", "world"], model="text-search-doc")
    assert len(vectors) == 2
    assert vectors[0] == [0.1, 0.2, 0.3]
