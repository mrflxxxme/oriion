"""DLP output guard — A3 hard-block (ADR-039).

Screens a task's final deliverable for RU-PDN. On a hit it writes one audit row
via the injected ``AuditSink`` port (category labels + count only — never the raw
value) and raises ``DlpViolation`` so the runtime stamps ``task.failed``. A clean
deliverable is a no-op (no audit, no raise).

The guard is pure logic over injected ports, so unit tests exercise the full
block path with a fake sink — no DB. The real ``AuditSink`` adapter (wrapping
``audit.emit_audit_event``) + the settings-gated wiring live in
``runtime.security_guardrails``.
"""

from __future__ import annotations

from uuid import UUID

from src.security.detectors.pii import default_pii_detector
from src.security.exceptions import DlpViolation
from src.security.ports import AuditSink, PiiDetector


class DlpGuard:
    """A3 output DLP hard-block over injected detector + audit ports."""

    def __init__(
        self,
        *,
        audit: AuditSink,
        detector: PiiDetector = default_pii_detector,
    ) -> None:
        self._audit = audit
        self._detector = detector

    async def screen(
        self,
        text: str,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
    ) -> None:
        """Raise ``DlpViolation`` (after auditing) if ``text`` contains RU-PDN."""
        result = self._detector.scan(text)
        if not result.has_pii:
            return
        categories = result.categories
        await self._audit.record_dlp_block(
            task_id=task_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            categories=categories,
            finding_count=len(result.findings),
        )
        raise DlpViolation(categories)
