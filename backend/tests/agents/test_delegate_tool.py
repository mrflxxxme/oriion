"""Unit tests for the delegate_task tool guards + the slug-validation seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from src.agents.exceptions import DelegationDepthExceeded, DelegationTargetInvalid
from src.agents.tools.delegate import (
    AgentSlug,
    CoordinatorDeps,
    DelegateInput,
    DelegateResult,
    delegate_task,
)


@dataclass
class _FakeRunContext:
    """Minimal RunContext stand-in. Real pydantic_ai.RunContext brings the
    full agent runtime which is overkill for unit-level guard tests."""

    deps: Any


def test_delegate_input_rejects_unknown_slug() -> None:
    """AC-W1-8: an unknown slug fails at *validation* time, not at dispatch.

    A bare ``str`` field would have accepted ``"bogus"`` and only tripped the
    runtime team-membership guard; the ``AgentSlug`` enum rejects it up-front.
    """
    with pytest.raises(ValidationError):
        DelegateInput(target_agent_slug="bogus", sub_prompt="...")  # type: ignore[arg-type]


def test_delegate_input_accepts_known_slug() -> None:
    inp = DelegateInput(target_agent_slug="researcher", sub_prompt="find data")
    assert inp.target_agent_slug is AgentSlug.RESEARCHER
    # StrEnum stays a real str for downstream comparisons / serialization.
    assert inp.target_agent_slug == "researcher"


async def test_delegate_rejects_target_not_in_team() -> None:
    # 'analyst' is a *valid* AgentSlug but is NOT in this cell's team, so the
    # runtime authz guard (not schema validation) must reject it.
    deps = CoordinatorDeps(
        cell_id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        available_agent_slugs=["researcher", "writer"],
    )
    ctx = _FakeRunContext(deps=deps)
    with pytest.raises(DelegationTargetInvalid):
        await delegate_task(
            ctx,  # type: ignore[arg-type]
            DelegateInput(target_agent_slug="analyst", sub_prompt="..."),
        )


async def test_delegate_rejects_depth_at_limit() -> None:
    deps = CoordinatorDeps(
        cell_id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        available_agent_slugs=["researcher"],
        current_depth=5,
        max_delegation_depth=5,
    )
    ctx = _FakeRunContext(deps=deps)
    with pytest.raises(DelegationDepthExceeded):
        await delegate_task(
            ctx,  # type: ignore[arg-type]
            DelegateInput(target_agent_slug="researcher", sub_prompt="..."),
        )


async def test_delegate_invokes_runner() -> None:
    captured: dict[str, Any] = {}

    async def fake_runner(inp: DelegateInput, deps: Any) -> DelegateResult:
        captured["inp"] = inp
        captured["deps"] = deps
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output="canned",
            tokens_used=42,
        )

    deps = CoordinatorDeps(
        cell_id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        available_agent_slugs=["researcher", "writer"],
        runner=fake_runner,
    )
    ctx = _FakeRunContext(deps=deps)
    result = await delegate_task(
        ctx,  # type: ignore[arg-type]
        DelegateInput(target_agent_slug="researcher", sub_prompt="find market data"),
    )
    assert result.tokens_used == 42
    assert isinstance(result.sub_task_id, UUID)
    assert captured["inp"].target_agent_slug == "researcher"


async def test_delegate_without_runner_raises_informative_notimplemented() -> None:
    deps = CoordinatorDeps(
        cell_id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        available_agent_slugs=["researcher"],
        runner=None,
    )
    ctx = _FakeRunContext(deps=deps)
    with pytest.raises(NotImplementedError, match="orchestrator|runner"):
        await delegate_task(
            ctx,  # type: ignore[arg-type]
            DelegateInput(target_agent_slug="researcher", sub_prompt="..."),
        )
