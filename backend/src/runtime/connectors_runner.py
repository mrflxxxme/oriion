"""Connector native-tool builders (mirror ``web_search_runner``) — Phase 01.9b.

Builds the connector ``NativeTool`` closures (single ``str`` in, ``str`` out) from
a workspace/cell context + the ``connector_credential_service``, so the read/draft
connectors can reach agents through the capability gate
(``dispatch.build_leaf_runner`` → ``gate_agent_tools``). The candidate map this
returns is what pass B's gate scopes per archetype: a connector attaches only when
the agent's ``agent_archetypes.tools_allowed`` lists it, and DANGEROUS ``send_*``
tools are never built here (the gate denies them regardless).

Each closure:
  * resolves the workspace's active credential lazily
    (``list_active_credentials`` → ``get_credential_plaintext``); no credential →
    a clear "connector not configured" degrade string (never a crash);
  * runs the outgoing-args DLP screen INSIDE the connector (the exfil guard);
    a PII hit is audited then degraded to a safe refusal (never raised to the
    agent);
  * emits an ``audit.audit_log`` row on every external call (AC-01.9b.7);
  * degrades any other typed ``MCPError`` to a short note so the agent never
    hard-fails (matching web_search/read_url).

Autonomous SEND stays a DANGEROUS-classified guarded stub — never exposed here.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.audit.services.audit_service import emit_audit_event
from src.llm_gateway.exceptions import KMSError
from src.llm_gateway.services.kms_provider import KMSProvider, get_kms_provider
from src.mcp.exceptions import MCPError
from src.mcp.services.connector_credential_service import (
    get_credential_plaintext,
    list_active_credentials,
)
from src.mcp.tools.connectors import imap_smtp, telegram_bot, yandex_disk
from src.mcp.tools.connectors.base import ConnectorAuditSink, HttpTransport, redact_secrets
from src.mcp.tools.connectors.dlp_screen import (
    ConnectorDlpScreen,
    default_connector_dlp_screen,
)
from src.mcp.tools.connectors.exceptions import (
    ConnectorDlpBlocked,
    ConnectorNotConfigured,
)
from src.mcp.tools.connectors.imap_smtp import ImapSmtpConnector, ImapTransport
from src.mcp.tools.connectors.telegram_bot import TelegramBotConnector, TelegramMessage
from src.mcp.tools.connectors.yandex_disk import DiskItem, YandexDiskConnector

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.mcp.tools.rate_limit import ToolRateLimiter

logger = structlog.get_logger(__name__)

NativeTool = Callable[[str], Awaitable[str]]

# Fixed synthetic actor for connector-originated audit rows (an external call /
# DLP block is a system action, not a user action). Stable so audit queries can
# filter on it.
CONNECTOR_ACTOR_ID = UUID("5ec00000-0000-0000-0000-00000000c0de")
EXTERNAL_CALL_ACTION = "mcp.connector.external_call"
DLP_BLOCK_ACTION = "security.connector.dlp_blocked"

# Degrade strings (RU — user-facing agent surface).
_NOT_CONFIGURED_MSG = "Коннектор {slug} не настроен для рабочего пространства."
_DLP_REFUSAL_MSG = "Запрос отклонён DLP: во входных данных обнаружены персональные данные ({cats})."


class EmitConnectorAuditSink:
    """Real ``ConnectorAuditSink`` — INSERTs audit rows via ``emit_audit_event``.

    Writes on the caller's session (no commit). SECURITY: the payload carries the
    connector slug + tool name + agent id + outcome / category labels only —
    never a tool argument, credential, or raw PII value.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        task_id: UUID | None = None,
        cell_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> None:
        self._session = session
        self._task_id = task_id
        self._cell_id = cell_id
        self._workspace_id = workspace_id

    async def record_external_call(
        self, *, connector_slug: str, tool_name: str, agent_id: str, outcome: str
    ) -> None:
        await emit_audit_event(
            actor_type="system",
            actor_id=CONNECTOR_ACTOR_ID,
            action=EXTERNAL_CALL_ACTION,
            resource_type="task",
            resource_id=self._task_id,
            payload={
                "connector_slug": connector_slug,
                "tool_name": tool_name,
                "agent_id": agent_id,
                "outcome": outcome,
            },
            session=self._session,
            workspace_id=self._workspace_id,
            cell_id=self._cell_id,
        )

    async def record_dlp_block(
        self,
        *,
        connector_slug: str,
        tool_name: str,
        agent_id: str,
        categories: tuple[str, ...],
    ) -> None:
        await emit_audit_event(
            actor_type="system",
            actor_id=CONNECTOR_ACTOR_ID,
            action=DLP_BLOCK_ACTION,
            resource_type="task",
            resource_id=self._task_id,
            payload={
                "connector_slug": connector_slug,
                "tool_name": tool_name,
                "agent_id": agent_id,
                "categories": list(categories),
            },
            session=self._session,
            workspace_id=self._workspace_id,
            cell_id=self._cell_id,
        )


