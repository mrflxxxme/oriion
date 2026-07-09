"""Unit: connector outgoing-args DLP screen (the exfiltration guard, AC-01.9b.2).

Proves the screen reuses the 01.6 detector: a contextual ИНН / e-mail in the args
raises ``ConnectorDlpBlocked`` (categories only, never the value); clean/empty
args are a no-op.
"""

from __future__ import annotations

import pytest
from src.mcp.tools.connectors.dlp_screen import (
    PiiConnectorDlpScreen,
    default_connector_dlp_screen,
)
from src.mcp.tools.connectors.exceptions import ConnectorDlpBlocked

_INN_CTX = "ИНН поставщика 7830002293"  # valid ИНН-10 + labelling token (synthetic)


@pytest.mark.asyncio
async def test_blocks_contextual_inn() -> None:
    with pytest.raises(ConnectorDlpBlocked) as ei:
        await default_connector_dlp_screen.screen(
            [_INN_CTX], connector_slug="telegram-bot", tool_name="telegram_read_updates"
        )
    assert ei.value.categories == ("inn",)
    # SECURITY: the raw number never appears in the exception message.
    assert "7830002293" not in str(ei.value)


@pytest.mark.asyncio
async def test_blocks_email_in_any_arg() -> None:
    with pytest.raises(ConnectorDlpBlocked):
        await PiiConnectorDlpScreen().screen(
            ["тема", "пиши на ivan@example.com"],
            connector_slug="imap-smtp",
            tool_name="email_draft",
        )


@pytest.mark.asyncio
async def test_clean_args_pass() -> None:
    # No raise — a benign query/draft is allowed through to the connector.
    await default_connector_dlp_screen.screen(
        ["план на неделю", "черновик поста"], connector_slug="s", tool_name="t"
    )


@pytest.mark.asyncio
async def test_empty_args_are_noop() -> None:
    await default_connector_dlp_screen.screen(["", ""], connector_slug="s", tool_name="t")


@pytest.mark.asyncio
async def test_bare_number_without_context_is_not_blocked() -> None:
    # A bare 10-digit run with no INN label is not identifiable PII (01.9a gate).
    await default_connector_dlp_screen.screen(
        ["заказ 7830002293"], connector_slug="s", tool_name="t"
    )
