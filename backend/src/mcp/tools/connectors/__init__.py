"""Wave-1 first-party connectors (read + draft only) — Phase 01.9b, ADR-041.

Native-tool connector clients mirroring ``WebSearchTool`` / ``ReadURLTool``:
telegram-bot (Bot-API), yandex-disk (REST), imap-smtp (IMAP). Each is
rate-limited, screens its outgoing args through the 01.6 DLP detector (exfil
guard), reads KMS-at-rest credentials via ``connector_credential_service``, and
degrades gracefully. Autonomous SEND is a DANGEROUS-classified guarded stub
(deny-until-approval-UI 01.12). Wired to agents through
``runtime.connectors_runner`` → ``dispatch.build_leaf_runner`` → the capability
gate.
"""

from __future__ import annotations

from src.mcp.tools.connectors.base import (
    BaseConnector,
    ConnectorAuditSink,
    HttpResponse,
    HttpTransport,
    HttpxTransport,
    NoopConnectorAuditSink,
)
from src.mcp.tools.connectors.dlp_screen import (
    ConnectorDlpScreen,
    PiiConnectorDlpScreen,
    default_connector_dlp_screen,
)
from src.mcp.tools.connectors.exceptions import (
    ConnectorDlpBlocked,
    ConnectorError,
    ConnectorNotConfigured,
    ConnectorSendDisabled,
)
from src.mcp.tools.connectors.imap_smtp import ImapMessage, ImapSmtpConnector, ImapTransport
from src.mcp.tools.connectors.telegram_bot import TelegramBotConnector, TelegramMessage
from src.mcp.tools.connectors.yandex_disk import DiskItem, YandexDiskConnector

__all__ = [
    "BaseConnector",
    "ConnectorAuditSink",
    "ConnectorDlpBlocked",
    "ConnectorDlpScreen",
    "ConnectorError",
    "ConnectorNotConfigured",
    "ConnectorSendDisabled",
    "DiskItem",
    "HttpResponse",
    "HttpTransport",
    "HttpxTransport",
    "ImapMessage",
    "ImapSmtpConnector",
    "ImapTransport",
    "NoopConnectorAuditSink",
    "PiiConnectorDlpScreen",
    "TelegramBotConnector",
    "TelegramMessage",
    "YandexDiskConnector",
    "default_connector_dlp_screen",
]
