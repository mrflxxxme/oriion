"""Unit: MemoryExtractor + LLMConversationSummarizer (Phase 01.4b C3).

Injected fakes (no PG / no provider): asserts the should_remember gate, the
billing-as-step (phase + step_index), the Q7 prompt shape, and the summarizer
adapter. The real-ledger ``record_memory_call_step`` + summarize-on-overflow are
exercised against PG in ``tests/runtime/test_memory_extraction_integration.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from src.agents.memory_curator import MemoryCallBilling, MemoryExtraction, MemoryExtractionEntry
from src.runtime.memory_extraction import LLMConversationSummarizer, MemoryExtractor


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeRun:
    output: Any
    _usage: _FakeUsage

    def usage(self) -> _FakeUsage:
        return self._usage


class _FakeModel:
    _last_provider_slug = "deepseek"
    _last_model_name = "deepseek-chat"


class _FakeAgent:
    def __init__(self, output: Any, *, in_tok: int = 80, out_tok: int = 40) -> None:
        self._output = output
        self._in = in_tok
        self._out = out_tok
        self.model = _FakeModel()
        self.prompts: list[str] = []

    async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
        self.prompts.append(prompt)
        return _FakeRun(self._output, _FakeUsage(self._in, self._out))


class _FakeCellMemory:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []

    async def add(self, *, content: str, kind: str = "fact", source: str = "manual", **kw: Any):
        self.added.append({"content": content, "kind": kind, "source": source, **kw})
        return object(), False


class _Recorder:
    def __init__(self, cost: Decimal = Decimal("0.5")) -> None:
        self.billings: list[MemoryCallBilling] = []
        self._cost = cost

    async def __call__(self, _session: Any, billing: MemoryCallBilling) -> Decimal:
        self.billings.append(billing)
        return self._cost


def _extractor(
    agent: _FakeAgent, recorder: _Recorder, cell_memory: _FakeCellMemory
) -> MemoryExtractor:
    return MemoryExtractor(
        session=object(),  # type: ignore[arg-type]
        cell_id=uuid4(),
        user_id=uuid4(),
        task_id=uuid4(),
        workspace_id=uuid4(),
        cell_memory=cell_memory,  # type: ignore[arg-type]
        user_prompt="Сделай конкурентный анализ",
        agent=agent,
        recorder=recorder,
    )


@pytest.mark.asyncio
async def test_extract_writes_entries_and_bills_when_should_remember() -> None:
    verdict = MemoryExtraction(
        should_remember=True,
        entries=[
            MemoryExtractionEntry(content="Клиент работает на рынке РФ.", kind="fact"),
            MemoryExtractionEntry(
                content="CTR — click-through rate.", kind="glossary", title="CTR"
            ),
        ],
    )
    agent = _FakeAgent(verdict)
    cell_memory = _FakeCellMemory()
    recorder = _Recorder(cost=Decimal("0.7"))

    cost, in_tok, out_tok = await _extractor(agent, recorder, cell_memory).extract(
        "Итоговый отчёт.", step_index=5
    )

    assert cost == Decimal("0.7")
    assert (in_tok, out_tok) == (80, 40)  # tokens returned for the task rollup
    # both entries persisted to cell memory, tagged source='filter_agent'
    assert len(cell_memory.added) == 2
    assert all(a["source"] == "filter_agent" for a in cell_memory.added)
    assert {a["kind"] for a in cell_memory.added} == {"fact", "glossary"}
    # exactly one billing step, phase + index + tokens threaded through
    assert len(recorder.billings) == 1
    billing = recorder.billings[0]
    assert billing.phase == "extraction"
    assert billing.step_index == 5
    assert (billing.input_tokens, billing.output_tokens) == (80, 40)
    assert billing.provider_slug == "deepseek"
    # Q7: the prompt carries BOTH the user request and the final deliverable
    assert "Сделай конкурентный анализ" in agent.prompts[0]
    assert "Итоговый отчёт." in agent.prompts[0]


@pytest.mark.asyncio
async def test_extract_bills_but_writes_nothing_when_not_should_remember() -> None:
    agent = _FakeAgent(MemoryExtraction(should_remember=False, entries=[]))
    cell_memory = _FakeCellMemory()
    recorder = _Recorder()

    cost, _in_tok, _out_tok = await _extractor(agent, recorder, cell_memory).extract(
        "x", step_index=3
    )

    assert cost == Decimal("0.5")
    assert cell_memory.added == []  # nothing remembered
    assert len(recorder.billings) == 1  # but the LLM call is still billed
    assert recorder.billings[0].step_index == 3


@pytest.mark.asyncio
async def test_extract_rejects_wrong_output_type_without_billing() -> None:
    agent = _FakeAgent("not a verdict")
    recorder = _Recorder()
    cell_memory = _FakeCellMemory()

    with pytest.raises(TypeError):
        await _extractor(agent, recorder, cell_memory).extract("x", step_index=1)

    # a bad verdict raises before the step is written → nothing billed, no entries
    assert recorder.billings == []
    assert cell_memory.added == []


@pytest.mark.asyncio
async def test_summarizer_returns_agent_text() -> None:
    class _FakeSummAgent:
        def __init__(self, text: str) -> None:
            self.text = text
            self.prompts: list[str] = []

        async def run(self, prompt: str, *, deps: Any) -> _FakeRun:
            self.prompts.append(prompt)
            return _FakeRun(self.text, _FakeUsage(10, 20))

    summarizer = LLMConversationSummarizer(cell_id=uuid4(), agent=_FakeSummAgent("Резюме диалога."))
    out = await summarizer.summarize(["сообщение один", "сообщение два"])
    assert out == "Резюме диалога."


# ── build-agent (production path) + .data fallback coverage ────────────────


def _bare_extractor(**over: Any) -> MemoryExtractor:
    kw: dict[str, Any] = {
        "session": object(),
        "cell_id": uuid4(),
        "user_id": uuid4(),
        "task_id": uuid4(),
        "workspace_id": uuid4(),
        "cell_memory": _FakeCellMemory(),
        "user_prompt": "p",
    }
    kw.update(over)
    return MemoryExtractor(**kw)  # type: ignore[arg-type]


def test_extractor_build_agent_requires_router_or_agent() -> None:
    with pytest.raises(ValueError, match="llm_router or an injected agent"):
        _bare_extractor(llm_router=None, agent=None)._build_agent()


def test_extractor_build_agent_from_router() -> None:
    """Production path: build a real Agent from the router (no network at build)."""
    agent, model = _bare_extractor(llm_router=object())._build_agent()
    assert agent is not None
    assert model is not None


def test_summarizer_build_agent_requires_router_or_agent() -> None:
    with pytest.raises(ValueError, match="llm_router or an injected agent"):
        LLMConversationSummarizer(cell_id=uuid4())._build_agent()


def test_summarizer_build_agent_from_router() -> None:
    assert (
        LLMConversationSummarizer(cell_id=uuid4(), llm_router=object())._build_agent() is not None
    )


class _DataRun:
    """A run exposing ``.data`` (older pydantic-ai) with ``.output`` None."""

    output = None

    def __init__(self, data: Any) -> None:
        self.data = data

    def usage(self) -> _FakeUsage:
        return _FakeUsage(1, 1)


@pytest.mark.asyncio
async def test_extract_reads_data_when_output_none() -> None:
    class _DataAgent:
        model = _FakeModel()

        async def run(self, _p: str, *, deps: Any) -> _DataRun:
            return _DataRun(MemoryExtraction(should_remember=False))

    cost, _i, _o = await _bare_extractor(agent=_DataAgent(), recorder=_Recorder()).extract(
        "x", step_index=1
    )
    assert cost == Decimal("0.5")  # verdict parsed from the .data fallback


@pytest.mark.asyncio
async def test_summarizer_reads_data_when_output_none() -> None:
    class _DataAgent:
        async def run(self, _p: str, *, deps: Any) -> _DataRun:
            return _DataRun("резюме из data")

    out = await LLMConversationSummarizer(cell_id=uuid4(), agent=_DataAgent()).summarize(["m"])
    assert out == "резюме из data"
