"""Unit tests for runtime.dispatch — inline orchestrator-dispatch wiring.

Phase 00.6 PR-B Commit 1. Covers the Wave-0 deterministic pipeline wiring
that closes the PR-A CRITICAL FINDING (POST /tasks queued-but-never-dispatched).

These tests inject fakes for the LLM layer + DB session so no Pydantic-AI
provider chain or real PostgreSQL is needed. The orchestrator itself is
covered by tests/runtime/test_orchestrator.py — here we test dispatch's own
seams: cost estimate, PlanExecutingCoordinator plan execution (order, guards,
artifact typing from the plan), and the production leaf-runner's child-task
persistence + cost roll-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.coordinator import CoordinatorOutput, DelegationStep
from src.agents.exceptions import DelegationDepthExceeded, DelegationTargetInvalid
from src.agents.tools.delegate import DelegateInput, DelegateResult
from src.mcp.exceptions import WebSearchError
from src.mcp.tools.web_search import WebSearchResult
from src.runtime.dispatch import (
    CREDIT_PER_INPUT_TOKEN,
    CREDIT_PER_OUTPUT_TOKEN,
    PlanExecutingCoordinator,
    _extract_output_text,
    _extract_usage,
    _LeafSpec,
    build_leaf_runner,
    dispatch_task,
    estimate_credits,
    fetch_research_context,
    normalize_artifact_markdown,
    strip_wrapping_fence,
)
from src.tasks.models import Task

# ── estimate_credits ──────────────────────────────────────────────────────


def test_estimate_credits_zero_tokens_is_zero() -> None:
    assert estimate_credits(input_tokens=0, output_tokens=0) == Decimal(0)


def test_estimate_credits_math_matches_constants() -> None:
    got = estimate_credits(input_tokens=1000, output_tokens=2000)
    expected = Decimal(1000) * CREDIT_PER_INPUT_TOKEN + Decimal(2000) * CREDIT_PER_OUTPUT_TOKEN
    assert got == expected


def test_estimate_credits_demo_scale_under_ac10_cap() -> None:
    """A realistic 3-specialist run (~30k in + ~20k out total) must stay
    well under the 30-credit (0.30 USD) AC10 cap."""
    cost = estimate_credits(input_tokens=30_000, output_tokens=20_000)
    assert cost < Decimal(30)


# ── PlanExecutingCoordinator (plan-then-execute) ──────────────────────────


@dataclass
class _FakeDeps:
    runner: Any
    available_agent_slugs: list[str] = field(
        default_factory=lambda: ["researcher", "analyst", "writer"]
    )
    cell_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    current_depth: int = 0
    max_delegation_depth: int = 5


@dataclass
class _PlanResult:
    output: CoordinatorOutput


class _FakeCoordinatorAgent:
    """Stand-in for the real PromptedOutput Coordinator: returns a canned plan."""

    def __init__(self, plan: CoordinatorOutput) -> None:
        self._plan = plan
        self.run_prompts: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _PlanResult:
        self.run_prompts.append(prompt)
        return _PlanResult(output=self._plan)


def _market_brief_plan() -> CoordinatorOutput:
    """The canonical 3-step plan, with artifact types carried IN the plan."""
    return CoordinatorOutput(
        summary="Декомпозиция на research → analyst → writer.",
        delegation_plan=[
            DelegationStep(
                step=1,
                agent="researcher",
                goal="research",
                status="planned",
                artifact_type="matrix",
            ),
            DelegationStep(
                step=2,
                agent="analyst",
                goal="analyze",
                status="planned",
                artifact_type="analysis",
                depends_on=[1],
            ),
            DelegationStep(
                step=3,
                agent="writer",
                goal="write",
                status="planned",
                artifact_type="brief",
                depends_on=[2],
            ),
        ],
    )


def _ok_runner(calls: list[str] | None = None, outputs: list[str] | None = None):
    async def _runner(inp: DelegateInput, _deps: Any) -> DelegateResult:
        if calls is not None:
            calls.append(inp.target_agent_slug)
        if outputs is not None:
            outputs.append(inp.sub_prompt)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output=f"OUT[{inp.target_agent_slug}]",
            cost_credits=Decimal("1.0"),
            tokens_used=10,
        )

    return _runner


@pytest.mark.asyncio
async def test_plan_executing_coordinator_runs_plan_in_order() -> None:
    calls: list[str] = []
    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(_market_brief_plan()))
    result = await coord.run("market brief please", deps=_FakeDeps(runner=_ok_runner(calls=calls)))

    assert calls == ["researcher", "analyst", "writer"]
    assert isinstance(result.output, CoordinatorOutput)
    assert len(result.output.artifacts) == 3
    # AC-W1-24: artifact types come from the PLAN, not a code-side slug → type map.
    assert [a.type for a in result.output.artifacts] == ["matrix", "analysis", "brief"]


@pytest.mark.asyncio
async def test_plan_executing_coordinator_orders_by_depends_on() -> None:
    """Steps given out of order are executed in dependency order."""
    plan = CoordinatorOutput(
        summary="s",
        delegation_plan=[
            DelegationStep(
                step=3, agent="writer", goal="w", status="p", artifact_type="brief", depends_on=[2]
            ),
            DelegationStep(
                step=1, agent="researcher", goal="r", status="p", artifact_type="matrix"
            ),
            DelegationStep(
                step=2,
                agent="analyst",
                goal="a",
                status="p",
                artifact_type="analysis",
                depends_on=[1],
            ),
        ],
    )
    calls: list[str] = []
    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(plan))
    await coord.run("x", deps=_FakeDeps(runner=_ok_runner(calls=calls)))
    assert calls == ["researcher", "analyst", "writer"]


@pytest.mark.asyncio
async def test_plan_executing_coordinator_chains_prior_output_into_sub_prompt() -> None:
    seen_prompts: list[str] = []
    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(_market_brief_plan()))
    await coord.run("исходный запрос", deps=_FakeDeps(runner=_ok_runner(outputs=seen_prompts)))

    # researcher sees only its goal; analyst sees researcher output;
    # writer sees both prior outputs.
    assert "OUT[researcher]" not in seen_prompts[0]
    assert "OUT[researcher]" in seen_prompts[1]
    assert "OUT[researcher]" in seen_prompts[2]
    assert "OUT[analyst]" in seen_prompts[2]


@pytest.mark.asyncio
async def test_plan_executing_coordinator_rejects_out_of_team_slug() -> None:
    """AC-W1-16b: the delegate_task guards re-apply at plan execution."""
    plan = CoordinatorOutput(
        summary="s",
        delegation_plan=[DelegationStep(step=1, agent="hacker", goal="g", status="p")],
    )
    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(plan))
    with pytest.raises(DelegationTargetInvalid):
        await coord.run("x", deps=_FakeDeps(runner=_ok_runner()))


@pytest.mark.asyncio
async def test_plan_executing_coordinator_rejects_over_depth() -> None:
    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(_market_brief_plan()))
    with pytest.raises(DelegationDepthExceeded):
        await coord.run(
            "x", deps=_FakeDeps(runner=_ok_runner(), current_depth=5, max_delegation_depth=5)
        )


# ── build_leaf_runner ─────────────────────────────────────────────────────


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
        self._body = body
        self._in = in_tok
        self._out = out_tok
        self.run_prompts: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _FakeRunResult:
        self.run_prompts.append(prompt)
        return _FakeRunResult(
            _output=_FakeLeafOutput(body_markdown=self._body),
            _usage=_FakeUsage(input_tokens=self._in, output_tokens=self._out),
        )


@dataclass
class _FakeDeps2:
    pass


class _FakeSession:
    """Captures added rows + assigns ids on flush (mimics gen_random_uuid())."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


