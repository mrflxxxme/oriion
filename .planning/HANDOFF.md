# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-24 (**Phase 01.4b — Memory auto-extraction, ADR-011 Wave-1 completion**)
- Session: `tender-clarke-a1cd06`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. 01.1-retro ✅ · 01.2 Master-Agent core ✅ · 01.3 Billing core ✅ · 01.4 Memory ✅ · **01.4b Memory auto-extraction ✅ code-complete + live-validated (this PR).**
- **What this PR delivers:** the **automatic** half of ADR-011 Wave-1 memory — a post-task **filter-agent** (on `succeeded` → distills durable cell knowledge → `memory.memory_entries(source='filter_agent')`) + an **LLM conversation summarizer** (`LLMConversationSummarizer`, overflow → `kind='conversation_summary'`), both billed as `task_steps` via a new horizontal **`memory_curator`** archetype (`role_category='analyzer'`, no CHECK migration; `step_type='llm_call'`). Orchestrator **`memory_extraction` seam** (mirror of `quota_admission`; success **pre-final-write**; cost folds into the per-task cap + step-sum; never rejects; best-effort swallow), worker (`actor.py`) wires the real hook. **Closes AC-01.4.7** (both triggers) + the AC-01.4.6 summarizer impl → **01.4 fully ✅**.
- **Branch:** `claude/tender-clarke-a1cd06` (off `origin/main` = `b5293a0`, which already includes #71+#72). Focused PR → `main` → founder-merge.
- ⚠️ **Dual-tree guard:** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`.

## Active blockers (none block 01.4b)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## What just happened — Phase 01.4b (2026-06-24)

Founder-process: F1 preflight (PR #71/#72 merged-check; Docker started by founder; funded `.env` copied from `goofy-darwin`, gitignored) → bootstrap-from-worktree + dual-tree guard → grill (7 forks via AskUserQuestion, 4+3) → plan pinned in-session (TaskList) + founder «приступай» → execute (7 atomic commits) → 3-lens multiagent adversarial audit → local CI green → exit ritual → focused PR.

**Grill decisions (2026-06-24):** Q1 **`memory_curator`/`analyzer`** archetype (no migration) · Q2 **two agents, deepseek-chat** · Q3 **summarizer-impl-only** (turn-capture producer → follow-up) · Q4 **`succeeded`-only**, all verticals · Q5 **fold in-cap, never reject** · Q6 **in-process live golden now** (worker transport → Linux) · Q7 **final deliverable + user_prompt**.

**Implemented (7 commits C1–C7):** C1 `agents/memory_curator.py` (`MemoryExtraction` + summarizer factories + roles → deepseek-chat) · C2 `agents/seed_data/memory_curator_v1.py` (archetype seed + `provision_team` wiring) · C3 `runtime/memory_extraction.py` (`MemoryExtractor` + `build_memory_extraction_hook` + `LLMConversationSummarizer`) + `record_memory_call_step` (dispatch) · C4 orchestrator `memory_extraction` seam + token reconciliation · C5 worker wires the real hook · C6 real-PG integration (filter→entries, summarize→summary, **billing invariant**) · C7 `scripts/live_golden_memory.py`.

**Billing invariant preserved:** entries written first, step billed last, cost folded only on clean return → `task.total_cost_credits == SUM(task_steps.cost_credits)` (dedicated real-PG regression test; the memory step counted once, `step_index = len(leaf)+2` collision-free vs leaves 1..N + Master synthesis N+1).

## Verification state

- **CI-equivalent, all green (local):** `ruff check` + `ruff format --check` (364) ✓ · `mypy --strict src` **194 files** ✓ · unit `pytest -m "not integration and not live"` **785 passed, 1 skipped** · integration `pytest -m "integration and not live"` **46 passed** (real PG; +3 memory-extraction) · per-module **`src/memory` 88.77%** (≥85) + new modules curator 100% / seed 100% / extraction 99% · `bandit -r src` **0**.
- **Live golden** (`scripts/live_golden_memory.py`, funded DeepSeek): **5/5**, GATE PASS, ~$0.001 — live `deepseek-chat` returns a parseable `MemoryExtraction` via PromptedOutput (rich → `should_remember=True` 5 typed entries; trivial → `should_remember=False`; summarizer → digest). In-process single-loop (Windows redis-per-loop / one-task-per-worker flake sidestepped; transport proven on Linux PR #64/#65 + `live_golden_worker_billing.py`).
- **Adversarial audit (3 lenses, 3 independent reviewers, refute-by-default):** **0 P0 / 0 current-P1** — **SOUND / SECURE / NO-REGRESSIONS**. Fixes: content-safe failure log (`error_type` not `str(exc)`); `MemoryCallBilling` docstring (`step_type='llm_call'`); cross-file step-index contract note. 2 pre-existing P2/P3 (`_extract_usage` zero-token; `delete_by_id` defense-in-depth) → chip `task_e980ab7b`.
- **8 AC-01.4b.x green** — see [`phases/01.4b-memory-auto-extraction.md`](./roadmap/wave-1-core-mvp/phases/01.4b-memory-auto-extraction.md). **01.4 now fully ✅** (AC-01.4.7 PARTIAL → ✅; AC-01.4.6 summarizer impl ✅).
- **NOT run (deferred):** the conversation-turn **producer** (capture agent-turns during a task) + the Dramatiq+Redis **worker-transport** live golden on Windows (→ CI/Linux). The PR's GitHub Actions (ci-backend / ci-security) is the binding gate at founder-merge.

## Next actions (founder)

1. **Merge** the focused PR (`claude/tender-clarke-a1cd06` → `main`).
2. **Carry-over follow-ups:** conversation-turn **producer** (so summarize-on-overflow fires in prod) · Windows worker-transport live golden → CI/Linux · `01.4-ui` («Что помнит [агент]» panel) · chip `task_e980ab7b` (`_extract_usage` zero-token + `delete_by_id` cell filter).
3. Still open: **01.3b ЮKassa** (OQ-02/OQ-19) · Master-**through-worker** live golden · F1-B ADR-026 evaluator.

## Next phase

**Phase 01.5 — Артефакты** ([ADR-012](./decisions/ADR-012-artifacts.md)): Yjs-документы + S3-ассеты + citeable `artifact://` URLs. (Memory `conversation_summary` + cell/role memory are available for artifact provenance + RAG in later phases; the auto filter-agent now populates cell memory from succeeded tasks.)
