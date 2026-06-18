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
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from src.agents.exceptions import DelegationDepthExceeded, DelegationTargetInvalid

DEFAULT_MAX_DELEGATION_DEPTH = 5


# ── canonical agent slugs (single source of truth) ──────────────────────


class AgentSlug(StrEnum):
    """Canonical agent role-slugs — the single source of truth (AC-W1-8).

    Constrains ``DelegateInput.target_agent_slug`` at *validation* time so an
    unknown slug fails fast with a Pydantic ``ValidationError`` instead of
    slipping through to dispatch. This is distinct from the per-cell *team
    membership* check in ``assert_delegation_allowed`` — that is the runtime
    authz layer (is this slug provisioned in THIS cell + under the depth cap);
    this enum only asserts the slug names a known archetype at all.

    ``StrEnum`` keeps each member a real ``str`` so existing comparisons,
    membership tests against ``available_agent_slugs: list[str]``, dict/SSE
    payloads and JSON serialization keep working unchanged.
    """

    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    WRITER = "writer"
    ANALYST = "analyst"


# ── tool payload schemas ────────────────────────────────────────────────


class DelegateInput(BaseModel):
    """Coordinator-side delegation payload — passed as the tool argument."""

    target_agent_slug: AgentSlug = Field(
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
    target_agent_slug: AgentSlug
    output: str
    cost_credits: Decimal = Decimal(0)
    tokens_used: int = 0


# ── runner protocol + the single deps container ─────────────────────────


DelegateRunner = Callable[["DelegateInput", "CoordinatorDeps"], Awaitable[DelegateResult]]
"""Signature: ``async (DelegateInput, deps) -> DelegateResult``."""


@dataclass
class CoordinatorDeps:
    """The single per-run deps container for the Coordinator (AC-W1-7).

    Collapses the former ``CoordinatorDeps`` (Pydantic BaseModel, was in
    ``agents/coordinator.py``) ↔ ``CoordinatorDepsLike`` (dataclass, was here)
    duality into ONE type. It lives in this low-level module because
    ``coordinator.py`` imports from ``delegate.py`` (not vice-versa), so the
    single type must be defined here to avoid an import cycle;
    ``coordinator.py`` re-exports it for backwards-compatible imports.

    Holds the minimum surface ``delegate_task`` + the plan-executor
    (``runtime.dispatch.PlanExecutingCoordinator``) need; the runtime
    orchestrator (Commit 6) injects the real DB-backed ``runner``.
    """

    cell_id: UUID
    task_id: UUID
    user_id: UUID
    available_agent_slugs: list[str] = field(
        default_factory=lambda: [
            AgentSlug.RESEARCHER,
            AgentSlug.WRITER,
            AgentSlug.ANALYST,
        ]
    )
    current_depth: int = 0
    max_delegation_depth: int = DEFAULT_MAX_DELEGATION_DEPTH
    # in-process runner for demo-flow tests; runtime orchestrator (Commit 6)
    # injects the real DB-backed runner.
    runner: DelegateRunner | None = None


# ── shared delegation guard ──────────────────────────────────────────────


def assert_delegation_allowed(
    target_slug: str,
    *,
    available: list[str],
    current_depth: int,
    max_depth: int = DEFAULT_MAX_DELEGATION_DEPTH,
) -> None:
    """Guard a delegation: target must be in-team and depth under the cap.

    Shared by the ``delegate_task`` tool (agentic path) and the plan-execution
    path (``runtime.dispatch.PlanExecutingCoordinator``, AC-W1-16b/24) so both
    enforce the same ADR-016 invariants. Raises ``DelegationTargetInvalid`` /
    ``DelegationDepthExceeded``.
    """
    if target_slug not in available:
        raise DelegationTargetInvalid(
            f"target_agent_slug={target_slug!r} not in cell team "
            f"{sorted(available)}. Coordinator can only delegate to provisioned "
            "specialists."
        )
    if current_depth >= max_depth:
        raise DelegationDepthExceeded(
            f"delegation depth {current_depth} >= max {max_depth}. ADR-016 "
            "horizontal preset normally runs at depth 1-2; depth 3+ signals "
            "an over-decomposed plan."
        )


# ── the tool function ────────────────────────────────────────────────────


async def delegate_task(
    ctx: RunContext[CoordinatorDeps],
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

    assert_delegation_allowed(
        inp.target_agent_slug,
        available=list(deps.available_agent_slugs or []),
        current_depth=deps.current_depth,
        max_depth=deps.max_delegation_depth,
    )

    runner = deps.runner
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
