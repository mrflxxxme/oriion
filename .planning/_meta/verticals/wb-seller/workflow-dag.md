---
title: "WB-Seller Agent Team — Workflow DAG"
vertical_slug: wb-seller
version: 0.1.0
last-updated: 2026-05-13
status: draft
---

# WB-Seller Agent Team — Workflow DAG

## Overview

Workflow описывает interaction trio agent_archetypes (`wb-coordinator`, `wb-researcher`, `wb-listing-writer`) для 5 primary user-tasks Wave 0. Это reference model для Phase 00.5 implementation.

## High-level DAG

```
[User intent / cell input]
        │
        ▼
   wb-coordinator
   (decomposes intent → task chain)
        │
        ├──► wb-researcher
        │    (gathers WB context:
        │     category rules, top competitors,
        │     current promo calendar, etc)
        │            │
        │            ▼
        │    [research artifact JSON]
        │            │
        ▼            ▼
   wb-listing-writer  ◄─── (research input)
   (generates copy: title /
    description / keywords /
    answer / review-response)
        │
        ▼
   [draft artifact + diff vs current]
        │
        ▼
   wb-coordinator
   (validates output, requests user confirm)
        │
        ▼
   [user review interaction]
        │
        ├── approved → publish via WB API (Wave 1)
        └── changes → loop back to writer/researcher
```

## Per-task workflows

### Task 1: Generate listing for new SKU

1. **coordinator** — parse user input (product photos, category hint, target keywords)
2. **coordinator → researcher** — «get category {X} rules + top-3 competitor listings»
3. **researcher** — returns structured JSON `{category_rules, competitor_examples, recommended_keywords, char_limits}`
4. **coordinator → writer** — «generate listing using {research} for {user_input}»
5. **writer** — returns `{title, description, keywords, char_counts_validation}`
6. **coordinator** — presents draft + char-count validation к user; collects feedback
7. **(loop)** — max 3 iterations per phase cost-budget

### Task 2: Audit existing listing

1. **coordinator** — receives SKU артикул
2. **researcher** — pulls current listing + category benchmarks + competitor snapshot
3. **writer (audit mode)** — compares against checklist (title length, keyword density, image specs, description structure), returns scored audit
4. **coordinator** — presents prioritized findings + suggested fixes

### Task 3: Draft answer to customer question

1. **coordinator** — receives question text + product context (артикул)
2. **researcher** — pulls product specs + recent similar Q&A patterns + customer review trends
3. **writer (response mode)** — generates draft answer with tone-control (per `tone:` parameter)
4. **coordinator** — presents draft для approval (compliance with WB community guidelines)

### Task 4: Draft response to negative review

1. **coordinator** — receives review text + sentiment classification + продукт-контекст
2. **researcher** — pulls similar past responses + escalation history (если есть)
3. **writer (review-response mode)** — generates empathetic, brand-aligned response (no defensive tone, no admission of guilt без явного user-approve)
4. **coordinator** — presents для founder/seller review перед публикацией

### Task 5: Snapshot ranking + suggest improvements

1. **coordinator** — receives артикул + target keywords list
2. **researcher** — pulls current ranking position per keyword, competitor analysis, conversion funnel
3. **writer (recommendation mode)** — generates prioritized recommendations (title tweak, image swap, price adjustment, promo participation)
4. **coordinator** — presents ranked action plan with impact estimates

## Escalation paths

- **Insufficient research data** (researcher не находит достоверной информации — например, новая категория без analog'ов) → coordinator escalates к founder с пометкой `out-of-scope`
- **Content-safety filter hit** (rare для WB-domain, но fallback existing) → coordinator returns error, suggests rephrase
- **Repeated user dissatisfaction** (>3 raze same task с разными outputs) → memory-curator captures pattern → suggests prompt revision к founder
- **WB API failure** (Wave 1+ publishing) → outbox queue, retry with notification per ADR-009
- **Cost-budget warning** — switch к fallback model (claude-sonnet-4-6) или suspend non-critical steps

## CloudEvents emitted

Per [`_meta/contracts/tasks/events.yaml`](../../contracts/tasks/events.yaml):

| Event | When |
|-------|------|
| `oriion.tasks.task.started.v1` | coordinator pickup user-intent |
| `oriion.tasks.task.step_completed.v1` | per agent invocation (researcher returns / writer returns) |
| `oriion.tasks.task.succeeded.v1` | user approves final artifact |
| `oriion.tasks.task.failed.v1` | escalation triggered OR max-retries hit |

## Memory interactions

- **memory.cells_search** — coordinator проверяет past task patterns per user-cell
- **memory.cells_upsert** — после completed task → store task-pattern + user-preference signals
- **PII filter** — никогда не сохраняем имена покупателей / exact review text без anonymization

## Cost budgeting

Per `_shared/cost-budget.yaml`:
- Single task end-to-end: ≤ ₽5 LLM cost target (Wave 0 internal)
- Wave 1+: ≤ 10% от paid price per action

## References

- [ADR-026](../../decisions/ADR-026-vertical-expertise.md)
- [`_meta/contracts/agents/`](../../contracts/agents/) — agent_archetypes table
- [`_meta/contracts/tasks/`](../../contracts/tasks/) — task lifecycle + events
- [ADR-015](../../decisions/ADR-015-task-lifecycle.md) — stagnation auto-kill
