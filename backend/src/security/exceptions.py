"""Security bounded-context exceptions.

Carry ``code`` / ``status_code`` / ``title`` mirroring ``memory.exceptions`` /
``artifacts.exceptions`` so the RFC-7807 handler in ``src.main`` and generic
failure handlers (``getattr(exc, "code", ...)`` in ``runtime.orchestrator``)
treat them uniformly.
"""

from __future__ import annotations

from collections.abc import Sequence


class SecurityError(Exception):
    """Base for all security-domain errors."""

    code: str = "security.error"
    status_code: int = 500
    title: str = "Security error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class DlpViolation(SecurityError):
    """Output blocked by the DLP guard — PII detected in the deliverable (A3).

    SECURITY: the message + the ``categories`` attribute carry the detected PII
    *category labels only* (e.g. ``inn``, ``snils``) — NEVER the matched raw
    value. The runtime failure handler echoes ``str(exc)`` into the ``task.failed``
    SSE frame, so leaking a value here would leak it to the client.
    """

    code = "security.dlp.blocked"
    status_code = 422
    title = "Output blocked by DLP"

    def __init__(self, categories: Sequence[str]) -> None:
        self.categories: tuple[str, ...] = tuple(categories)
        joined = ", ".join(self.categories) if self.categories else "unspecified"
        super().__init__(f"output blocked: detected PII categories: {joined}")
