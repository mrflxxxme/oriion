"""Typed exceptions for the Wave-1 connector clients (Phase 01.9b, ADR-041).

All subclass ``mcp.exceptions.MCPError`` so the connector NativeTool closures can
degrade the whole family with a single ``except MCPError`` (mirroring
``web_search_runner``), and the eventual FastAPI handler surfaces
``application/problem+json`` without bespoke mapping.

SECURITY: ``ConnectorDlpBlocked`` carries the detected PII *category labels only*
(e.g. ``inn``, ``phone``) — NEVER the matched raw value. The value never leaves
the detector, so it cannot leak through a log, audit payload, or refusal string.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.mcp.exceptions import MCPError


class ConnectorError(MCPError):
    """A connector call failed (transport, parse, or upstream error)."""

    code = "mcp.connector.error"
    status_code = 502
    title = "Connector error"


class ConnectorNotConfigured(ConnectorError):
    """No credential is configured for the connector in this workspace.

    The connector degrades to a clear "not configured" result rather than
    crashing — the workspace owner has simply not connected the account yet.
    """

    code = "mcp.connector.not_configured"
    status_code = 400
    title = "Connector not configured"


class ConnectorSendDisabled(ConnectorError):
    """Autonomous outward SEND is denied until the approval UI (01.12).

    The ``send_*`` tools are ALSO capability-classified DANGEROUS, so the gate
    denies them before they are ever attached to an agent — this guarded stub is
    belt-and-suspenders so a direct call can never perform a real send.
    """

    code = "mcp.connector.send_disabled"
    status_code = 403
    title = "Connector send disabled (deny-until-01.12)"


class ConnectorDlpBlocked(ConnectorError):
    """Outgoing tool-call arguments carried RU-PDN — the external call was blocked.

    The exfiltration guard (ADR-041, ADR-039 D10): every connector screens its
    outgoing args through the 01.6 DLP detector BEFORE any external call. A hit
    raises this; the NativeTool closure degrades it to a safe refusal.

    SECURITY: ``categories`` holds category labels only — never the raw value.
    """

    code = "mcp.connector.dlp_blocked"
    status_code = 422
    title = "Connector call blocked by DLP"

    def __init__(self, categories: Sequence[str]) -> None:
        self.categories: tuple[str, ...] = tuple(categories)
        joined = ", ".join(self.categories) if self.categories else "unspecified"
        super().__init__(f"connector call blocked: PII in outgoing args: {joined}")


__all__ = [
    "ConnectorDlpBlocked",
    "ConnectorError",
    "ConnectorNotConfigured",
    "ConnectorSendDisabled",
]
