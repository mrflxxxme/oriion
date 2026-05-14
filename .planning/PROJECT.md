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

## Roadmap (6 волн)

| Wave | Срок | Цель | Метрика успеха |
|---|---|---|---|
| **0. Foundation** | 3 нед | Internal demo: WB-Селлер team end-to-end | Demo passes |
| **1. Core MVP** | 6 нед | Pre-alpha: 3 vertical-templates + memory + billing + RBAC | 10-15 friends, ≥3 задачи/клиент, success ≥75% |
| **2. Pixel + каталог** | 8 нед | Public beta: 5 vertical-templates + Pixel + Pyodide + MCP-каталог | 100 регистраций/нед, TTFV ≤3 мин, конверсия ≥5% |
| **3. Глубина** | 8 нед | GA: Vertical Rituals + «Знания команды» + corp connectors + CS | 500 платящих, MRR ≥3 млн ₽ |
| **4. Масштаб + Partner** | 12 нед | K8s + Partner programme + dedicated namespace Pro | 2000 платящих, MRR ≥15 млн ₽ |
| **5+. Enterprise & v2** | 12+ мес | On-premise + Firecracker + open marketplace | TBD |

Детали — [`roadmap/INDEX.md`](./roadmap/INDEX.md).

## Команда

Per [GRILL DECISION-3](./_meta/GRILL-DECISIONS-ORIION.md#decision-3-team-model--bc--pipeline-per-phase--11-persistent-opus-agents) + [P-INIT-5](./_meta/GRILL-DECISIONS-ORIION.md#3-policy-decisions-cross-session-stable): **solo founder + 11 persistent Opus AI-агентов**.

- **Founder** — продукт, архитектура, sales, final approver per [ADR-027](./decisions/ADR-027-git-pr-workflow.md) tier-table (всегда tier 3+ approval) per [P-INIT-3](./_meta/GRILL-DECISIONS-ORIION.md#3-policy-decisions-cross-session-stable)
- **11 persistent Opus AI-агентов** в [`.claude/agents/<role>/`](../.claude/agents/) per [ADR-023](./decisions/ADR-023-ai-team-runtime.md):
  - **Cross-cutting (3):** architect / planner / memory-curator
  - **Implementation (3):** designer / frontend-implementer / backend-implementer
  - **Quality gates (5):** reviewer-frontend / reviewer-backend / reviewer-security / verifier / evaluator
- **Non-persistent роли** (spawned per phase): vertical-prompt-author / mcp-builder / devops-implementer / golden-dataset-curator
- **Pipeline runtime:** Claude Code Task tool + AgentDB memory per ADR-023 §6-7; handbook entry-point — [`agent-handbook/`](./agent-handbook/)

R-29 закрыт через founder personal vertical expertise (см. [risks/REGISTER.md](./risks/REGISTER.md)).

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

## Ключевые ADR (полный каталог в [`decisions/`](./decisions/))

### Core
- [ADR-001](./decisions/ADR-001-modular-monolith.md) — Модульный монолит (FastAPI + Vite+React, split)
- [ADR-002](./decisions/ADR-002-llm-gateway.md) — LLM Multi-provider Gateway + BYOK
- [ADR-003](./decisions/ADR-003-pydantic-ai-runtime.md) — Pydantic-AI runtime
- [ADR-009](./decisions/ADR-009-multitenancy-3-levels.md) — Cell-first multitenancy
- [ADR-013](./decisions/ADR-013-mcp-protocol.md) — MCP-протокол

### UI / Pixel
- [ADR-004](./decisions/ADR-004-pixel-department.md) — Pixel Department (Canvas 2D)
- [ADR-016](./decisions/ADR-016-team-first-ux.md) — Team-first UX
- [ADR-021](./decisions/ADR-021-ai-generated-pixel-pipeline.md) — AI-generated pixel pipeline
- [ADR-022](./decisions/ADR-022-coordinator-wizard-llm-hybrid.md) — Coordinator hybrid

### Backend / Runtime
- [ADR-005](./decisions/ADR-005-pgvector-then-qdrant.md) — pgvector → Qdrant
- [ADR-006](./decisions/ADR-006-gvisor-then-firecracker.md) — Pyodide → gVisor → Firecracker
- [ADR-011](./decisions/ADR-011-memory-2-level.md) — Memory + PARA
- [ADR-019](./decisions/ADR-019-vertical-autonomous-mode.md) — Vertical Autonomous Mode
- [ADR-020](./decisions/ADR-020-pyodide-code-execution.md) — Pyodide WASM

### LLM / Product
- [ADR-018](./decisions/ADR-018-deepseek-primary-llm.md) — DeepSeek primary
- [ADR-010](./decisions/ADR-010-role-versioning.md) — SemVer + Canary + Golden datasets
- [ADR-017](./decisions/ADR-017-vertical-templates.md) — 5 vertical-templates
- [ADR-008](./decisions/ADR-008-credits-billing.md) — Team-кредиты + ЮKassa
- [ADR-012](./decisions/ADR-012-artifacts.md) — Yjs + S3

### Security & Ops
- [ADR-007](./decisions/ADR-007-authentik-then-keycloak.md) — Auth: Custom JWT → Logto → Keycloak
- [ADR-014](./decisions/ADR-014-security.md) — RBAC + DLP + isolation
- [ADR-015](./decisions/ADR-015-ai-dev-process.md) — AI-dev process

## Tariffs (детали — [ADR-008](./decisions/ADR-008-credits-billing.md))

| Тариф | ₽/мес | Cells | Agents | Included T-credits | BYOK ₽/мес |
|---|---|---|---|---|---|
| Trial | 0 (14 дней) | 1 | 3 | 500 | — |
| Solo | 990 | 1 | 3 | 300 | 490 |
| Команда 5 | 1900 | 3 | 5 | 600 | 890 |
| Команда 15 | 4900 | 5 | 15 | 2000 | 2400 |
| Команда 30 | 9900 | 10 | 30 | 5000 | 4900 |
| Enterprise | Custom | Custom | Custom | Custom | + on-premise |
