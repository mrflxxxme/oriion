# TEAMLY_RU — Project Overview

> Облачная платформа AI-команд для СМБ-сегмента РФ. Пользователь нанимает готовую команду одним кликом, Coordinator декомпозирует задачи, агенты выполняют, результат — в Pixel Department.

## Primary USP

РФ-вертикальная экспертиза: 5 стартовых vertical-templates — WB-Селлер, Маркетинг-агентство, Telegram-крейтор, ИП-Бухгалтерия, СМБ-Sales.

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

## Roadmap (6 волн)

| Wave | Срок | Цель | Метрика успеха |
|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: WB-Селлер team end-to-end | Demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha: 3 vertical-templates + memory + billing + RBAC | 10-15 friends, ≥3 задачи/клиент, success ≥75% |
| **2. Pixel + каталог** | 8 нед | Public beta: 5 vertical-templates + Pixel + Pyodide + MCP-каталог | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 8 нед | GA: Vertical Rituals + «Знания команды» + corp connectors + CS | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro | 2000 платящих, MRR ≥15 млн ₽ |
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

**Pre-Wave-0** → следующая: [Phase 00.1 (Repo & CI/CD)](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md).

Активные blockers — [`STATUS.md`](./STATUS.md).

## Стартовые vertical-templates (5 шт.)

| Иконка | Template | Wave | ЦА |
|---|---|---|---|
| 🛒 | WB-Селлер команда | W0 | Селлеры WildBerries |
| 📈 | Маркетинг-агентство РФ | W1 | Маркетинг-агентства |
| ✍️ | Telegram-крейтор / Курс-автор | W1 | Авторы каналов |
| 💼 | ИП-Бухгалтерия (1С/Эльба) | W2 | ИП |
| 🎯 | СМБ-Sales (Bitrix24/amoCRM) | W2 | СМБ с CRM |

Детали — [`decisions/ADR-017-vertical-templates.md`](./decisions/ADR-017-vertical-templates.md).

## Архитектурные решения

Полный каталог ADR — [`decisions/README.md`](./decisions/README.md). Политики и cross-ref решений — [`decisions/ADR-028-policies-registry.md`](./decisions/ADR-028-policies-registry.md).

## Тарифы

См. [`decisions/ADR-008-credits-billing.md`](./decisions/ADR-008-credits-billing.md).
