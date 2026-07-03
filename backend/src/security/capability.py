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
    # Outward-action tools land with connectors (01.9+). Declared now so the
    # classifier + approval seam is ready; the real gate activates in 01.9.
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
