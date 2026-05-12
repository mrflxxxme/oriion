# ADR Catalog

> Architecture Decision Records. Формат: Decision / Implementation / Consequences / Links.

## Core architecture

| ID | Решение |
|---|---|
| [ADR-001](./ADR-001-modular-monolith.md) | Модульный монолит: Python+FastAPI + Vite+React (split frontend/backend) |
| [ADR-002](./ADR-002-llm-gateway.md) | LLM Multi-provider Gateway — триконтурный стек с BYOK first-class |
| [ADR-003](./ADR-003-pydantic-ai-runtime.md) | Pydantic-AI как агентный runtime |
| [ADR-009](./ADR-009-multitenancy-3-levels.md) | Multitenancy: Cell как domain-first concept + 3 уровня изоляции |
| [ADR-013](./ADR-013-mcp-protocol.md) | MCP-протокол как universal connector layer + кураторский каталог |

## Frontend / UI

| ID | Решение |
|---|---|
| [ADR-004](./ADR-004-pixel-department.md) | Pixel Department — Native Canvas 2D + AI-generated + 5 hand-drawn vertical-героев |
| [ADR-016](./ADR-016-team-first-ux.md) | Team-first UX — «нанять команду» как primary abstraction |
| [ADR-021](./ADR-021-ai-generated-pixel-pipeline.md) | AI-generated pixel-asset pipeline + hand-drawn vertical-герои |
| [ADR-022](./ADR-022-coordinator-wizard-llm-hybrid.md) | Coordinator — Wizard (free) + LLM (trial/paid) гибрид |

## Backend / Runtime

| ID | Решение |
|---|---|
| [ADR-005](./ADR-005-pgvector-then-qdrant.md) | pgvector на старте, Qdrant standalone в Wave 4 |
| [ADR-006](./ADR-006-gvisor-then-firecracker.md) | Code-execution: Pyodide WASM (MVP) → gVisor (опц.) → Firecracker (Enterprise) |
| [ADR-011](./ADR-011-memory-2-level.md) | Memory 2-уровневая + persistent в Wave 2 + «Знания команды» (PARA) в Wave 3 |
| [ADR-019](./ADR-019-vertical-autonomous-mode.md) | Vertical-specific Autonomous Mode + Knowledge Workspace |
| [ADR-020](./ADR-020-pyodide-code-execution.md) | Pyodide WASM в браузере для code-execution (Analyst роль) |

## LLM / AI

| ID | Решение |
|---|---|
| [ADR-018](./ADR-018-deepseek-primary-llm.md) | DeepSeek как primary LLM-стек (DeepSeek V3 + R1) |
| [ADR-010](./ADR-010-role-versioning.md) | Версионирование ролей/templates: SemVer + Canary + Golden dataset |

## Product strategy

| ID | Решение |
|---|---|
| [ADR-017](./ADR-017-vertical-templates.md) | 5 стартовых vertical-templates как primary USP |
| [ADR-008](./ADR-008-credits-billing.md) | Team-кредиты + ЮKassa, Solo/Команды 5/15/30 + BYOK режим |
| [ADR-012](./ADR-012-artifacts.md) | Артефакты: Yjs для документов, S3 для ассетов |

## Security & operations

| ID | Решение |
|---|---|
| [ADR-007](./ADR-007-authentik-then-keycloak.md) | Auth: Custom JWT (W0-1) → Logto (W2-3) → Keycloak (Enterprise) |
| [ADR-014](./ADR-014-security.md) | Security: RBAC + DLP + isolation memory от tool-output |
| [ADR-015](./ADR-015-ai-dev-process.md) | AI-dev-процесс: 6 ролей + tier-based ревью + изоляция от prod |

## Шаблон нового ADR

См. [ADR-template.md](./ADR-template.md).

## Когда создавать ADR

- Архитектурное решение, затрагивающее ≥2 bounded contexts
- Выбор технологии/провайдера/библиотеки на >6 месяцев вперёд
- Trade-off между альтернативами, требующий документации