@pytest.mark.asyncio
async def test_build_leaf_runner_creates_child_task_and_costs() -> None:
    session = _FakeSession()
    parent_id = uuid4()
    cell_id = uuid4()
    user_id = uuid4()

    fake_agent = _FakeLeafAgent("исследование рынка", in_tok=1000, out_tok=2000)
    specs = {
        "researcher": _LeafSpec(
            build=lambda *, model: fake_agent,
            deps_factory=_FakeDeps2,
        )
    }

    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]  # never used — fake build ignores model
        session=session,  # type: ignore[arg-type]
        parent_task_id=parent_id,
        cell_id=cell_id,
        user_id=user_id,
        leaf_specs=specs,
    )

    result = await runner(
        DelegateInput(target_agent_slug="researcher", sub_prompt="изучи рынок"),
        None,  # type: ignore[arg-type]  # OrchestratorContext unused in production runner
    )

    assert result.output == "исследование рынка"
    assert result.tokens_used == 2000
    expected_cost = estimate_credits(input_tokens=1000, output_tokens=2000)
    assert result.cost_credits == expected_cost

    # A child Task row was persisted under the parent + cell.
    assert len(session.added) == 1
    child = session.added[0]
    assert child.parent_task_id == parent_id
    assert child.cell_id == cell_id
    assert child.initiated_by_user_id == user_id
    assert child.status == "succeeded"
    assert child.total_output_tokens == 2000
    assert isinstance(child.id, UUID)
    assert result.sub_task_id == child.id


