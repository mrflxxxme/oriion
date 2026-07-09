"""Outgoing-args DLP screen — the connector exfiltration guard (Phase 01.9b).

Every connector runs this over its outgoing tool-call arguments (query / path /
mailbox / draft text) BEFORE any external call. A PII hit raises
``ConnectorDlpBlocked`` so the external call never happens — this is the R-05
exfiltration control (ADR-041, ADR-039 D10: DLP-before-connectors).

This REUSES the 01.6 detection seam (``security.detectors.pii.default_pii_detector``)
verbatim — no detection logic is reimplemented here. Swapping in the layer-A ML
detector later is a one-line change (any ``PiiDetector`` impl).

SECURITY: only ``(category, span)`` findings ever leave the detector; the raw
matched substring is never carried, logged, or raised.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import structlog

from src.mcp.tools.connectors.exceptions import ConnectorDlpBlocked
from src.security.detectors.pii import default_pii_detector
from src.security.ports import PiiDetector

logger = structlog.get_logger(__name__)


class ConnectorDlpScreen(Protocol):
    """Screen outgoing connector args for RU-PDN; raise on a hit."""

    async def screen(self, args: Sequence[str], *, connector_slug: str, tool_name: str) -> None: ...


class PiiConnectorDlpScreen:
    """Deterministic outgoing-args screen over the injected ``PiiDetector``.

    Defaults to the shared 01.6 ``default_pii_detector`` — the exact same
    regex+checksum RU-PDN detector the output DLP guard uses, so a connector call
    and a final deliverable are screened by one source of truth.
    """

    def __init__(self, detector: PiiDetector = default_pii_detector) -> None:
        self._detector = detector

    async def screen(self, args: Sequence[str], *, connector_slug: str, tool_name: str) -> None:
        """Raise ``ConnectorDlpBlocked`` if any arg carries RU-PDN.

        The args are joined with newlines so a checksum-valid ИНН keeps its
        line-local labelling context (the 01.9a INN-10 precision gate reads the
        run's physical line). Empty/blank args are a no-op.
        """
        joined = "\n".join(arg for arg in args if arg)
        if not joined.strip():
            return
        result = self._detector.scan(joined)
        if not result.has_pii:
            return
        # SECURITY: category labels only — never the raw matched value.
        logger.warning(
            "mcp.connector.dlp_blocked",
            connector_slug=connector_slug,
            tool_name=tool_name,
            categories=result.categories,
        )
        raise ConnectorDlpBlocked(result.categories)


default_connector_dlp_screen: ConnectorDlpScreen = PiiConnectorDlpScreen()


__all__ = [
    "ConnectorDlpScreen",
    "PiiConnectorDlpScreen",
    "default_connector_dlp_screen",
]
