"""Memory bounded-context exceptions.

Carry ``code`` / ``status_code`` / ``title`` mirroring ``billing.exceptions``
so the API error mapper and the orchestrator's generic failure handler
(``getattr(exc, "code", ...)``) treat them uniformly.
"""

from __future__ import annotations


class MemoryError(Exception):
    """Base for all memory-domain errors."""

    code: str = "memory.error"
    status_code: int = 500
    title: str = "Memory error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class MemoryEntryNotFound(MemoryError):
    """A referenced cell/role memory entry id is absent (404)."""

    code = "memory.entry_not_found"
    status_code = 404
    title = "Memory entry not found"

    def __init__(self, entry_id: str) -> None:
        super().__init__(f"memory entry not found: {entry_id}")
        self.entry_id = entry_id


class EmbeddingUnavailable(MemoryError):
    """The embedding provider failed/returned an empty vector (503).

    Surfaced when a store/search needs a real embedding but the gateway is
    unavailable. Distinct from a validation error so callers can retry.
    """

    code = "memory.embedding_unavailable"
    status_code = 503
    title = "Embedding provider unavailable"
