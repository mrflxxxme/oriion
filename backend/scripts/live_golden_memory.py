"""Live golden for memory auto-extraction (Phase 01.4b) — in-process, real DeepSeek.

Validates the NEW filter-agent + summarizer LLM contract against the live model
WITHOUT the docker worker stack (no PG/Redis — this exercises the part green
unit/integration tests cannot cover: does live ``deepseek-chat`` actually return a
parseable ``MemoryExtraction`` via ``PromptedOutput``?).

Coverage split (grill Q6, 2026-06-24): the DB-write + real-ledger billing path is
covered on real PG by ``tests/runtime/test_memory_extraction_integration.py``; the
Dramatiq + Redis-SSE worker TRANSPORT is proven on Linux (PR #64/#65) +
``scripts/live_golden_worker_billing.py`` and deferred on Windows (the documented
one-task-per-worker stall). This golden covers the remaining gap — the live LLM
contract of the new agents — robustly in a single event loop.

  1. filter-agent on a knowledge-rich deliverable → parseable MemoryExtraction,
     should_remember=True with >=1 atomic entry (kind in fact/note/glossary);
  2. filter-agent on a trivial deliverable → parseable MemoryExtraction (the gate
     is that it PARSES; should_remember=False is the expected heuristic signal);
  3. summarizer → non-empty free-text digest.

Run (funded backend/.env, NEVER committed):
    uv run --directory backend python scripts/live_golden_memory.py
Cost: a few DeepSeek calls (~$0.01). Prints PASS/FAIL; no DB writes.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any
from uuid import uuid4

from src._shared.config import get_settings
from src.agents.memory_curator import (
    ROLE_KEY_MEMORY_FILTER,
    ROLE_KEY_MEMORY_SUMMARY,
    MemoryCuratorDeps,
    MemoryExtraction,
    build_conversation_summarizer_agent,
    build_memory_extraction_agent,
)
from src.llm_gateway.factory import build_llm_router
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel
from src.runtime.memory_extraction import _compose_extraction_prompt

# Windows console (cp1251) cannot encode Cyrillic / math glyphs via print(); force
# UTF-8 so the live RU output renders instead of raising UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_USER_PROMPT = "Подготовь конкурентный анализ для нашего бренда кофеен в Казани."
_RICH_DELIVERABLE = (
    "Итоги анализа: бренд «КофеКазань» работает в Казани, 4 точки, ЦА 18-30 лет, "
    "бюджет ~150к ₽/мес. Основной конкурент — сеть «Бариста-Х» (12 точек). "
    "Ключевая метрика — CTR (click-through rate) по таргету VK. Договорились "
    "запускать акции по вторникам. Маркировка рекламы через ОРД обязательна."
)
_TRIVIAL_DELIVERABLE = "Привет! Спасибо за обращение. Хорошего дня."
_MESSAGES = [
    "Пользователь: запусти кампанию для кофейни.",
    "Агент: уточните бюджет и города.",
    "Пользователь: 150к в месяц, Казань.",
    "Агент: предлагаю VK-таргет + Telegram-канал, старт со вторника.",
    "Пользователь: согласен, маркировку через ОРД не забудьте.",
]


def _usage(run: Any) -> tuple[int, int]:
    attr = getattr(run, "usage", None)
    u = attr() if callable(attr) else attr  # method (deprecated) or property
    if u is None:
        return 0, 0
    i = getattr(u, "input_tokens", None) or getattr(u, "request_tokens", None) or 0
    o = getattr(u, "output_tokens", None) or getattr(u, "response_tokens", None) or 0
    return int(i), int(o)


async def main() -> int:
    settings = get_settings()
    if not settings.deepseek_api_key.get_secret_value():
        print("FAIL: DEEPSEEK_API_KEY not set in env — cannot run live golden.")
        return 2

    router = build_llm_router(settings).router
    deps = MemoryCuratorDeps(cell_id=uuid4(), task_id=uuid4())
    filter_model = LLMGatewayModel(role_key=ROLE_KEY_MEMORY_FILTER, llm_router=router)
    filter_agent = build_memory_extraction_agent(model=filter_model)
    summ_model = LLMGatewayModel(role_key=ROLE_KEY_MEMORY_SUMMARY, llm_router=router)
    summ_agent = build_conversation_summarizer_agent(model=summ_model)

    results: list[tuple[str, bool]] = []
    tok_in = tok_out = 0

    # ── 1. rich deliverable → should_remember + entries ───────────────────
    print("=" * 70)
    print("[1] filter-agent on a knowledge-rich deliverable")
    run = await filter_agent.run(
        _compose_extraction_prompt(_USER_PROMPT, _RICH_DELIVERABLE), deps=deps
    )
    verdict = run.output
    i, o = _usage(run)
    tok_in += i
    tok_out += o
    parse_ok = isinstance(verdict, MemoryExtraction)
    results.append(("rich: parseable MemoryExtraction", parse_ok))
    rich_remember = parse_ok and verdict.should_remember and len(verdict.entries) >= 1
    results.append(("rich: should_remember + >=1 entry", bool(rich_remember)))
    if parse_ok:
        results.append(
            (
                "rich: entry kinds valid",
                all(e.kind in ("fact", "note", "glossary") for e in verdict.entries),
            )
        )
        print(
            f"    provider/model: {filter_model._last_provider_slug}/{filter_model._last_model_name}"
        )
        print(f"    should_remember={verdict.should_remember} entries={len(verdict.entries)}")
        for e in verdict.entries[:5]:
            print(f"      - [{e.kind}] {e.content[:90]}")
    print(f"    tokens in={i} out={o}")

    # ── 2. trivial deliverable → parses (should_remember=False expected) ──
    print("=" * 70)
    print("[2] filter-agent on a trivial deliverable (gate = parses)")
    run2 = await filter_agent.run(
        _compose_extraction_prompt("Поздоровайся.", _TRIVIAL_DELIVERABLE), deps=deps
    )
    v2 = run2.output
    i, o = _usage(run2)
    tok_in += i
    tok_out += o
    parse2 = isinstance(v2, MemoryExtraction)
    results.append(("trivial: parseable MemoryExtraction", parse2))
    if parse2:
        print(f"    should_remember={v2.should_remember} entries={len(v2.entries)}")
    print(f"    tokens in={i} out={o}")

    # ── 3. summarizer → non-empty digest ─────────────────────────────────
    print("=" * 70)
    print("[3] summarizer on an overflowing window")
    run3 = await summ_agent.run("\n".join(f"- {m}" for m in _MESSAGES), deps=deps)
    summary = str(run3.output)
    i, o = _usage(run3)
    tok_in += i
    tok_out += o
    summ_ok = len(summary.strip()) > 30
    results.append(("summary: non-empty digest", summ_ok))
    print(f"    provider/model: {summ_model._last_provider_slug}/{summ_model._last_model_name}")
    print(f"    summary[:200]: {summary.strip()[:200]}")
    print(f"    tokens in={i} out={o}")

    # ── summary ────────────────────────────────────────────────────────────
    print("=" * 70)
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    cost_usd = tok_in * 0.27e-6 + tok_out * 1.10e-6
    print(
        f"\nSUMMARY: {passed}/{len(results)} checks | "
        f"tokens in={tok_in} out={tok_out} | est. cost ~ ${cost_usd:.4f}"
    )
    # GATE = the structured-output contract (both filter parses + summary text);
    # should_remember values are heuristic live signals, not a hard gate.
    gate_ok = parse_ok and parse2 and summ_ok
    print(f"GATE (filter structured-output + summarizer contract): {'PASS' if gate_ok else 'FAIL'}")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
