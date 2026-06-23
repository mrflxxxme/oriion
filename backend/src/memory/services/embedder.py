"""Embedder port over the LLM gateway (256-dim YandexGPT, ADR-011 Q1).

The port is the single seam the memory services depend on, so unit/integration
tests inject a deterministic fake (no live key in CI) while production wires the
real ``GatewayEmbedder``. SECURITY: this layer NEVER logs input text or vectors.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from src.llm_gateway.providers.base import LLMProvider
from src.llm_gateway.services.router_service import LLMRouter
from src.memory.exceptions import EmbeddingUnavailable

_EMBEDDER_ROLE_KEY = "embedder"
# YandexGPT uses an asymmetric pair in the SAME 256-dim space: documents are
# embedded with text-search-doc, queries with text-search-query.
_YANDEX_DOC_MODEL = "text-search-doc"
_YANDEX_QUERY_MODEL = "text-search-query"


@runtime_checkable
class Embedder(Protocol):
    """Minimal embedding seam consumed by the memory services."""

    @property
    def model_name(self) -> str:
        """Stable label persisted in ``embedding_model`` (e.g. provider/model)."""
        ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed stored documents (one vector per text, in order)."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a search query (asymmetric model where the provider supports it)."""
        ...


class GatewayEmbedder:
    """Real embedder — routes ``role_key='embedder'`` to YandexGPT embeddings.

    Failover note: the embedder role's chain starts at yandexgpt; if its circuit
    is open the router returns a chat-only provider whose ``embeddings()`` raises
    NotImplementedError — surfaced here as :class:`EmbeddingUnavailable` (503),
    never a silent wrong-dimension vector.
    """

    def __init__(self, router: LLMRouter, *, workspace_id: UUID) -> None:
        self._router = router
        self._workspace_id = workspace_id

    @property
    def model_name(self) -> str:
        return f"yandexgpt/{_YANDEX_DOC_MODEL}"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        provider, doc_model = await self._resolve()
        return await self._embed(provider, texts, doc_model)

    async def embed_query(self, text: str) -> list[float]:
        provider, doc_model = await self._resolve()
        query_model = _YANDEX_QUERY_MODEL if doc_model == _YANDEX_DOC_MODEL else doc_model
        vectors = await self._embed(provider, [text], query_model)
        return vectors[0]

    async def _resolve(self) -> tuple[LLMProvider, str]:
        return await self._router.route(
            workspace_id=self._workspace_id,
            role_key=_EMBEDDER_ROLE_KEY,
            model_hint=None,
        )

    @staticmethod
    async def _embed(provider: LLMProvider, texts: list[str], model: str) -> list[list[float]]:
        try:
            vectors = await provider.embeddings(texts, model)
        except NotImplementedError as exc:
            raise EmbeddingUnavailable(
                f"provider {provider.name!r} exposes no embeddings endpoint"
            ) from exc
        if len(vectors) != len(texts) or any(not v for v in vectors):
            raise EmbeddingUnavailable("embedding provider returned an empty/short result")
        return vectors


def build_gateway_embedder(router: LLMRouter, *, workspace_id: UUID) -> GatewayEmbedder:
    """Construct the production embedder bound to a workspace's routing."""
    return GatewayEmbedder(router, workspace_id=workspace_id)
