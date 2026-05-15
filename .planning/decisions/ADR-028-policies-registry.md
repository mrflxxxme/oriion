---
id: ADR-028
title: Policies Registry & Decisions Cross-Reference
status: Accepted
date: 2026-05-14
deciders: founder
supersedes: GRILL-DECISIONS-ORIION.md (consolidated)
---

# ADR-028 — Policies Registry & Decisions Cross-Reference

## Context

В ходе milestones A–D сформировались стабильные cross-session политики (P-INIT, P-AUDIT, P-DESIGN) и серия зафиксированных решений (DECISION-1..11), которые исторически жили в крупном сессионном логе `_meta/GRILL-DECISIONS-ORIION.md`. Это нарушало single-source-of-truth: ADR оставались каноничными для архитектуры, но политики/решения цитировались из сессионного нарратива.

Этот ADR — формальный home для всех политик и cross-reference карта `DECISION-N → existing ADR`. Исторический сессионный лог удалён; все ссылки переадресуются сюда.

## Decision

Все стабильные политики проекта фиксируются в этом файле. Каждой политике соответствует якорь вида `#p-init-N`, `#p-audit-N`, `#p-design-N`. Каждому решению из исходного GRILL-лога — якорь `#decision-N` со ссылкой на ADR, который его операционализирует.

## Policies (canonical home)

### P-INIT-1 — Phase-spec B-level implementation-ready

Phase-spec'ы Wave 0–1 содержат OpenAPI-фрагменты, DDL, сигнатуры функций, тестовые сценарии и UI-spec ссылки. Не B-level → блокирует phase-start.

**Operationalized by:** [ADR-023 §1 (planner role)](./ADR-023-ai-team-runtime.md), [ADR-025 §2 (gate triggers spec advancement)](./ADR-025-acceptance-gate-format.md).

### P-INIT-2 — Authoritative spec layer in `contracts/<context>/`

Каждый bounded context имеет канонические артефакты в `contracts/<context>/`. Phase-spec'ы cross-link на них — не дублируют схемы инлайн.

**Operationalized by:** [ADR-024](./ADR-024-bounded-context-contracts.md), особенно §5 (cross-link rule).

### P-INIT-3 — Founder = always final approver tier 3+

Никакая AI-роль не имеет права на merge выше tier 2. Founder = единственный финальный approver для всего, что меняет архитектуру, security, public surface, product behavior.

**Operationalized by:** [ADR-027 §2-5 (tier-table)](./ADR-027-solo-ai-git-pr-workflow.md).

### P-INIT-4 — Vertical-prompt anti-hallucination Level B

Vertical prompts проходят: source-citation в payload → founder REVIEW-CHECKLIST → evaluator gate (≥75% golden-dataset + 100% adversarial) → 90-day re-verification cycle.

**Operationalized by:** [ADR-026 §3-5](./ADR-026-vertical-expertise-pipeline.md).

### P-INIT-5 — Team model: solo founder + 11 persistent Opus AI-agents

Команда фиксирована: 1 founder + 11 persistent Opus-агентов (cross-cutting 3 + implementation 3 + quality-gates 5) + non-persistent spawned roles (vertical-prompt-author, mcp-builder, devops-implementer, golden-dataset-curator). Никаких human hires до Wave 3.

**Closes:** OQ-13, OQ-14, OQ-15, OQ-16 (все `N/A`). **Closes:** R-29 (founder vertical expertise as Level-B foundation).

**Operationalized by:** [ADR-023 §1-2](./ADR-023-ai-team-runtime.md).

### P-AUDIT-1 — AI dev cost numbers — only in `cost-budget.yaml`

**AI dev cost cap-номера** (per-task / per-day / per-month / Sonnet fallback thresholds) не дублируются в ADR, risks, phase-specs. Единственный канонический источник — `.claude/agents/_shared/cost-budget.yaml`.

**Founder-personal financial decisions** (funding strategy / runway / burn / personal capital allocation / pre-seed timing) — **out-of-scope project docs** per Session-2026-05-15. Не хранятся, не tracked, не блокируют project workflow. **Closes:** OQ-17, OQ-18 (закрыты как `out-of-scope`).

**Operationalized by:** [ADR-023 Consequences §2](./ADR-023-ai-team-runtime.md) (cross-ref без embed).

### P-AUDIT-2 — Deprecated terms patched in same PR as ADR deprecation

Когда ADR помечает термин/API deprecated, все phase-spec и contracts-ссылки на этот термин патчатся в той же PR. Никаких pending deprecation diffs.

**Operationalized by:** [ADR-024 §2 (naming-corrections table)](./ADR-024-bounded-context-contracts.md).

### P-AUDIT-3 — Tool-naming registry conformance

Каждый `tools-allowlist` (в `.claude/agents/<role>/` или `verticals/<slug>/prompts/<role>.md`) обязан ссылаться только на slugs из [`tools/registry.md`](../tools/registry.md). Reviewer-backend проверяет conformance в pre-merge gate. Несуществующий slug → блок merge.