async def _resolve_credential(
    session: AsyncSession,
    kms: KMSProvider,
    *,
    workspace_id: UUID,
    connector_slug: str,
) -> str | None:
    """Return the newest active credential plaintext for the connector, or None.

    Newest-first (``list_active_credentials`` orders by ``created_at`` desc). A
    workspace that has not connected the account yields None → the connector
    degrades to "not configured".

    A ``KMSError`` (e.g. a tampered ``cred_encrypted`` → AES-GCM ``InvalidTag``)
    is caught and degraded to None too: ``KMSError`` subclasses
    ``LLMGatewayException`` (NOT ``MCPError``), so it would otherwise escape the
    tool closure's ``except MCPError`` and crash the delegation. Degrading here
    keeps the connector safe (no plaintext, no crash) — same "not configured"
    result surface.
    """
    rows = await list_active_credentials(session, workspace_id=workspace_id)
    for row in rows:
        if row.connector_slug == connector_slug:
            try:
                _row, plaintext = await get_credential_plaintext(
                    session, kms, credential_id=row.id, workspace_id=workspace_id
                )
            except KMSError:
                logger.warning(
                    "mcp.connector.credential_decrypt_failed",
                    connector_slug=connector_slug,
                    workspace_id=str(workspace_id),
                )
                return None
            return plaintext
    return None


def _format_telegram(messages: list[TelegramMessage]) -> str:
    if not messages:
        return "Сообщений не найдено."
    lines = ["## Последние сообщения Telegram:"]
    for i, m in enumerate(messages, start=1):
        lines.append(f"{i}. [{m.chat}] {m.text}")
    return "\n".join(lines)


def _format_disk_items(items: list[DiskItem]) -> str:
    if not items:
        return "Папка пуста или не найдена."
    lines = ["## Содержимое папки Яндекс.Диска:"]
    for item in items:
        lines.append(f"- {item.name} ({item.type}, {item.size} B) — {item.path}")
    return "\n".join(lines)


def _format_inbox(messages: list[imap_smtp.ImapMessage]) -> str:
    if not messages:
        return "Входящих сообщений не найдено."
    lines = ["## Последние письма (входящие):"]
    for i, m in enumerate(messages, start=1):
        lines.append(f"{i}. От: {m.sender} | Тема: {m.subject}\n   {m.snippet}")
    return "\n".join(lines)


