"""Unit tests for the delegate_task tool guards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.exceptions import DelegationDepthExceeded, DelegationTargetInvalid
from src.agents.tools.delegate import (
    CoordinatorDepsLike,
    DelegateInput,
    DelegateResult,
    delegate_task,
)


@dataclass
class _FakeRunContext:
    """Minimal RunContext stand-in. Real pydantic_ai.RunContext brings the
    full agent runtime which is overkill for unit-level guard tests."""

    deps: Any


async def test_delegate_rejects_target_not_in_team():
    deps = CoordinatorDepsLike(
        cell_id=uuid4(),
        task_id=uuid4(),
        user_id=uuid4(),
        available_agent_slugs=["researcher", "writer"],
    )
    ctx = _FakeRunContext(deps=deps)
    with pytest.raises(DelegationTargetInvalid):
        await delegate_task(
            ctx,  # type: ignore[arg-type]
            DelegateInput(target_agent_slug="ghost", sub_prompt="..."),
        )


async def test_delegate_rejects_depth_at_limit():
    deps = CoordinatorDepsLike(
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


async def test_delegate_invokes_runner():
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

    deps = CoordinatorDepsLike(
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


async def test_delegate_without_runner_raises_informative_notimplemented():
    deps = CoordinatorDepsLike(
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
