# TEAMLY_RU — Project Overview

> Облачная платформа AI-команд для СМБ + personal-users сегмента РФ. Пользователь начинает с универсальной команды («Твои личные ассистенты»), при необходимости расширяет до vertical-команды с domain-expertise. Coordinator декомпозирует задачи (или Master-Agent в vertical-режиме), агенты выполняют, результат — в Pixel Department.

## Primary USP (dual messaging per [Session-decision 2026-05-15](./JOURNAL.md))

**Entry-point:** универсальная team-команда `productivity-core` («Твои личные ассистенты») — Coordinator + Researcher + Writer + Analyst — для общих задач исследований/аналитики/контента/маркетинга.

**Depth layer:** 5 vertical-templates с РФ-domain экспертизой через Master-Agent layer per [ADR-029](./decisions/ADR-029-master-agent-vertical-templates.md) — Маркетинг-агентство, Telegram-крейтор, WB-Селлер, ИП-Бухгалтерия, СМБ-Sales.

## Tech-стек (Wave 0)

- **Backend:** Python 3.12 + FastAPI + Pydantic-AI
- **Frontend:** Vite 6 + React 19 + TanStack Router + Tailwind v4 + shadcn/ui
- **2D:** Native HTML5 Canvas
- **Code-exec:** Pyodide WASM (browser)
- **DB:** PostgreSQL 16 + pgvector
- **Cache:** Redis 7 + Dramatiq
- **Auth:** Custom JWT (W0-1) → Logto (W2-3) → Keycloak (Enterprise)
- **LLM:** DeepSeek V3/R1 + YandexGPT + GigaChat, все BYOK с дня 1
- **Cloud:** Yandex Cloud ru-central-1 (Москва)
- **Connectors:** MCP-протокол

Полный стек — [`_meta/stack.md`](./_meta/stack.md).

## Roadmap (6 волн, revision 2026-05-15)

| Wave | Срок | Цель | Метрика успеха |
|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: horizontal `productivity-core` team end-to-end (Market & content brief сценарий) | Demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha: horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + memory + billing + RBAC + Telegram Business API | 10-15 friends, ≥3 задачи/клиент, success ≥75% |
| **2. Pixel + каталог** | 9 нед (было 8) | Public beta: horizontal + 3 vertical (Marketing + Telegram + WB-Селлер) + Pixel + Pyodide + Telegram Mini App + MCP-каталог | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 10 нед (было 8) | GA: +2 vertical (ИП-Бух + СМБ-Sales с Master-Agent) + Vertical Rituals + «Знания команды» + corp connectors + CS | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro + Telegram Stars billing | 2000 платящих, MRR ≥15 млн ₽ |
| **5+. Enterprise & v2** | 12+ мес | On-premise + Firecracker + open marketplace | TBD |

Детали — [`roadmap/README.md`](./roadmap/README.md).

## Команда

Per [P-INIT-5](./decisions/ADR-028-policies-registry.md#p-init-5) + [ADR-023](./decisions/ADR-023-ai-team-runtime.md): **solo founder + 11 persistent Opus AI-агентов**.

- **Founder** — продукт, архитектура, sales, final approver per [ADR-027](./decisions/ADR-027-solo-ai-git-pr-workflow.md) tier-table (всегда tier 3+ approval) per [P-INIT-3](./decisions/ADR-028-policies-registry.md#p-init-3).
- **11 persistent Opus AI-агентов** в [`.claude/agents/<role>/`](../.claude/agents/) per [ADR-023](./decisions/ADR-023-ai-team-runtime.md):
  - **Cross-cutting (3):** architect / planner / memory-curator
  - **Implementation (3):** designer / frontend-implementer / backend-implementer
  - **Quality gates (5):** reviewer-frontend / reviewer-backend / reviewer-security / verifier / evaluator
- **Non-persistent роли** (spawned per phase): vertical-prompt-author / mcp-builder / devops-implementer / golden-dataset-curator.
- **Pipeline runtime:** Claude Code Task tool + AgentDB memory per ADR-023 §6-7; handbook entry-point — [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md).

R-29 закрыт через founder personal vertical expertise (см. [`risks/REGISTER.md`](./risks/REGISTER.md)).

## Текущая phase

**Wave 0 (Foundation) — Phase 00.1 (Repo & CI/CD) 🔄 active**, implementation complete на branch `claude/amazing-hamilton-8b9d2c` awaiting founder review + merge. Rolling status + AC verification + блокеры — [`STATUS.md`](./STATUS.md).

## Стартовые team-presets (1 horizontal + 5 vertical)

| Иконка | Template | Wave | ЦА | Тип |
|---|---|---|---|---|
| 🧰 | **Твои личные ассистенты** (`productivity-core`) | **W0 (anchor)** | SMB + солопренёры + personal-users | horizontal |
| 📈 | Маркетинг-агентство РФ | W1 | Маркетинг-агентства | vertical (Master-Agent) |
| ✍️ | Telegram-крейтор / Курс-автор | W1 | Авторы каналов | vertical (Master-Agent) |
| 🛒 | WB-Селлер команда | **W2 (was W0)** | Селлеры WildBerries | vertical (Master-Agent) |
| 💼 | ИП-Бухгалтерия (1С/Эльба) | **W3 (was W2)** | ИП | vertical (Master-Agent) |
| 🎯 | СМБ-Sales (Bitrix24/amoCRM) | **W3 (was W2)** | СМБ с CRM | vertical (Master-Agent) |

Детали — [`decisions/ADR-017-vertical-templates.md`](./decisions/ADR-017-vertical-templates.md) (горизонталь + вертикали), [`decisions/ADR-029-master-agent-vertical-templates.md`](./decisions/ADR-029-master-agent-vertical-templates.md) (Master-Agent layer).

## Архитектурные решения

Полный каталог ADR — [`decisions/README.md`](./decisions/README.md). Политики и cross-ref решений — [`decisions/ADR-028-policies-registry.md`](./decisions/ADR-028-policies-registry.md).

## Тарифы

См. [`decisions/ADR-008-credits-billing.md`](./decisions/ADR-008-credits-billing.md).
