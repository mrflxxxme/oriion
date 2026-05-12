# Wave 4 — Phase Index

> ⚠️ Phase-файлы Wave 4 — placeholders. Структура волны и phase-list финализируются при старте Wave 4 на основе:
> - Текущего scope из [README.md](./README.md)
> - Wave 3 retro outcomes
> - Customer demand сигналов на enterprise features

## Высокоуровневые phase-направления Wave 4

| Phase | Направление | Owner | Релевантные ADR |
|---|---|---|---|
| 04.1 | Migration на Yandex Managed K8s + Helm + ArgoCD GitOps | Senior DevOps + Tech Lead | [ADR-001](../../decisions/ADR-001-modular-monolith.md) |
| 04.2 | Qdrant migration (pgvector → Qdrant standalone) | Senior Backend | [ADR-005](../../decisions/ADR-005-pgvector-then-qdrant.md) |
| 04.3 | Postgres read-replicas + read/write splitting | Senior DevOps | [ADR-001](../../decisions/ADR-001-modular-monolith.md) |
| 04.4 | Dedicated namespace per Pro-tenant (multitenancy Level C) | Tech Lead + DevOps | [ADR-009](../../decisions/ADR-009-multitenancy-3-levels.md) |
| 04.5 | Partner-программа: контракты, dashboard, revenue-share, sertification | Founder + Partner Manager + Backend | (process) |
| 04.6 | BYOK для S3 (Enterprise option) + envelope encryption через client KMS | Senior Backend | [ADR-012](../../decisions/ADR-012-artifacts.md), [ADR-014](../../decisions/ADR-014-security.md) |
| 04.7 | Auth migration: Custom JWT → Logto self-hosted; Keycloak параллельно для Enterprise SAML/AD | Tech Lead | [ADR-007](../../decisions/ADR-007-authentik-then-keycloak.md) |
| 04.8 | Visual workflow editor (drag-and-drop DAG) | Senior Frontend | [ADR-003](../../decisions/ADR-003-pydantic-ai-runtime.md) |
| 04.9 | AI-Coach встроенный (PLG механика для retention) | Senior Backend + Frontend | (Wave 4 product feature) |
| 04.10 | WB/Ozon write API (создание листингов автоматически) | Middle Backend | [ADR-017](../../decisions/ADR-017-vertical-templates.md), [ADR-013](../../decisions/ADR-013-mcp-protocol.md) |
| 04.11 | (опц., при demand) Anthropic / OpenAI через прокси для Enterprise | Tech Lead | [ADR-002](../../decisions/ADR-002-llm-gateway.md) |
| 04.12 | (опц.) Sertification programme «AI-team manager» | Founder + CS + Frontend | (process) |

## Acceptance gate to Wave 5+

См. [README.md](./README.md) — секция «Метрика успеха».

Конкретные phase-spec'ы генерируются при старте Wave 4 после Wave 3 retro.
