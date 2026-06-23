# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-23 (**Phase 01.4 — Memory, ADR-011 Wave-1**)
- Session: `dazzling-shamir-c26b51`
- Agent: @claude-opus

## Project status

- **Wave:** Wave 1 (Core MVP) — **in progress**. 01.1-retro ✅ · 01.2 Master-Agent core ✅ · 01.3 Billing core ✅ · **01.4 Memory ✅ code-complete + locally verified (this PR).**
- **What this PR delivers:** two-level memory (ADR-011 Wave-1) — **cell memory** + **role memory** (store/search/CRUD API, RLS, 256-dim Yandex embeddings + HNSW cosine, advisory soft caps) + **conversation history** (FIFO N=50 + summarize-on-overflow seam) + the manual **«запомни»** trigger. Single `memory` schema + `cell_id` + FORCE-RLS. **Focused-split scope** (grill 2026-06-23): the **automatic** filter-agent + LLM summarizer + orchestrator post-task wiring → follow-up **`01.4b`**.
- **Branch:** `claude/dazzling-shamir-c26b51` (off `origin/main` = `b92a8d7`). Focused PR → `main` → founder-merge.
- ⚠️ **Dual-tree guard:** canon `.planning/` is in the **worktree**; the outer `…/TEAMLY_RU/.planning` is stale. Anchor to `git rev-parse --show-toplevel`.

## Active blockers (none block 01.4 memory)

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | gates **01.3b ЮKassa** live-flip |
| OQ-19 | Открытие ЮKassa (5–10 дн) | Founder + бухгалтер | gates **01.3b ЮKassa** test→live |
| OQ-32 / OQ-33 | Telegram Business consent-UX + 152-ФЗ + РКН | Founder + юрист | gates **Phase 01.11** |

## What just happened — Phase 01.4 (2026-06-23)

Founder-process: F1 follow-ups → bootstrap-from-worktree + dual-tree guard → grill (7 forks via AskUserQuestion, 4+3 — tool caps at 4/call) → plan (pinned in-session) → execute (7 atomic commits) → multiagent adversarial audit → local CI green → exit ritual → focused PR.

**F1 (before 01.4):** Docker up + funded `.env` (DeepSeek+**Yandex**+GigaChat, copied from the `goofy-darwin` worktree, gitignored). **F1-A re-run green:** in-process Master golden `scripts/live_golden_master.py` **7/7** vs live DeepSeek at HEAD (~$0.0147). Master-**through-worker** still not run (no script; needs vertical-cell provisioning) — non-blocking. F1-B (ADR-026 evaluator) = separate phase.

**Grill decisions (2026-06-23):** Q1 **Yandex 256-dim** (ADR's "1024" was wrong; GigaChat embeddings NotImplemented; Yandex funded+coded) · Q2 **conversation history IN** Wave-1 · Q3 **single `memory` schema + RLS** (not per-cell) · Q4 **retrieval API only** (no RAG-inject) · Q5 filter-agent **both** triggers · Q6 **backend+API only** (UI→`01.4-ui`) · Q7 **soft caps 500/cell·200/role** + no TTL until delete.

**Implemented (ADR-011 Wave-1 slice, 7 commits):**
- `memory/0001_memory_core` (memory_entries + role_memory_entries; FORCE-RLS `_shared.current_cell_id()`; `vector(256)` + HNSW `vector_cosine_ops`) + `memory/0002_conversation_history` (per cell+agent; **`seq` IDENTITY** for FIFO — `now()` ties within a tx).
- `memory.models`/`schemas`/`exceptions` + `repositories/` (cosine `<=>` search, RETURNING delete-existence) + `services/` (injectable `Embedder` port + `GatewayEmbedder` asymmetric doc/query, failover→`EmbeddingUnavailable`; cell/role services embed-on-store + advisory soft caps + delete→404; `ConversationHistoryService` FIFO + summarize-on-overflow via injected port).
- `routers/memory.py` (`/api/v1/memory*` cell+role CRUD/search; cell from RLS tenant context not client; manual POST=«запомни»; `X-Memory-Soft-Cap-Exceeded` header; **vectors never serialized**) + `deps.py` + `main.py` (`MemoryError` RFC-7807 + router) + new `get_current_workspace_id` tenant dep.
- `tests/memory/` unit + **integration (real PG)** + a narrow `filterwarnings` ignore (Windows pytest-asyncio loop-GC artifact; Linux CI unaffected).

**Focused-split (per `infra-pr-scope-prefers-focused-splits`):** the **filter-agent auto-after-task trigger** balloons (`task_steps.agent_archetype_id` NOT-NULL FK → archetype seed + orchestrator hot-path + flaky-Windows live validation) → **`01.4b — memory auto-extraction`**. Mechanism ships (summarizer = injected port; explicit «запомни» delivered). **AC-01.4.7 = PARTIAL.** Orchestrator/billing path untouched → billing invariant structurally intact.

## Verification state

- **CI-equivalent, all green (local):** `ruff check src tests` + `ruff format --check` ✓ (356) · `mypy --strict src` **191 files** ✓ · unit `pytest -m "not integration and not live"` **768 passed, 1 skipped** · integration `pytest -m "integration and not live"` **44 passed** (real testcontainers PG; +4 memory: embedding round-trip + RLS isolation cell-A↛cell-B + role agent-scoping + conversation FIFO under `oriion_app`) · per-module **memory 88.14%** (≥85) · `bandit -r src` **0 issues**.
- **Adversarial audit (3 lenses):** 0 P0 / 0 P1 — SOUND / SECURE / NO-REGRESSIONS. Diff purely additive (+2261, 0 deletions). 3 P3 hardening nits → backlog (embedder dim-validation; 2 security nits).
- **9 AC-01.4.x green + 1 PARTIAL** — see [`phases/01.4-memory.md`](./roadmap/wave-1-core-mvp/phases/01.4-memory.md).
- **Billing-инвариант сохранён:** the diff does not touch `runtime`/`billing`/`billing_service` → step-sum cost authority structurally untouched.
- **NOT run (deferred to `01.4b`):** the live filter-agent + LLM summarizer through the worker (needs the archetype seed + orchestrator wiring). The PR's GitHub Actions (ci-backend / ci-security) is the binding gate at founder-merge.

## Next actions (founder)

1. **Merge** the focused PR (`claude/dazzling-shamir-c26b51` → `main`).
2. **`01.4b — memory auto-extraction`** (chip): LLM filter-agent + summarizer + orchestrator post-task wiring + `memory_curator` archetype seed + live worker validation.
3. (optional) **`01.4-ui`** — «Что помнит [агент]» view/edit/delete panel (grill Q6).
4. Cleanup chip: drop the unused 1024-dim `cell_<uuid>.memory_entries` from `multitenancy/0004`.
5. Carry-over (still open): **01.3b ЮKassa** (OQ-02/OQ-19) · Master-**through-worker** live golden · F1-B ADR-026 evaluator.

## Next phase

**Phase 01.5 — Артефакты** ([ADR-012](./decisions/ADR-012-artifacts.md)): Yjs-документы + S3-ассеты + citeable `artifact://` URLs. (Memory `conversation_summary` entries + cell/role memory are now available for artifact provenance + RAG in later phases.)
