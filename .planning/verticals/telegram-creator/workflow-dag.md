---
title: "Telegram-крейтор Agent Team — Workflow DAG"
vertical_slug: telegram_creator
version: 0.1.0
last-updated: 2026-07-09
status: draft
---

# Telegram-крейтор Agent Team — Workflow DAG

## Overview

Two-layer orchestration per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md):
Master (доменный CEO) → Coordinator (операционный COO) → Researcher / Analyst /
Writer (reused horizontal specialists) + Community-manager (vertical-specific,
Telegram-bot connector consumer). Mirrors `agency-marketing-ru`'s DAG shape
(see [`verticals/agency-marketing-ru/`](../agency-marketing-ru/)) with one
addition: the Community-manager node, which is where the Telegram connector
tools (`telegram_read_updates` / `telegram_draft_message`) attach.

## High-level DAG

```
[User request]
      │
      ▼
    Master
(доменный триаж → MasterPlan: objective + domain_constraints + success_criteria)
      │
      ▼
  Coordinator
(декомпозирует MasterPlan.objective в task chain)
      │
      ├──► Researcher   (тренды, конкуренты, референсы по нише)
      ├──► Analyst       (интерпретация ERR/охватов относительно бенчмарка)
      └──► Community-manager
              (telegram_read_updates: читает активность канала —
               комментарии/реакции/последние посты)
      │
      ▼ (research + analysis + channel-activity feed into Writer)
    Writer
(черновики: пост / сторис-текст / фоллоу-ап, по рубрике + тону)
      │
      ▼
  Community-manager
  (telegram_draft_message: готовит platform-native черновик поста —
   форматирование под Telegram, НЕ отправка)
      │
      ▼
  Coordinator
  (валидирует, собирает CoordinatorOutput)
      │
      ▼
    Master
  (синтез: финальный deliverable для пользователя, доменная проверка —
   маркировка рекламы / РКН-триггер / отсутствие выдуманных цифр)
      │
      ▼
  [User review — approve / iterate]
      │
      ├── approved → user publishes manually (send-side gated to 01.12 approval-UI)
      └── changes  → loop back to Writer/Community-manager (max 3 iterations per cost-budget)
```

## Per-task workflows

### Task 1: Контент-план

1. **Master** — доменный триаж запроса (ниша, аудитория, желаемая частота) → `MasterPlan.objective` = «собрать рубрикатор + черновики на период»
2. **Coordinator** — делегирует Researcher (тренды в нише) + Analyst (текущая динамика канала, если данные есть)
3. **Writer** — генерирует рубрикатор на месяц + детальный план на 2 недели (per domain-brief §2 planning-horizon convention)
4. **Coordinator → Master** — синтез: единый контент-план документ

### Task 2: Написание поста

1. **Master** — определяет формат/рубрику/тон из запроса
2. **Coordinator → Researcher** — при необходимости фактчек/референсы
3. **Coordinator → Writer** — черновик поста
4. **Coordinator → Community-manager** — `telegram_draft_message`: platform-native форматирование (длина, эмодзи-конвенции, отсутствие markdown-артефактов)
5. **Master** — синтез + доменная проверка (нет ли непроверенных фактических заявлений)

### Task 3: Аудит канала / аналитика

1. **Master** — объективная цель: «понять, что происходит с вовлечённостью и почему»
2. **Coordinator → Community-manager** — `telegram_read_updates`: снимок текущей активности (последние посты, реакции, комментарии)
3. **Coordinator → Analyst** — интерпретация ERR/охватов **относительно бенчмарка размера канала** (не голые цифры)
4. **Master** — синтез: диагностика + prioritized recommendations

### Task 4: Комплаенс-аудит (маркировка рекламы + РКН)

1. **Master** — доменный триаж: это комплаенс-задача, не новый креатив (см. Master-prompt few-shot #2, mirrors agency-marketing-ru)
2. **Coordinator → Researcher** — актуальные требования ФЗ-38/ОРД/РКН-реестр (если нужен свежий контекст)
3. **Coordinator → Analyst** — построчный risk/ok разбор поста
4. **Master** — синтез: конкретные правки + чек-лист маркировки + явный флаг, если у канала 10K+ подписчиков и нет данных о регистрации в реестре блогеров

### Task 5: Стратегия монетизации + репёрпоузинг

1. **Master** — доменная цель: выбор модели монетизации под размер/нишу + план адаптации существующего контента под форматы
2. **Coordinator → Researcher** — какие модели монетизации реалистичны для размера/ниши канала (без выдуманных цифр — см. domain-brief §4)
3. **Coordinator → Writer** — черновики репёрпоуженного контента (пост → сторис-текст → фоллоу-ап)
4. **Coordinator → Community-manager** — `telegram_draft_message` для итоговых platform-native черновиков
5. **Master** — синтез: единая стратегия, монетизационные цифры помечены как market-reference-range, не гарантия

## Escalation paths

- **Недостаточно данных о канале** (Community-manager `telegram_read_updates` возвращает пусто/канал новый) → Coordinator escalates: работать с рыночными бенчмарками вместо канал-специфичных данных, явно это пометить.
- **Content-safety / регуляторный риск** (реклама без маркировки, канал 10K+ без РКН-регистрации, сравнительная реклама, медицинские/финансовые заявления) → Master блокирует synthesis-approve, эмитирует явный флаг вместо тихого пропуска.
- **Send-side запрос** (пользователь просит «просто опубликуй») → Coordinator/Community-manager отказывает автономно отправлять — `send_telegram` остаётся DANGEROUS/deny-until-approval (01.12); предлагает подготовленный черновик для ручной публикации.
- **Cost-budget warning** → см. `.claude/agents/_shared/cost-budget.yaml`; suspend non-critical steps (например, Analyst-deep-dive) при близости к капу.

## CloudEvents emitted

Per [`contracts/tasks/events.yaml`](../../contracts/tasks/events.yaml) — same
`task.*` event set as `agency-marketing-ru` (no vertical-specific events
introduced this phase).

## Cost budgeting

Per `.claude/agents/_shared/cost-budget.yaml` — same aggregate-budget-cap
shape as `agency-marketing-ru` (Master plan + synthesis calls billed as
`task_steps` rows on the Master's parent task, per `src/agents/master.py`
`MasterCallBilling`).

## References

- [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md) — Master-Agent layer
- [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md) — vertical-expertise pipeline
- [`verticals/agency-marketing-ru/`](../agency-marketing-ru/) — structural reference (first Wave-1 vertical)
- [`src/security/capability.py`](../../../backend/src/security/capability.py) — connector tool risk classification