# ── web_search wiring (Researcher live context) ───────────────────────────


class _FakeSearchTool:
    def __init__(
        self, results: list[WebSearchResult] | None = None, raise_exc: Exception | None = None
    ) -> None:
        self._results = results or []
        self._raise = raise_exc
        self.queries: list[str] = []

    async def search(
        self, query: str, agent_id: str = "system", max_results: int = 10
    ) -> list[WebSearchResult]:
        self.queries.append(query)
        if self._raise is not None:
            raise self._raise
        return self._results[:max_results]


@pytest.mark.asyncio
async def test_fetch_research_context_formats_results() -> None:
    tool = _FakeSearchTool(
        results=[
            WebSearchResult(title="Конкурент А", url="https://a.ru", snippet="AI команды"),
            WebSearchResult(title="Конкурент Б", url="https://b.ru", snippet="боты"),
        ]
    )
    ctx = await fetch_research_context(tool, "рынок AI команд РФ")  # type: ignore[arg-type]
    assert "https://a.ru" in ctx and "https://b.ru" in ctx
    assert "Конкурент А" in ctx
    assert tool.queries == ["рынок AI команд РФ"]


@pytest.mark.asyncio
async def test_fetch_research_context_degrades_on_error() -> None:
    tool = _FakeSearchTool(raise_exc=WebSearchError("no_search_backend_configured"))
    assert await fetch_research_context(tool, "q") == ""  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_fetch_research_context_empty_query_and_no_results() -> None:
    assert await fetch_research_context(_FakeSearchTool(), "") == ""  # type: ignore[arg-type]
    assert await fetch_research_context(_FakeSearchTool(results=[]), "q") == ""  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_build_leaf_runner_prepends_research_context_for_researcher() -> None:
    session = _FakeSession()
    fake_agent = _FakeLeafAgent("матрица", in_tok=100, out_tok=200)
    specs = {"researcher": _LeafSpec(build=lambda *, model: fake_agent, deps_factory=_FakeDeps2)}
    tool = _FakeSearchTool(results=[WebSearchResult(title="X", url="https://x.ru", snippet="s")])

    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs=specs,
        web_search_tool=tool,  # type: ignore[arg-type]
        user_prompt="рынок AI команд РФ",
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="собери матрицу"), None)  # type: ignore[arg-type]

    # The Researcher's actual prompt was augmented with the live search block.
    assert tool.queries == ["рынок AI команд РФ"]
    assert "https://x.ru" in fake_agent.run_prompts[0]
    assert "собери матрицу" in fake_agent.run_prompts[0]


@pytest.mark.asyncio
async def test_build_leaf_runner_native_tool_path_skips_prefetch() -> None:
    """AC-W1-19 (DeepSeek path): when a native web_search callable is supplied the
    Researcher agent is built WITH the tool and the scripted pre-fetch is skipped
    (the sub-prompt is passed through unchanged; the model owns the search loop)."""
    session = _FakeSession()
    fake_agent = _FakeLeafAgent("матрица", in_tok=100, out_tok=200)
    seen_build_kwargs: dict[str, Any] = {}

    def _build(*, model: Any, **kwargs: Any) -> Any:
        seen_build_kwargs.update(kwargs)
        return fake_agent

    specs = {"researcher": _LeafSpec(build=_build, deps_factory=_FakeDeps2)}
    scripted_tool = _FakeSearchTool(
        results=[WebSearchResult(title="X", url="https://x.ru", snippet="s")]
    )

    async def _native_web_search(query: str) -> str:
        return "native result"

    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs=specs,
        web_search_tool=scripted_tool,  # type: ignore[arg-type]  # present but must be ignored
        native_web_search=_native_web_search,
        user_prompt="рынок AI команд РФ",
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="собери матрицу"), None)  # type: ignore[arg-type]

    # The native tool was registered on the agent…
    assert seen_build_kwargs.get("web_search") is _native_web_search
    # …the scripted pre-fetch did NOT run (no queries, prompt unchanged).
    assert scripted_tool.queries == []
    assert fake_agent.run_prompts[0] == "собери матрицу"


