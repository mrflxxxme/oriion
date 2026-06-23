"""Deterministic test doubles for the memory domain (no network / no live key).

``DeterministicEmbedder`` returns the SAME 256-dim vector for a given text via a
sha256 expansion, so ``embed_query(t) == embed_documents([t])[0]`` — exact-match
recall is reproducible, which is what the pgvector round-trip plumbing test
needs (semantic quality is covered by the optional @live Yandex test).
"""

from __future__ import annotations

import hashlib

from src.memory.exceptions import EmbeddingUnavailable
from src.memory.models import MEMORY_EMBEDDING_DIM


class DeterministicEmbedder:
    """Same text → same vector. Records calls for assertions."""

    def __init__(self, dim: int = MEMORY_EMBEDDING_DIM) -> None:
        self._dim = dim
        self.embed_documents_calls: list[list[str]] = []
        self.embed_query_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return "fake/deterministic-256"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls.append(list(texts))
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls.append(text)
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        return [seed[i % len(seed)] / 255.0 for i in range(self._dim)]


class FailingEmbedder:
    """Embedder that always raises EmbeddingUnavailable (error-path coverage)."""

    @property
    def model_name(self) -> str:
        return "fake/failing"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailable("fake embedder is down")

    async def embed_query(self, text: str) -> list[float]:
        raise EmbeddingUnavailable("fake embedder is down")
