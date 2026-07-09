"""Unit: connector tools threaded through dispatch.build_leaf_runner + the gate.

Proves the 01.9b wiring seam (AC-01.9b.3/.4): a connector READ tool is attached
to a leaf whose archetype ``tools_allowed`` lists it, DENIED (not attached, audit
row emitted) for a leaf that does not, and a DANGEROUS ``send_*`` tool is denied
regardless of the allowlist. Uses a fake leaf spec whose builder accepts a
``connector_tools`` kwarg (the horizontal builders do not — that attachment is
01.10's vertical-archetype job).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.agents.tools.delegate import DelegateInput
from src.runtime.dispatch import _LeafSpec, build_leaf_runner


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
    async def run(self, prompt: str, *, deps: Any) -> _RunResult:
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


async def _tg_read(_q: str) -> str:
    return "updates"


async def _send(_q: str) -> str:  # pragma: no cover - never invoked (gate denies)
    return "sent"


def _runner(seen: dict[str, Any], sink: _FakeDenySink, **kwargs: Any) -> Any:
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
        step_recorder=_rec,
        tool_deny_audit=sink,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_connector_tool_attached_when_archetype_lists_it() -> None:
    seen: dict[str, Any] = {}
    sink = _FakeDenySink()
    runner = _runner(
        seen,
        sink,
        connector_tools={"telegram_read_updates": _tg_read},
        tools_allowed_by_slug={"researcher": ["telegram_read_updates"]},
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert seen.get("connector_tools") == {"telegram_read_updates": _tg_read}
    assert sink.calls == []


@pytest.mark.asyncio
async def test_connector_tool_denied_when_archetype_omits_it() -> None:
    seen: dict[str, Any] = {}
    sink = _FakeDenySink()
    runner = _runner(
        seen,
        sink,
        connector_tools={"telegram_read_updates": _tg_read},
        tools_allowed_by_slug={"researcher": ["web_search"]},
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert "connector_tools" not in seen
    assert sink.calls == [("telegram_read_updates", "not_in_allowlist")]


@pytest.mark.asyncio
async def test_dangerous_send_tool_denied_even_if_listed() -> None:
    seen: dict[str, Any] = {}
    sink = _FakeDenySink()
    runner = _runner(
        seen,
        sink,
        connector_tools={"send_telegram": _send},
        tools_allowed_by_slug={"researcher": ["send_telegram"]},
    )
    await runner(DelegateInput(target_agent_slug="researcher", sub_prompt="p"), None)  # type: ignore[arg-type]
    assert "connector_tools" not in seen
    assert sink.calls == [("send_telegram", "requires_approval")]
