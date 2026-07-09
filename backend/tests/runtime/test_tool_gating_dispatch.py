"""Unit: capability gate wired into runtime.dispatch.build_leaf_runner (Phase 01.9b).

Proves the live tool-dispatch path is NOT regressed:
  * web_search/read_url still register for the researcher under the real seed
    allowlist (["web_search","read_url"]) AND under an empty/absent allowlist.
  * A non-empty allowlist that omits read_url scopes it out on the live path and
    emits an audit deny row (via the injected sink).
  * resolve_tools_allowed_by_slug is safe against duck-typed fake sessions
    (returns {} instead of raising) so it can't crash dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.tools.delegate import DelegateInput
from src.runtime.dispatch import _LeafSpec, build_leaf_runner, resolve_tools_allowed_by_slug

# ── minimal leaf fakes (mirror tests/runtime/test_dispatch.py) ────────────


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Out:
    body_markdown: str


@dataclass
class _RunResult:
    _o: _Out
    _u: _Usage

    @property
    def output(self) -> _Out:
        return self._o

    def usage(self) -> _Usage:
        return self._u


class _LeafAgent:
    def __init__(self) -> None:
        self.run_prompts: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _RunResult:
        self.run_prompts.append(prompt)
        return _RunResult(_Out("body"), _Usage(1, 1))


class _Deps:
    pass


class _Session:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()


class _FakeDenySink:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

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
        self.calls.append((tool_name, reason))


async def _rec(_session: Any, _billing: Any) -> Decimal:
    return Decimal("0")


async def _native_ws(_q: str) -> str:
    return "web"


async def _native_ru(_q: str) -> str:
    return "url"


def _runner_with(seen: dict[str, Any], **kwargs: Any):
    agent = _LeafAgent()

    def _build(*, model: Any, **build_kwargs: Any) -> Any:
        seen.update(build_kwargs)
        return agent

    specs = {"researcher": _LeafSpec(build=_build, deps_factory=_Deps)}
    return build_leaf_runner(
        llm_router=object(),  # type: ignore[arg-type]
        session=_Session(),  # type: ignore[arg-type]
        parent_task_id=uuid4(),
        cell_id=uuid4(),
        user_id=uuid4(),
        leaf_specs=specs,
        native_web_search=_native_ws,
        step_recorder=_rec,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_web_search_registers_under_real_researcher_allowlist() -> None:
    seen: dict[str, Any] = {}
    runner = _runner_with(
        seen,
        native_read_url=_native_ru,
        tools_allowed_by_slug={"researcher": ["web_search", "read_url"]},
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert seen.get("web_search") is _native_ws
    assert seen.get("read_url") is _native_ru


@pytest.mark.asyncio
async def test_web_search_registers_under_empty_or_absent_allowlist() -> None:
    # Absent map entirely (None) → empty allowlist → READ_ONLY tools pass.
    seen_none: dict[str, Any] = {}
    runner_none = _runner_with(seen_none, native_read_url=_native_ru)
    await runner_none(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert seen_none.get("web_search") is _native_ws
    assert seen_none.get("read_url") is _native_ru

    # Empty allowlist for the slug → same (backward-compat for writer/analyst/[]).
    seen_empty: dict[str, Any] = {}
    runner_empty = _runner_with(
        seen_empty, native_read_url=_native_ru, tools_allowed_by_slug={"researcher": []}
    )
    await runner_empty(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert seen_empty.get("web_search") is _native_ws
    assert seen_empty.get("read_url") is _native_ru


@pytest.mark.asyncio
async def test_non_empty_allowlist_scopes_out_read_url_live_and_audits() -> None:
    seen: dict[str, Any] = {}
    sink = _FakeDenySink()
    runner = _runner_with(
        seen,
        native_read_url=_native_ru,
        tools_allowed_by_slug={"researcher": ["web_search"]},
        tool_deny_audit=sink,
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert seen.get("web_search") is _native_ws
    assert "read_url" not in seen
    assert sink.calls == [("read_url", "not_in_allowlist")]


@pytest.mark.asyncio
async def test_resolve_tools_allowed_by_slug_safe_on_fake_session() -> None:
    # No `.execute` attribute → best-effort resolver returns {} (never raises).
    assert await resolve_tools_allowed_by_slug(_Session(), ["researcher"]) == {}  # type: ignore[arg-type]
    # Empty slugs → {} without touching the session.
    assert await resolve_tools_allowed_by_slug(object(), []) == {}  # type: ignore[arg-type]
