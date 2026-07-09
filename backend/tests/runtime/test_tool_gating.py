"""Unit: runtime.tool_gating — capability-gate policy + audit-on-deny (Phase 01.9b).

Proves the exact activation rule:
  * DANGEROUS / unknown tools are denied (fail-closed), independent of the allowlist.
  * A non-empty ``tools_allowed`` scopes per role (filters unlisted tools).
  * An EMPTY ``tools_allowed`` allows all non-DANGEROUS tools (backward-compat).
  * Each denial emits an audit row via the injected sink.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from src.runtime.tool_gating import (
    DENY_NOT_IN_ALLOWLIST,
    DENY_REQUIRES_APPROVAL,
    evaluate_tools,
    gate_agent_tools,
)


class _FakeAuditSink:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def record_tool_denied(
        self,
        *,
        tool_name: str,
        reason: str,
        agent_slug: str,
        task_id: UUID | None,
        cell_id: UUID | None,
        workspace_id: UUID | None,
    ) -> None:
        self.calls.append(
            {
                "tool_name": tool_name,
                "reason": reason,
                "agent_slug": agent_slug,
                "task_id": task_id,
                "cell_id": cell_id,
                "workspace_id": workspace_id,
            }
        )


# ── evaluate_tools (pure policy) ──────────────────────────────────────────


def test_read_only_tools_pass_under_empty_allowlist() -> None:
    decision = evaluate_tools(["web_search", "read_url"], tools_allowed=[])
    assert decision.allowed == ("web_search", "read_url")
    assert decision.denied == ()


def test_dangerous_tool_denied_even_when_in_allowlist() -> None:
    # A DANGEROUS tool is denied regardless of the allowlist (deny-until-approval).
    decision = evaluate_tools(["send_email"], tools_allowed=["send_email"])
    assert decision.allowed == ()
    assert [d.reason for d in decision.denied] == [DENY_REQUIRES_APPROVAL]
    assert decision.denied[0].name == "send_email"


def test_unknown_tool_is_fail_closed() -> None:
    decision = evaluate_tools(["mystery_tool"], tools_allowed=[])
    assert decision.allowed == ()
    assert decision.denied[0].reason == DENY_REQUIRES_APPROVAL


def test_non_empty_allowlist_scopes_out_unlisted_tool() -> None:
    decision = evaluate_tools(["web_search", "read_url"], tools_allowed=["web_search"])
    assert decision.allowed == ("web_search",)
    assert [(d.name, d.reason) for d in decision.denied] == [("read_url", DENY_NOT_IN_ALLOWLIST)]


def test_listed_read_only_tools_all_pass() -> None:
    decision = evaluate_tools(["web_search", "read_url"], tools_allowed=["web_search", "read_url"])
    assert decision.allowed == ("web_search", "read_url")
    assert decision.denied == ()


# ── gate_agent_tools (filter + audit) ─────────────────────────────────────


async def _ws(_q: str) -> str:
    return "web"


async def _ru(_q: str) -> str:
    return "url"


async def _send(_q: str) -> str:
    return "sent"


@pytest.mark.asyncio
async def test_gate_returns_allowed_callables_and_audits_denials() -> None:
    sink = _FakeAuditSink()
    task_id, cell_id, workspace_id = uuid4(), uuid4(), uuid4()
    allowed = await gate_agent_tools(
        {"web_search": _ws, "send_telegram": _send},
        tools_allowed=[],
        agent_slug="researcher",
        audit=sink,
        task_id=task_id,
        cell_id=cell_id,
        workspace_id=workspace_id,
    )
    # web_search survives (READ_ONLY); send_telegram dropped (DANGEROUS).
    assert set(allowed) == {"web_search"}
    assert allowed["web_search"] is _ws
    assert len(sink.calls) == 1
    call = sink.calls[0]
    assert call["tool_name"] == "send_telegram"
    assert call["reason"] == DENY_REQUIRES_APPROVAL
    assert call["agent_slug"] == "researcher"
    assert call["task_id"] == task_id
    assert call["workspace_id"] == workspace_id


@pytest.mark.asyncio
async def test_gate_scopes_by_non_empty_allowlist_and_audits() -> None:
    sink = _FakeAuditSink()
    allowed = await gate_agent_tools(
        {"web_search": _ws, "read_url": _ru},
        tools_allowed=["web_search"],
        agent_slug="researcher",
        audit=sink,
    )
    assert set(allowed) == {"web_search"}
    assert [c["reason"] for c in sink.calls] == [DENY_NOT_IN_ALLOWLIST]
    assert sink.calls[0]["tool_name"] == "read_url"


@pytest.mark.asyncio
async def test_gate_without_audit_sink_does_not_crash_on_deny() -> None:
    allowed = await gate_agent_tools(
        {"send_email": _send},
        tools_allowed=[],
        agent_slug="writer",
        audit=None,
    )
    assert allowed == {}
