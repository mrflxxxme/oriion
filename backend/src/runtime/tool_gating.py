"""Capability-gate activation for the tool-dispatch path (ADR-039 §5, Phase 01.9b).

This is the FIRST runtime enforcement of the 01.6 capability substrate
(``src.security.capability``). Given a candidate set of named tools + an agent
archetype's ``tools_allowed`` allowlist, the gate returns only the tools that may
be attached to the Agent, dropping:

  1. **DANGEROUS (or unknown → fail-closed) tools** — ``requires_approval`` is
     True. These are deny-until-approval-UI (01.12); the class includes every
     outward-action connector tool (``send_email`` / ``send_telegram`` / …) that
     pass B will register. This rule is INDEPENDENT of the allowlist and is
     ALWAYS enforced.
  2. **Tools outside the archetype's per-role allowlist — but ONLY when the
     allowlist is non-empty.** An EMPTY ``tools_allowed`` means "all non-DANGEROUS
     tools allowed" (backward-compat): the seeded ``writer`` / ``analyst`` /
     ``master`` / ``memory_curator`` archetypes carry ``[]`` and must keep
     working, and the seeded ``researcher`` / ``coordinator`` DO list
     ``web_search`` / ``read_url`` so they pass under either interpretation. This
     keeps the live web_search/read_url pipeline intact.

Each denied tool emits an ``audit.audit_log`` row via the ``ToolDenyAuditSink``
port (real adapter wraps ``audit.emit_audit_event`` with a fixed synthetic system
actor). The audit payload carries only the tool name + deny reason + agent slug —
no secret or tool argument.

The gate is the clean seam pass B threads its connector tools through: build the
``{name: callable}`` candidate map, call :func:`gate_agent_tools`, attach the
returned subset to the Agent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.services.audit_service import emit_audit_event
from src.security.capability import requires_approval

logger = structlog.get_logger(__name__)

_T = TypeVar("_T")

# Deny reasons (stable strings — surface in the audit payload).
DENY_REQUIRES_APPROVAL = "requires_approval"
DENY_NOT_IN_ALLOWLIST = "not_in_allowlist"

# Fixed synthetic actor for capability-gate audit rows (a tool denial is a system
# action, not a user action). Stable so audit queries can filter on it.
CAPABILITY_GATE_ACTOR_ID = UUID("5ec00000-0000-0000-0000-00000000ca9e")

TOOL_DENIED_ACTION = "security.capability.tool_denied"


@dataclass(frozen=True, slots=True)
class DeniedTool:
    """One tool the gate refused — its name + the deny reason (no value)."""

    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ToolGateDecision:
    """Outcome of a capability-gate evaluation over a candidate tool set."""

    allowed: tuple[str, ...] = ()
    denied: tuple[DeniedTool, ...] = ()


def evaluate_tools(
    candidate_tools: Sequence[str],
    *,
    tools_allowed: Sequence[str],
) -> ToolGateDecision:
    """Pure capability-gate policy over candidate tool NAMES.

    Rules (in order, per tool):
      1. ``requires_approval(name)`` True (DANGEROUS or unknown → fail-closed) →
         DENY (``requires_approval``). Independent of the allowlist.
      2. Non-empty ``tools_allowed`` and ``name`` not in it → DENY
         (``not_in_allowlist``). An EMPTY allowlist disables scoping (all
         non-DANGEROUS tools pass) for backward-compat.
      3. Otherwise → ALLOW.

    Deterministic and side-effect free; :func:`gate_agent_tools` layers the audit
    emission + callable filtering on top.
    """
    allowlist = set(tools_allowed)
    scope_by_allowlist = bool(allowlist)
    allowed: list[str] = []
    denied: list[DeniedTool] = []
    for name in candidate_tools:
        if requires_approval(name):
            denied.append(DeniedTool(name, DENY_REQUIRES_APPROVAL))
            continue
        if scope_by_allowlist and name not in allowlist:
            denied.append(DeniedTool(name, DENY_NOT_IN_ALLOWLIST))
            continue
        allowed.append(name)
    return ToolGateDecision(allowed=tuple(allowed), denied=tuple(denied))


class ToolDenyAuditSink(Protocol):
    """Sink for a capability-gate tool-deny audit row.

    SECURITY: the impl MUST receive only the tool name + reason + agent slug —
    never a tool argument or any secret.
    """

    async def record_tool_denied(
        self,
        *,
        tool_name: str,
        reason: str,
        agent_slug: str,
        task_id: UUID | None,
        cell_id: UUID | None,
        workspace_id: UUID | None,
    ) -> None: ...


class EmitToolDenyAuditSink:
    """Real ``ToolDenyAuditSink`` — INSERTs a deny row via ``emit_audit_event``.

    Writes on the caller's session (no commit): the caller owns the surrounding
    transaction. SECURITY: the payload carries the tool name + deny reason + agent
    slug only.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        # Anchor the row on the task (resource_id=task_id + resource_type='task'),
        # mirroring the DLP-block audit row so both are queryable the same way; the
        # denied tool + reason + agent live in the payload (no secret / tool arg).
        await emit_audit_event(
            actor_type="system",
            actor_id=CAPABILITY_GATE_ACTOR_ID,
            action=TOOL_DENIED_ACTION,
            resource_type="task",
            resource_id=task_id,
            payload={"tool_name": tool_name, "reason": reason, "agent_slug": agent_slug},
            session=self._session,
            workspace_id=workspace_id,
            cell_id=cell_id,
        )


async def gate_agent_tools(
    candidate_tools: Mapping[str, _T],
    *,
    tools_allowed: Sequence[str],
    agent_slug: str,
    audit: ToolDenyAuditSink | None = None,
    task_id: UUID | None = None,
    cell_id: UUID | None = None,
    workspace_id: UUID | None = None,
) -> dict[str, _T]:
    """Filter a ``{name: callable}`` candidate map through the capability gate.

    Returns the allowed subset (preserving the callables). Each denied tool is
    logged and — when ``audit`` is supplied — recorded to ``audit.audit_log``.
    Audit failures are best-effort: a denied tool is already dropped, so a broken
    sink must never crash dispatch.
    """
    decision = evaluate_tools(tuple(candidate_tools), tools_allowed=tools_allowed)
    for denied in decision.denied:
        logger.warning(
            "security.capability.tool_denied",
            tool_name=denied.name,
            reason=denied.reason,
            agent_slug=agent_slug,
        )
        if audit is not None:
            await audit.record_tool_denied(
                tool_name=denied.name,
                reason=denied.reason,
                agent_slug=agent_slug,
                task_id=task_id,
                cell_id=cell_id,
                workspace_id=workspace_id,
            )
    return {name: candidate_tools[name] for name in decision.allowed}


__all__ = [
    "CAPABILITY_GATE_ACTOR_ID",
    "DENY_NOT_IN_ALLOWLIST",
    "DENY_REQUIRES_APPROVAL",
    "TOOL_DENIED_ACTION",
    "DeniedTool",
    "EmitToolDenyAuditSink",
    "ToolDenyAuditSink",
    "ToolGateDecision",
    "evaluate_tools",
    "gate_agent_tools",
]
