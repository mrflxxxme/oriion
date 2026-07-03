"""Unit tests for the capability risk classifier + approval seam (ADR-039 §5)."""

from __future__ import annotations

import pytest
from src.security.capability import classify_tool, requires_approval
from src.security.ports import RiskLevel


class TestClassifyTool:
    @pytest.mark.parametrize(
        ("tool", "expected"),
        [
            ("web_search", RiskLevel.READ_ONLY),
            ("read_url", RiskLevel.READ_ONLY),
            ("delegate_task", RiskLevel.INTERNAL),
            ("send_email", RiskLevel.DANGEROUS),
            ("send_telegram", RiskLevel.DANGEROUS),
            ("transfer_money", RiskLevel.DANGEROUS),
        ],
    )
    def test_known_tools(self, tool: str, expected: RiskLevel) -> None:
        assert classify_tool(tool) is expected

    def test_unknown_tool_fail_closed_dangerous(self) -> None:
        assert classify_tool("some_new_unlisted_tool") is RiskLevel.DANGEROUS


class TestRequiresApproval:
    def test_read_only_and_internal_no_approval(self) -> None:
        assert requires_approval("web_search") is False
        assert requires_approval("read_url") is False
        assert requires_approval("delegate_task") is False

    def test_dangerous_requires_approval(self) -> None:
        assert requires_approval("send_email") is True
        assert requires_approval("transfer_money") is True

    def test_unknown_requires_approval(self) -> None:
        assert requires_approval("mystery_tool") is True
