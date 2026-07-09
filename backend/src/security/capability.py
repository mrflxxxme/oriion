"""Capability risk classifier + approval seam (ADR-039 §5, layer B).

There is **no runtime capability-gate in 01.6** — the real gate activates in 01.9
when the first outward-action connectors land together with the owner-config
surface. This module is the *substrate*: a deterministic static registry of tool
risk + ``requires_approval()`` (fail-closed on unknown tools) that 01.9 will call
before dispatching a dangerous tool.

Static registry (not a DB column): agent personas live on
``agents.agent_archetypes`` with a ``tools_allowed`` array and carry no
``risk_level`` field; a static map satisfies the classify-by-risk intent with
zero migration.
"""

from __future__ import annotations

from src.security.ports import RiskLevel

TOOL_RISK: dict[str, RiskLevel] = {
    # Wave-1 tool surface — all read-only / internal (no outward action).
    "web_search": RiskLevel.READ_ONLY,
    "read_url": RiskLevel.READ_ONLY,
    "delegate_task": RiskLevel.INTERNAL,
    # Wave-1 connector READ/DRAFT tools (01.9b, ADR-041). READ = external read,
    # no side-effect (READ_ONLY); DRAFT = prepare content for an artifact, no
    # outward action (INTERNAL). Both pass the gate; the paired ``send_*`` tools
    # below stay DANGEROUS (deny-until-approval-UI 01.12).
    "telegram_read_updates": RiskLevel.READ_ONLY,
    "telegram_draft_message": RiskLevel.INTERNAL,
    "yandex_disk_list": RiskLevel.READ_ONLY,
    "yandex_disk_read_file": RiskLevel.READ_ONLY,
    "yandex_disk_draft": RiskLevel.INTERNAL,
    "imap_read_inbox": RiskLevel.READ_ONLY,
    "email_draft": RiskLevel.INTERNAL,
    # Outward-action tools. The connector ``send_*`` tools (01.9b) join the
    # pre-declared DANGEROUS set — the gate denies them until the approval UI.
    "send_email": RiskLevel.DANGEROUS,
    "send_telegram": RiskLevel.DANGEROUS,
    "transfer_money": RiskLevel.DANGEROUS,
    "commit_to_prod_branch": RiskLevel.DANGEROUS,
}


def classify_tool(tool_name: str) -> RiskLevel:
    """Risk tier of a tool. Fail-closed: an unknown tool is treated DANGEROUS."""
    return TOOL_RISK.get(tool_name, RiskLevel.DANGEROUS)


def requires_approval(tool_name: str) -> bool:
    """Whether invoking ``tool_name`` needs human approval.

    The 01.9 capability-gate seam: True for any DANGEROUS (incl. unknown) tool.
    01.6 only classifies — it does not gate any dispatch path.
    """
    return classify_tool(tool_name) is RiskLevel.DANGEROUS
