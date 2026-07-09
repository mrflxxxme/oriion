"""Unit: TOOL_RISK entries for the Wave-1 connector tools (Phase 01.9b).

Read tools → READ_ONLY, draft tools → INTERNAL (both pass the gate); the paired
send_* tools stay DANGEROUS (deny-until-approval-UI 01.12).
"""

from __future__ import annotations

import pytest
from src.security.capability import classify_tool, requires_approval
from src.security.ports import RiskLevel


@pytest.mark.parametrize(
    "tool",
    ["telegram_read_updates", "yandex_disk_list", "yandex_disk_read_file", "imap_read_inbox"],
)
def test_connector_read_tools_are_read_only(tool: str) -> None:
    assert classify_tool(tool) is RiskLevel.READ_ONLY
    assert requires_approval(tool) is False


@pytest.mark.parametrize(
    "tool",
    ["telegram_draft_message", "yandex_disk_draft", "email_draft"],
)
def test_connector_draft_tools_are_internal(tool: str) -> None:
    assert classify_tool(tool) is RiskLevel.INTERNAL
    assert requires_approval(tool) is False


@pytest.mark.parametrize("tool", ["send_telegram", "send_email"])
def test_connector_send_tools_are_dangerous(tool: str) -> None:
    assert classify_tool(tool) is RiskLevel.DANGEROUS
    assert requires_approval(tool) is True