def test_router_supports_native_tools_defensive() -> None:
    """The gating helper returns False for routers lacking the predicate
    (the object() stand-in used by no-delegation tests) and honours real ones."""
    from src.runtime.dispatch import _router_supports_native_tools

    class _Yes:
        def would_use_native_tools(self, role_key: str) -> bool:
            return role_key == "researcher"

    class _No:
        def would_use_native_tools(self, role_key: str) -> bool:
            return False

    assert _router_supports_native_tools(object(), "researcher") is False
    assert _router_supports_native_tools(_Yes(), "researcher") is True
    assert _router_supports_native_tools(_Yes(), "writer") is False
    assert _router_supports_native_tools(_No(), "researcher") is False


@pytest.mark.asyncio
async def test_build_native_web_search_formats_and_rate_limits() -> None:
    """The native tool callable formats hits like the scripted path and returns a
    clear note (not an exception) when the rate limit is hit."""
    from src.mcp.exceptions import ToolRateLimitExceeded
    from src.runtime.dispatch import build_native_web_search

    ok_tool = _FakeSearchTool(
        results=[WebSearchResult(title="Конкурент", url="https://c.ru", snippet="боты")]
    )
    fn = build_native_web_search(ok_tool)  # type: ignore[arg-type]
    out = await fn("AI команды")
    assert "https://c.ru" in out and "Конкурент" in out
    assert ok_tool.queries == ["AI команды"]

    limited = _FakeSearchTool(raise_exc=ToolRateLimitExceeded(retry_after=30, detail="x"))
    note = await build_native_web_search(limited)("q")  # type: ignore[arg-type]
    assert "Лимит" in note


@pytest.mark.asyncio
async def test_build_leaf_runner_no_search_tool_uses_plain_subprompt() -> None:
    session = _FakeSession()
    fake_agent = _FakeLeafAgent("матрица", in_tok=100, out_tok=200)
    specs = {"researcher": _LeafSpec(build=lambda *, model: fake_agent, deps_factory=_FakeDeps2)}
    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=session,  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs=specs,
        web_search_tool=None,  # no live search → plain sub-prompt
        user_prompt="рынок",
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="собери матрицу"), None)  # type: ignore[arg-type]
    assert fake_agent.run_prompts[0] == "собери матрицу"


@pytest.mark.asyncio
async def test_build_leaf_runner_unknown_slug_raises() -> None:
    runner = build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=_FakeSession(),  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs={},  # empty → any slug unknown
    )
    with pytest.raises(KeyError):
        await runner(
            DelegateInput(target_agent_slug="nonexistent", sub_prompt="x"),
            None,  # type: ignore[arg-type]
        )


# ── extract helpers (version-tolerant) ────────────────────────────────────


def test_extract_output_text_data_fallback_and_none() -> None:
    @dataclass
    class _OutOnlyData:
        data: Any

    @dataclass
    class _Body:
        body_markdown: str

    # .output missing → falls back to .data
    assert _extract_output_text(_OutOnlyData(data=_Body("from-data"))) == "from-data"

    # both missing → empty string
    @dataclass
    class _Empty:
        pass

    assert _extract_output_text(_Empty()) == ""


def test_extract_usage_request_response_aliases_and_none() -> None:
    @dataclass
    class _OldUsage:
        request_tokens: int
        response_tokens: int

    @dataclass
    class _OldResult:
        def usage(self) -> _OldUsage:
            return _OldUsage(request_tokens=7, response_tokens=11)

    assert _extract_usage(_OldResult()) == (7, 11)

    @dataclass
    class _NoUsage:
        pass

    assert _extract_usage(_NoUsage()) == (0, 0)


# ── markdown normalization (founder session 2026-06-11) ──────────────────

_WRAPPED_DOC = """```markdown
---
artifact_type: brief
assumptions: [запуск в мае 2026]
---

# Бриф

Текст брифа.

### Пост 1 — Telegram — Пн

```python
print("inner code block survives")
```

**Structured summary:**

```
artifact_path: brief.md
key_messages: ["раз", "два"]
gaps: []
```
```
"""


def test_strip_wrapping_fence_unwraps_whole_doc_fence() -> None:
    assert strip_wrapping_fence("```markdown\n# Бриф\n\nТекст.\n```") == "# Бриф\n\nТекст."
    assert strip_wrapping_fence("```\n# Бриф\n```") == "# Бриф"


def test_strip_wrapping_fence_keeps_inner_fences_untouched() -> None:
    # A leading fence that closes early (interior fences) is NOT a wrapper.
    text = "```markdown\n# Doc\n```\n\nостальной текст"
    assert strip_wrapping_fence(text) == text
    plain = "# Doc\n\n```python\nprint(1)\n```"
    assert strip_wrapping_fence(plain) == plain