**Enforcement deliverable (Phase 00.1):** reviewer-backend CI hook + pre-commit linter.

### P-AUDIT-4 — Cost-budget structure separation: dev_team vs user_production

`cost-budget.yaml` v2 разделяет два контура:
- **dev_team** — baseline (~$500/мес), активен с Phase 00.1.
- **user_production** — dormant до wave-1-to-2 gate; активируется с включением user-cell LLM-gateway.

Каждый контур имеет независимые caps, telemetry и kill-switches. Mixing запрещён.

**Activation rule:** `user_production` ветка включается одновременно с public-beta релизом (Wave 2).

### P-DESIGN-1 — Designer = DS-keeper; ui-ux-pro-max primary; Claude Design fallback

`designer` (один из 11 persistent agents per ADR-023) — единственный владелец Design System. Первичный инструмент — skill `ui-ux-pro-max`. Claude Design используется как fallback с Wave 1+ для hero-illustrations, marketing assets, branded illustrations, где `ui-ux-pro-max` не покрывает.

**Operationalized by:** [ADR-023 §1 (designer role mandate)](./ADR-023-ai-team-runtime.md). DS evolution path (B→C→D) описана в [ADR-001](./ADR-001-modular-monolith.md) (Wave-aligned design-system maturity).

## Decisions cross-reference (DECISION-N → ADR)

Эта таблица — навигационный мост: исторические якоря `#decision-N` сохраняются, но указывают на каноничные ADR, где решение операционализировано.

### #decision-1 — Phase-spec quality bar
→ Зафиксировано как **[P-INIT-1](#p-init-1)** + [ADR-023](./ADR-023-ai-team-runtime.md), [ADR-001](./ADR-001-modular-monolith.md).

### #decision-2 — Wave 0+1 = B-level, Wave 2-5 = direction + gate
→ [ADR-025 §2 (hard go/no-go thresholds)](./ADR-025-acceptance-gate-format.md).

### #decision-3 — Team model = 1 founder + 11 persistent Opus
→ **[P-INIT-5](#p-init-5)** + [ADR-023 §1](./ADR-023-ai-team-runtime.md).

### #decision-4 — Design System B→C→D evolutionary
→ **[P-DESIGN-1](#p-design-1)** + [ADR-001](./ADR-001-modular-monolith.md) + [ADR-016](./ADR-016-team-first-ux.md).

### #decision-5 — `.claude/agents/<role>/` = C modular split (7-file structure)
→ [ADR-023 §4](./ADR-023-ai-team-runtime.md).

### #decision-6 — Vertical-expertise = Pattern D (AI-baseline + founder edit + friends-loop)
→ [ADR-026 §1-2](./ADR-026-vertical-expertise-pipeline.md).

### #decision-7 — Schema-contracts = C bounded-context split (10 contexts)
→ [ADR-024 §1](./ADR-024-bounded-context-contracts.md) + **[P-INIT-2](#p-init-2)**.

### #decision-8 — Runtime = Claude Code Task tool + AgentDB bridge
→ [ADR-023 §6-7](./ADR-023-ai-team-runtime.md).

### #decision-9 — Acceptance-gate Wave→Wave = YAML frontmatter + Markdown body
→ [ADR-025 §1-2](./ADR-025-acceptance-gate-format.md).

### #decision-10 — Git/PR workflow = phase-branch + atomic AI commits + selective rebase
→ [ADR-027 §1-5](./ADR-027-solo-ai-git-pr-workflow.md) + **[P-INIT-3](#p-init-3)**.

### #decision-11 — Anti-hallucination Level B (Wave 0) → Level C (Wave 1+) friends-loop
→ [ADR-026 §3-4](./ADR-026-vertical-expertise-pipeline.md) + **[P-INIT-4](#p-init-4)**.

## Consequences

**Положительные:**
- Канонический home для политик; нет двойного источника истины с GRILL-логом.
- Существующие 27 ADR не модифицированы (минимум surface для распространения изменений).
- Анкоры `#decision-N` и `#p-init-N` сохранены для обратной совместимости текстовых ссылок.

**Отрицательные:**
- Этот файл — навигационный, не «истинный» архитектурный ADR (политики vs архитектура). Считаем приемлемым trade-off против разнесения политик по 10+ существующим ADR.

**Follow-up actions (Phase 00.1):**
- Имплементировать P-AUDIT-3 CI-hook (reviewer-backend tools-allowlist conformance).
- Создать `cost-budget.yaml` v2 с dev_team/user_production структурой (P-AUDIT-4).
- При создании `.claude/agents/designer/` — закрепить ui-ux-pro-max как primary tool (P-DESIGN-1).

## Anchors index

| Anchor | Topic |
|---|---|
| `#p-init-1` … `#p-init-5` | Policies — init |
| `#p-audit-1` … `#p-audit-4` | Policies — audit |
| `#p-design-1` | Policies — design |
| `#decision-1` … `#decision-11` | Historical decisions → ADR map |
