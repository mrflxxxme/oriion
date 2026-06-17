"""AC-W1-13 + AC-W1-2: the leaf runner derives REAL cost from the billing ledger
and persists a per-delegation task_steps row with the token + cost split.

Stubs ``_resolve_archetype`` + ``record_llm_cost`` so the branch is exercised
deterministically without a real DB / LLM (the in-DB sum-check lives in the
billing service's own tests). The unit-test default path (workspace_id=None) is
covered in test_dispatch.py — here we assert the production (workspace_id set)
path writes the step and uses the ledger cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
import src.runtime.dispatch as dispatch_mod
from src.agents.tools.delegate import DelegateInput
from src.runtime.dispatch import _LeafSpec, build_leaf_runner
from src.runtime.orchestrator import OrchestratorContext
from src.runtime.sse_publisher import InProcessSSEPublisher
from src.tasks.models import Task, TaskStep


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeLeafOutput:
    body_markdown: str


@dataclass
class _FakeRunResult:
    _output: _FakeLeafOutput
    _usage: _FakeUsage

    @property
    def output(self) -> _FakeLeafOutput:
        return self._output

    def usage(self) -> _FakeUsage:
        return self._usage


class _FakeLeafAgent:
    def __init__(self, body: str, in_tok: int, out_tok: int) -> None:
        self._body, self._in, self._out = body, in_tok, out_tok

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:  # noqa: ARG002
        return _FakeRunResult(
            _output=_FakeLeafOutput(body_markdown=self._body),
            _usage=_FakeUsage(input_tokens=self._in, output_tokens=self._out),
        )


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


def _ctx() -> OrchestratorContext:
    return OrchestratorContext(
        task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        sse_publisher=InProcessSSEPublisher(),
    )


@pytest.mark.asyncio
async def test_leaf_runner_real_cost_and_persists_task_step(monkeypatch: Any) -> None:
    archetype_id = uuid4()
    recorded: dict[str, Any] = {}

    async def _fake_resolve(_session: Any, slug: str) -> Any:
        return SimpleNamespace(
            id=archetype_id, model_provider_slug="deepseek", model_name="deepseek-chat", slug=slug
        )

    async def _fake_record(session: Any, **kwargs: Any) -> tuple[Decimal, Decimal]:
        recorded.update(kwargs)
        return Decimal("0.001234"), Decimal("0.1234")  # (cost_usd, cost_rub)

    monkeypatch.setattr(dispatch_mod, "_resolve_archetype", _fake_resolve)
    monkeypatch.setattr(dispatch_mod, "record_llm_cost", _fake_record)

    session = _FakeSession()
    parent_id, cell_id, user_id, workspace_id = uuid4(), uuid4(), uuid4(), uuid4()
    specs = {
        "researcher": _LeafSpec(build=lambda *, model: _FakeLeafAgent("м", 1000, 2000), deps_factory=dict)
    }
    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
        parent_task_id=parent_id,
        cell_id=cell_id,
        user_id=user_id,
        workspace_id=workspace_id,
        leaf_specs=specs,
    )

    result = await runner(
        DelegateInput(target_agent_slug="researcher", sub_prompt="изучи рынок"), _ctx()
    )

    # record_llm_cost was called with the real token split + tenant ids.
    assert recorded["tokens_in"] == 1000
    assert recorded["tokens_out"] == 2000
    assert recorded["provider"] == "deepseek"  # archetype fallback (model never ran)
    assert recorded["workspace_id"] == workspace_id
    assert recorded["task_id"] == parent_id

    # Cost comes from the ledger (cost_rub), NOT the coarse estimate.
    assert result.cost_credits == Decimal("0.1234")

    # A child Task + exactly one task_steps row were persisted.
    steps = [r for r in session.added if isinstance(r, TaskStep)]
    children = [r for r in session.added if isinstance(r, Task)]
    assert len(children) == 1
    assert len(steps) == 1
    step = steps[0]
    assert step.task_id == parent_id
    assert step.agent_archetype_id == archetype_id
    assert step.step_type == "llm_call"
    assert step.step_index == 0  # ctx.leaf_outputs empty at this point
    assert step.cost_credits == Decimal("0.1234")  # non-zero (AC-W1-2)
    assert step.input_jsonb["tokens_input"] == 1000
    assert step.output_jsonb["tokens_output"] == 2000


@pytest.mark.asyncio
async def test_leaf_runner_step_index_tracks_prior_delegations(monkeypatch: Any) -> None:
    """step_index = count of already-completed delegations (orchestrator appends
    to ctx.leaf_outputs only after each runner call) → unique per parent."""

    async def _fake_resolve(_session: Any, slug: str) -> Any:
        return SimpleNamespace(
            id=uuid4(), model_provider_slug="deepseek", model_name="deepseek-chat", slug=slug
        )

    async def _fake_record(session: Any, **kwargs: Any) -> tuple[Decimal, Decimal]:
        return Decimal("0"), Decimal("0.5")

    monkeypatch.setattr(dispatch_mod, "_resolve_archetype", _fake_resolve)
    monkeypatch.setattr(dispatch_mod, "record_llm_cost", _fake_record)

    session = _FakeSession()
    specs = {
        "writer": _LeafSpec(build=lambda *, model: _FakeLeafAgent("w", 10, 20), deps_factory=dict)
    }
    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        workspace_id=uuid4(),
        leaf_specs=specs,
    )

    ctx = _ctx()
    r1 = await runner(DelegateInput(target_agent_slug="writer", sub_prompt="a"), ctx)
    ctx.leaf_outputs.append(r1)  # mimic the orchestrator's post-call append
    r2 = await runner(DelegateInput(target_agent_slug="writer", sub_prompt="b"), ctx)

    steps = [r for r in session.added if isinstance(r, TaskStep)]
    assert [s.step_index for s in steps] == [0, 1]
    # task.total == sum(steps): orchestrator accumulates these same costs.
    assert sum((s.cost_credits for s in steps), Decimal(0)) == r1.cost_credits + r2.cost_credits