def build_connector_tools(
    *,
    session: AsyncSession,
    workspace_id: UUID,
    task_id: UUID | None = None,
    cell_id: UUID | None = None,
    kms: KMSProvider | None = None,
    rate_limiter: ToolRateLimiter | None = None,
    dlp_screen: ConnectorDlpScreen = default_connector_dlp_screen,
    audit_sink: ConnectorAuditSink | None = None,
    agent_id: str = "system",
    telegram_transport: HttpTransport | None = None,
    yandex_transport: HttpTransport | None = None,
    imap_transport: ImapTransport | None = None,
) -> dict[str, NativeTool]:
    """Build the connector NativeTool candidate map for a workspace.

    The returned ``{name: callable}`` map is what ``build_leaf_runner`` threads
    through ``gate_agent_tools`` — the gate scopes it per archetype and drops any
    DANGEROUS tool. SEND tools are intentionally absent (deny-until-01.12).
    """
    resolved_kms = kms or get_kms_provider()
    audit: ConnectorAuditSink = audit_sink or EmitConnectorAuditSink(
        session, task_id=task_id, cell_id=cell_id, workspace_id=workspace_id
    )

    async def _degrade(exc: MCPError, *, slug: str, tool_name: str) -> str:
        if isinstance(exc, ConnectorNotConfigured):
            return _NOT_CONFIGURED_MSG.format(slug=slug)
        if isinstance(exc, ConnectorDlpBlocked):
            await audit.record_dlp_block(
                connector_slug=slug,
                tool_name=tool_name,
                agent_id=agent_id,
                categories=exc.categories,
            )
            return _DLP_REFUSAL_MSG.format(cats=", ".join(exc.categories))
        # Rate-limit / transport / parse errors → empty so the agent proceeds.
        # SECURITY: scrub credential material before logging (belt-and-suspenders —
        # the transport already redacts, but a hand-built error must not leak here).
        logger.info(
            "mcp.connector.degraded",
            connector_slug=slug,
            tool_name=tool_name,
            error=redact_secrets(str(exc)),
        )
        return ""

    def _telegram() -> TelegramBotConnector:
        return TelegramBotConnector(
            credential=None,
            transport=telegram_transport,
            rate_limiter=rate_limiter,
            dlp_screen=dlp_screen,
            audit_sink=audit,
        )

    async def telegram_read_updates(query: str) -> str:
        """Прочитать последние сообщения Telegram-канала (Bot API getUpdates).

        Передай числовой offset или пустую строку. Возвращает список сообщений.
        """
        try:
            cred = await _resolve_credential(
                session, resolved_kms, workspace_id=workspace_id, connector_slug=telegram_bot.SLUG
            )
            conn = TelegramBotConnector(
                credential=cred,
                transport=telegram_transport,
                rate_limiter=rate_limiter,
                dlp_screen=dlp_screen,
                audit_sink=audit,
            )
            return _format_telegram(await conn.read_updates(query, agent_id=agent_id))
        except MCPError as exc:
            return await _degrade(
                exc, slug=telegram_bot.SLUG, tool_name=telegram_bot.TOOL_READ_UPDATES
            )

    async def telegram_draft_message(text: str) -> str:
        """Подготовить черновик сообщения Telegram (текст для артефакта, без отправки)."""
        try:
            return await _telegram().draft_message(text, agent_id=agent_id)
        except MCPError as exc:
            return await _degrade(
                exc, slug=telegram_bot.SLUG, tool_name=telegram_bot.TOOL_DRAFT_MESSAGE
            )

    def _yandex() -> YandexDiskConnector:
        return YandexDiskConnector(
            credential=None,
            transport=yandex_transport,
            rate_limiter=rate_limiter,
            dlp_screen=dlp_screen,
            audit_sink=audit,
        )

    async def yandex_disk_list(path: str) -> str:
        """Показать содержимое папки Яндекс.Диска. Передай путь (напр. '/' или '/docs')."""
        try:
            cred = await _resolve_credential(
                session, resolved_kms, workspace_id=workspace_id, connector_slug=yandex_disk.SLUG
            )
            conn = YandexDiskConnector(
                credential=cred,
                transport=yandex_transport,
                rate_limiter=rate_limiter,
                dlp_screen=dlp_screen,
                audit_sink=audit,
            )
            return _format_disk_items(await conn.list_folder(path or "/", agent_id=agent_id))
        except MCPError as exc:
            return await _degrade(exc, slug=yandex_disk.SLUG, tool_name=yandex_disk.TOOL_LIST)

    async def yandex_disk_read_file(path: str) -> str:
        """Скачать и вернуть содержимое файла Яндекс.Диска по пути."""
        try:
            cred = await _resolve_credential(
                session, resolved_kms, workspace_id=workspace_id, connector_slug=yandex_disk.SLUG
            )
            conn = YandexDiskConnector(
                credential=cred,
                transport=yandex_transport,
                rate_limiter=rate_limiter,
                dlp_screen=dlp_screen,
                audit_sink=audit,
            )
            return await conn.read_file(path, agent_id=agent_id)
        except MCPError as exc:
            return await _degrade(exc, slug=yandex_disk.SLUG, tool_name=yandex_disk.TOOL_READ_FILE)

    async def yandex_disk_draft(text: str) -> str:
        """Подготовить черновик содержимого (текст для артефакта, без загрузки на Диск)."""
        try:
            return await _yandex().draft_content(text, agent_id=agent_id)
        except MCPError as exc:
            return await _degrade(exc, slug=yandex_disk.SLUG, tool_name=yandex_disk.TOOL_DRAFT)

    def _imap() -> ImapSmtpConnector:
        return ImapSmtpConnector(
            credential=None,
            transport=imap_transport,
            rate_limiter=rate_limiter,
            dlp_screen=dlp_screen,
            audit_sink=audit,
        )

    async def imap_read_inbox(mailbox: str) -> str:
        """Прочитать последние входящие письма по IMAP. Передай папку (по умолчанию INBOX)."""
        try:
            cred = await _resolve_credential(
                session, resolved_kms, workspace_id=workspace_id, connector_slug=imap_smtp.SLUG
            )
            conn = ImapSmtpConnector(
                credential=cred,
                transport=imap_transport,
                rate_limiter=rate_limiter,
                dlp_screen=dlp_screen,
                audit_sink=audit,
            )
            return _format_inbox(await conn.read_inbox(mailbox or "INBOX", agent_id=agent_id))
        except MCPError as exc:
            return await _degrade(exc, slug=imap_smtp.SLUG, tool_name=imap_smtp.TOOL_READ_INBOX)

    async def email_draft(text: str) -> str:
        """Подготовить черновик письма (текст для артефакта, без отправки)."""
        try:
            return await _imap().draft_email(text, agent_id=agent_id)
        except MCPError as exc:
            return await _degrade(exc, slug=imap_smtp.SLUG, tool_name=imap_smtp.TOOL_DRAFT)

    return {
        telegram_bot.TOOL_READ_UPDATES: telegram_read_updates,
        telegram_bot.TOOL_DRAFT_MESSAGE: telegram_draft_message,
        yandex_disk.TOOL_LIST: yandex_disk_list,
        yandex_disk.TOOL_READ_FILE: yandex_disk_read_file,
        yandex_disk.TOOL_DRAFT: yandex_disk_draft,
        imap_smtp.TOOL_READ_INBOX: imap_read_inbox,
        imap_smtp.TOOL_DRAFT: email_draft,
    }


__all__ = [
    "CONNECTOR_ACTOR_ID",
    "DLP_BLOCK_ACTION",
    "EXTERNAL_CALL_ACTION",
    "EmitConnectorAuditSink",
    "NativeTool",
    "build_connector_tools",
]
