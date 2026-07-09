"""telegram-bot connector — Bot-API READ + DRAFT (Phase 01.9b, ADR-041).

Bot-API scope ONLY (NOT Business-API — that is 01.11, GATED RW-05). Read = fetch
recent channel posts / updates via ``getUpdates``. Draft = prepare a message body
the agent puts into an artifact (no external call, no credential). Send =
guarded DANGEROUS stub (deny-until-approval-UI 01.12) — never performs a real
``sendMessage``.

Transport is injectable (``HttpTransport``) so unit tests drive it with a mock;
the real ``HttpxTransport`` is used only when a bot token is configured
(deferred live-smoke, DV-11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from src.mcp.tools.connectors.base import BaseConnector, HttpResponse, HttpTransport, HttpxTransport
from src.mcp.tools.connectors.exceptions import ConnectorError, ConnectorSendDisabled

SLUG: Final = "telegram-bot"
TOOL_READ_UPDATES: Final = "telegram_read_updates"
TOOL_DRAFT_MESSAGE: Final = "telegram_draft_message"
TOOL_SEND: Final = "send_telegram"

_API_BASE: Final = "https://api.telegram.org"
_DEFAULT_LIMIT: Final = 20


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    """One parsed channel post / update message."""

    chat: str
    text: str
    date: int


def _parse_offset(query: str) -> int | None:
    """Interpret a numeric query as a getUpdates ``offset``; else None."""
    q = query.strip()
    if not q:
        return None
    try:
        return int(q)
    except ValueError:
        return None


def _parse_updates(payload: Any, limit: int) -> list[TelegramMessage]:
    """Parse a Bot-API ``getUpdates`` response into messages (degrades to [])."""
    if not isinstance(payload, dict) or not payload.get("ok"):
        return []
    results = payload.get("result")
    if not isinstance(results, list):
        return []
    out: list[TelegramMessage] = []
    for update in results:
        if not isinstance(update, dict):
            continue
        # A channel post arrives as ``channel_post``; a DM/group message as ``message``.
        msg = update.get("channel_post") or update.get("message")
        if not isinstance(msg, dict):
            continue
        text = msg.get("text") or msg.get("caption") or ""
        chat_raw = msg.get("chat")
        chat_obj: dict[str, Any] = chat_raw if isinstance(chat_raw, dict) else {}
        chat = str(chat_obj.get("title") or chat_obj.get("username") or chat_obj.get("id") or "")
        date_raw = msg.get("date")
        date = date_raw if isinstance(date_raw, int) else 0
        out.append(TelegramMessage(chat=chat, text=str(text), date=date))
        if len(out) >= limit:
            break
    return out


class TelegramBotConnector(BaseConnector):
    """Telegram Bot-API connector — read updates, draft a message (guarded send)."""

    def __init__(
        self,
        *,
        credential: str | None,
        transport: HttpTransport | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(connector_slug=SLUG, credential=credential, **base_kwargs)
        self._transport = transport or HttpxTransport()

    async def read_updates(
        self, query: str = "", *, agent_id: str = "system", limit: int = _DEFAULT_LIMIT
    ) -> list[TelegramMessage]:
        """READ: recent channel posts / updates via Bot-API ``getUpdates``."""
        await self._rate_limit(agent_id, TOOL_READ_UPDATES)
        await self._screen(TOOL_READ_UPDATES, [query])
        token = self._require_credential()
        params: dict[str, Any] = {"limit": limit}
        offset = _parse_offset(query)
        if offset is not None:
            params["offset"] = offset
        resp: HttpResponse = await self._transport.request(
            "GET", f"{_API_BASE}/bot{token}/getUpdates", params=params
        )
        try:
            messages = _parse_updates(resp.json(), limit)
        except ValueError as exc:
            raise ConnectorError("telegram getUpdates: non-JSON response") from exc
        await self._audit_external(TOOL_READ_UPDATES, agent_id)
        return messages

    async def draft_message(self, text: str, *, agent_id: str = "system") -> str:
        """DRAFT: prepare a message body for an artifact (no external call)."""
        await self._rate_limit(agent_id, TOOL_DRAFT_MESSAGE)
        await self._screen(TOOL_DRAFT_MESSAGE, [text])
        return text.strip()

    async def send(self, text: str, *, agent_id: str = "system") -> str:  # noqa: ARG002
        """SEND (guarded stub): autonomous send is deny-until-approval-UI (01.12).

        Never performs a real Bot-API ``sendMessage``. Also DANGEROUS-classified,
        so the capability gate denies registration long before this is reachable.
        """
        raise ConnectorSendDisabled("send_telegram is disabled until the approval UI (01.12)")


__all__ = [
    "SLUG",
    "TOOL_DRAFT_MESSAGE",
    "TOOL_READ_UPDATES",
    "TOOL_SEND",
    "TelegramBotConnector",
    "TelegramMessage",
]
