"""YandexGPT provider — direct REST against Yandex Foundation Models.

Uses the Cloud Foundation Models v1 endpoint:
    POST https://llm.api.cloud.yandex.net/foundationModels/v1/completion
    POST https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding

Auth is hybrid (Api-Key preferred over IAM):
    * ``YANDEX_API_KEY`` set → ``Authorization: Api-Key <key>`` — a static key
      that does NOT expire (preferred).
    * else ``YANDEX_IAM_TOKEN`` set → ``Authorization: Bearer <token>`` — the
      legacy/failover scheme (~12h TTL, `yc iam create-token` rotation).
    * else → a clear config error at request time (router then fails over).
The catalog (folder) id is required for the modelUri.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.providers.base import LLMRequest, LLMResponse, LLMUsage

_logger = structlog.get_logger(__name__)


class YandexGPTProvider:
    """Yandex Foundation Models REST client."""

    name: str = "yandexgpt"

    def __init__(
        self,
        *,
        catalog_id: str,
        api_key: str | None = None,
        iam_token: str | None = None,
        base_url: str = "https://llm.api.cloud.yandex.net",
        timeout_seconds: float = 30.0,
    ) -> None:
        # Two auth schemes (Api-Key preferred — see _auth_header). Both optional
        # at construction: per the gateway convention the provider is built
        # unconditionally and fails at REQUEST time if no credential is set
        # (router_service then fails over to the next provider).
        self._api_key = api_key
        self._iam_token = iam_token
        self._catalog_id = catalog_id
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def _auth_header(self) -> str:
        """Authorization header value — Api-Key preferred over IAM Bearer.

        * ``api_key`` set → ``Api-Key <key>`` (static, non-expiring).
        * else ``iam_token`` set → ``Bearer <token>`` (legacy, ~12h TTL).
        * else → ``LLMProviderUnavailable`` (clear config error; the router's
          failover chain catches it and skips to the next provider).
        """
        if self._api_key:
            return f"Api-Key {self._api_key}"
        if self._iam_token:
            return f"Bearer {self._iam_token}"
        raise LLMProviderUnavailable(
            "yandexgpt: no credential configured — set YANDEX_API_KEY "
            "(Api-Key scheme, preferred) or YANDEX_IAM_TOKEN (Bearer)."
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Authorization": self._auth_header(),
                "x-folder-id": self._catalog_id,
                "Content-Type": "application/json",
            },
        )

    def _model_uri(self, model: str) -> str:
        # Yandex modelUri convention: gpt://<folder_id>/<model_name>/<version>.
        # If `model` already carries a version segment (contains "/", e.g.
        # "yandexgpt/rc" = YandexGPT 5.1 Pro), use it verbatim; otherwise
        # default to the stable "latest" alias (e.g. "yandexgpt" → 5 Pro).
        if "/" in model:
            return f"gpt://{self._catalog_id}/{model}"
        return f"gpt://{self._catalog_id}/{model}/latest"

    def _completion_body(self, req: LLMRequest, *, stream: bool) -> dict[str, Any]:
        return {
            "modelUri": self._model_uri(req.model),
            "completionOptions": {
                "stream": stream,
                "temperature": req.temperature,
                "maxTokens": str(req.max_tokens),
            },
            "messages": [{"role": m["role"], "text": m["content"]} for m in req.messages],
        }

    async def chat(self, req: LLMRequest) -> LLMResponse:
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/foundationModels/v1/completion",
                json=self._completion_body(req, stream=False),
            )
            resp.raise_for_status()
            payload = resp.json()

        # Yandex returns result.alternatives[].message.text + usage block.
        result = payload.get("result", {})
        alternatives = result.get("alternatives") or []
        first = alternatives[0] if alternatives else {}
        message = first.get("message", {})
        usage_block = result.get("usage", {})

        return LLMResponse(
            content=message.get("text", "") or "",
            finish_reason=first.get("status", "stop") or "stop",
            usage=LLMUsage(
                tokens_input=int(usage_block.get("inputTextTokens", 0)),
                tokens_output=int(usage_block.get("completionTokens", 0)),
            ),
            raw_provider_metadata={"provider": "yandexgpt", "model": req.model},
        )

    async def chat_stream(self, req: LLMRequest) -> AsyncIterator[LLMResponse]:
        async with (
            self._client() as client,
            client.stream(
                "POST",
                f"{self._base_url}/foundationModels/v1/completion",
                json=self._completion_body(req, stream=True),
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except ValueError:
                    _logger.warning("yandex.stream.malformed_chunk", raw=line)
                    continue
                result = chunk.get("result", {})
                alternatives = result.get("alternatives") or []
                if not alternatives:
                    continue
                msg = alternatives[0].get("message", {})
                yield LLMResponse(
                    content=msg.get("text", "") or "",
                    finish_reason=alternatives[0].get("status", "stop") or "stop",
                    raw_provider_metadata={"provider": "yandexgpt"},
                )

    async def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate 256-dim embeddings via /textEmbedding.

        Yandex requires one POST per text — batched in parallel via httpx.
        Standard models: ``text-search-doc`` and ``text-search-query``.
        """
        async with self._client() as client:
            vectors: list[list[float]] = []
            for text in texts:
                resp = await client.post(
                    f"{self._base_url}/foundationModels/v1/textEmbedding",
                    json={"modelUri": self._model_uri(model), "text": text},
                )
                resp.raise_for_status()
                payload = resp.json()
                emb = payload.get("embedding") or []
                vectors.append([float(x) for x in emb])
            return vectors

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/")
        except httpx.HTTPError as exc:
            _logger.info("yandex.health.unreachable", error=str(exc))
            return False
        return resp.status_code < 500
