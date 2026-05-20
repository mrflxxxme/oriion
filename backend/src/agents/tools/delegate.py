"""delegate_task — Coordinator-only tool for sub-task fan-out.

Per Phase 00.5 phase-spec + ADR-016 (team-first UX, no peer-to-peer agent comms).
Only the Coordinator role has this tool wired in its Agent.tools list — the
three leaf specialists (Researcher / Writer / Analyst) CANNOT delegate
(prevents accidental recursion and matches the ADR-016 mental model
"Coordinator hires specialists; specialists do not hire each other").

Wave 0 surface (Phase 00.5b Commit 5): validate target + depth + emit a
delegation event. The actual sub-task orchestration (DB row creation,
step persistence, SSE emission, cost rollup) lives in
``src.runtime.orchestrator.execute_agent_task`` which lands in Commit 6.

Until orchestrator wires up, callers either:
    (a) inject a ``runner: DelegateRunner`` callable via ``CoordinatorDeps``
        for in-process dispatch (demo-flow integration test uses this); or
    (b) rely on the orchestrator (lands Commit 6).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from src.agents.exceptions import DelegationDepthExceeded, DelegationTargetInvalid

DEFAULT_MAX_DELEGATION_DEPTH = 5


# ── tool payload schemas ────────────────────────────────────────────────


class DelegateInput(BaseModel):
    """Coordinator-side delegation payload — passed as the tool argument."""

    target_agent_slug: str = Field(
        ...,
        description="Role-key of the target agent — 'researcher' | 'writer' | 'analyst'",
    )
    sub_prompt: str = Field(
        ...,
        min_length=1,
        description="Self-sufficient instruction (target agent does not see user-prompt)",
    )
    context_artifact_ids: list[UUID] = Field(
        default_factory=list,
        description="Optional artifact references from previous sub-tasks",
    )


class DelegateResult(BaseModel):
    """Coordinator-side delegation result."""

    sub_task_id: UUID
    target_agent_slug: str
    output: str
    cost_credits: Decimal = Decimal(0)
    tokens_used: int = 0


# ── runner protocol — injected via deps ─────────────────────────────────


DelegateRunner = Callable[["DelegateInput", "CoordinatorDepsLike"], Awaitable[DelegateResult]]
"""Signature: ``async (DelegateInput, deps) -> DelegateResult``."""


@dataclass
class CoordinatorDepsLike:
    """Minimum surface ``delegate_task`` needs from the parent agent's deps.

    Concrete Agent definitions (coordinator.py) compose this into a richer
    Pydantic BaseModel — we keep this dataclass-style shim so the tool
    signature stays independent of the larger CoordinatorDeps class.
    """

    cell_id: UUID
    task_id: UUID
    user_id: UUID
    available_agent_slugs: list[str]
    current_depth: int = 0
    max_delegation_depth: int = DEFAULT_MAX_DELEGATION_DEPTH
    runner: DelegateRunner | None = None


# ── the tool function ────────────────────────────────────────────────────


async def delegate_task(
    ctx: RunContext[Any],
    inp: DelegateInput,
) -> DelegateResult:
    """Tool body — guards + dispatch.

    1. Validate target_agent_slug ∈ ctx.deps.available_agent_slugs.
    2. Validate ctx.deps.current_depth < max_delegation_depth.
    3. Dispatch:
       * ctx.deps.runner is set → in-process call (demo-flow path).
       * else → raise NotImplementedError pointing at Commit 6.

    All sub-task DB persistence + audit + cost rollup live downstream
    of the runner (per ADR-024 — agents stays bounded to «what to
    delegate»; tasks/runtime owns «how it executes»).
    """
    deps = ctx.deps
    target_slug = inp.target_agent_slug

    available = list(getattr(deps, "available_agent_slugs", []) or [])
    if target_slug not in available:
        raise DelegationTargetInvalid(
            f"target_agent_slug={target_slug!r} not in cell team "
            f"{sorted(available)}. Coordinator can only delegate to provisioned "
            "specialists."
        )

    current_depth = int(getattr(deps, "current_depth", 0))
    max_depth = int(getattr(deps, "max_delegation_depth", DEFAULT_MAX_DELEGATION_DEPTH))
    if current_depth >= max_depth:
        raise DelegationDepthExceeded(
            f"delegation depth {current_depth} >= max {max_depth}. ADR-016 "
            "horizontal preset normally runs at depth 1-2; depth 3+ signals "
            "an over-decomposed plan."
        )

    runner: DelegateRunner | None = getattr(deps, "runner", None)
    if runner is None:
        raise NotImplementedError(
            "delegate_task has no runner attached. Wire ctx.deps.runner in the "
            "agent test fixture (Commit 5) OR rely on the runtime orchestrator "
            "(Commit 6, src.runtime.orchestrator.execute_agent_task)."
        )

    return await runner(inp, deps)


def make_sub_task_id() -> UUID:
    """Helper for runners that don't have DB-generated IDs yet."""
    return uuid4()