def test_strip_wrapping_fence_idempotent() -> None:
    once = strip_wrapping_fence("```markdown\n# Бриф\nТекст.\n```")
    assert strip_wrapping_fence(once) == once


def test_normalize_artifact_markdown_strips_frontmatter_and_summary() -> None:
    out = normalize_artifact_markdown(_WRAPPED_DOC)
    # Wrapper meta gone…
    assert "artifact_type" not in out
    assert "artifact_path" not in out
    assert "Structured summary" not in out
    # …human document intact, including the AC9 post heading + inner code.
    assert out.startswith("# Бриф")
    assert "### Пост 1 — Telegram — Пн" in out
    assert 'print("inner code block survives")' in out


def test_normalize_artifact_markdown_idempotent_and_plain_passthrough() -> None:
    out = normalize_artifact_markdown(_WRAPPED_DOC)
    assert normalize_artifact_markdown(out) == out
    plain = "# Просто документ\n\nБез обёрток."
    assert normalize_artifact_markdown(plain) == plain


def test_normalize_artifact_markdown_keeps_non_summary_trailing_fence() -> None:
    text = "# Doc\n\n```python\nprint(2)\n```"
    assert normalize_artifact_markdown(text) == text


@pytest.mark.asyncio
async def test_plan_executing_coordinator_artifact_clean_but_context_keeps_meta() -> None:
    """prior_context keeps the role-contract meta; the user-facing artifact doesn't."""
    seen_prompts: list[str] = []
    meta_doc = (
        "---\nartifact_type: research-pack\n---\n\n# Research summary\n\nФакты.\n\n"
        "```\nartifact_path: pack.md\nkey_messages: [x]\n```"
    )

    async def _runner(inp: DelegateInput, _deps: Any) -> DelegateResult:
        seen_prompts.append(inp.sub_prompt)
        return DelegateResult(
            sub_task_id=uuid4(),
            target_agent_slug=inp.target_agent_slug,
            output=meta_doc,
            cost_credits=Decimal(0),
            tokens_used=0,
        )

    coord = PlanExecutingCoordinator(coordinator_agent=_FakeCoordinatorAgent(_market_brief_plan()))
    result = await coord.run("запрос", deps=_FakeDeps(runner=_runner))

    # Downstream agents still see the frontmatter + summary block…
    assert "artifact_type: research-pack" in seen_prompts[1]
    assert "artifact_path: pack.md" in seen_prompts[1]
    # …while every materialized artifact is clean.
    for artifact in result.output.artifacts:
        assert "artifact_type" not in artifact.path_or_inline
        assert "artifact_path" not in artifact.path_or_inline
        assert "# Research summary" in artifact.path_or_inline


# ── dispatch_task wiring ──────────────────────────────────────────────────


class _DispatchSession:
    """Session shim for dispatch_task: get(Task) + add/flush."""

    def __init__(self, task: Task) -> None:
        self._task = task
        self.added: list[Any] = []

    async def get(self, _model: Any, _task_id: UUID) -> Task:
        return self._task

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


class _NoDelegationCoordinator:
    """Coordinator stand-in that returns directly without delegating —
    keeps dispatch_task's orchestrator path off the real LLM layer."""

    async def run(self, _user_prompt: str, *, deps: Any) -> Any:
        return _NoDelegationCoordinator._Result()

    @dataclass
    class _Result:
        output: CoordinatorOutput = field(
            default_factory=lambda: CoordinatorOutput(summary="scripted no-op")
        )


@pytest.mark.asyncio
async def test_dispatch_task_runs_orchestrator_and_returns_output() -> None:
    task_id = uuid4()
    task = Task(
        cell_id=uuid4(),
        initiated_by_user_id=uuid4(),
        title="parent",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "market brief"},
    )
    task.id = task_id
    task.total_cost_credits = Decimal(0)
    task.total_input_tokens = 0
    task.total_output_tokens = 0
    session = _DispatchSession(task)

    from src.runtime.sse_publisher import InProcessSSEPublisher

    publisher = InProcessSSEPublisher()

    result = await dispatch_task(
        task=task,
        session=session,  # type: ignore[arg-type]
        llm_router=object(),  # type: ignore[arg-type]  # never used — coordinator never delegates
        sse_publisher=publisher,
        coordinator=_NoDelegationCoordinator(),  # type: ignore[arg-type]
    )

    assert result["summary"] == "scripted no-op"
    assert task.status == "succeeded"
    drained = publisher._drain.get(task_id, [])
    assert [ev.event_type for ev in drained] == ["task.started", "task.completed"]
