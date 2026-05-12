# Wave 4 — Scale + Partner-программа (12 недель)

## Цель волны

**Готовность к масштабу + первая enterprise-сделка.** Миграция на Kubernetes, Qdrant отдельным сервисом, read-replicas, dedicated namespace для Pro-тарифа, Partner-программа с share-revenue, Keycloak для SAML/SSO, миграция auth на Logto. Open marketplace vertical-templates — Wave 5+.

## Метрика успеха

- 2000 платящих команд
- MRR ≥15 млн ₽
- Первая enterprise-сделка ≥500 тыс ₽/мес (хотя бы 1)
- 5+ активных partner с публикованными vertical-ролями
- Monthly churn <5%
- API p99 latency <500ms на нагрузке 200 RPS

## Критерий перехода к Wave 5+

- ✅ Все phase'ы — Done
- ✅ MRR достигнут
- ✅ Enterprise-клиент onboarded
- ✅ Partner-программа: первый partner отгенерил ≥3 публичные роли с user-adoption
- ✅ Retro

## Scope

**Must:**
- Yandex Managed K8s + Helm-чарт + ArgoCD GitOps
- Qdrant standalone (миграция с pgvector → recall-test)
- Postgres read-replicas + read/write splitting
- Dedicated namespace per Pro-tenant (ADR-009 Level C)
- Partner-программа: контракты, dashboard, revenue-share, sertification
- Anthropic / OpenAI через прокси (Wave 2+ recovery в Wave 4 для Enterprise если активный demand)
- BYOK для S3 (Enterprise option)
- Auth migration: Custom JWT → Logto self-hosted
- Keycloak параллельно с Logto для Enterprise SAML/AD/SSO
- WB/Ozon write API (создание листингов и т.д.)
- AI-Coach встроенный (PLG механика)
- Visual workflow editor

**Nice:**
- Win-back / retention bonuses
- On-premise Helm dry-run (preparation для Wave 5)
- Sertification programme «AI-team manager» (курс + экзамен)
- Annual conference preparations

## Длительность и команда

- **Срок:** 12 недель
- **Команда:** +Senior DevOps (full), +Partner Manager, +Sales/BizDev; ядро 8 человек
- **Бюджет AI-dev:** ~$10000

## Phases

См. [PHASES.md](./PHASES.md).

> **⚠️ Phase-файлы Wave 4 — placeholder.** Регенерируются в начале Wave 4 на базе результатов Wave 3 retro + актуальных ADR.

## Risks specific

- **R-06 (миграция):** k8s миграция требует strict zero-downtime — отдельный chaos drill before cutover
- **R-09 (найм):** Senior DevOps критичен для k8s
- **R-08:** Enterprise-клиент = security audit; ISO/SOC 2 preparation
- **R-12:** соблазн делать всё сразу — strict ICE prioritization

## Артефакты к концу волны

- Production на K8s (Yandex Managed) с auto-scaling
- Helm-чарт для on-premise (preparation для Wave 5)
- Partner-портал работает, ≥5 активных
- 1+ enterprise-клиент с SLA contract
- Sertification programme launched
- Visual workflow editor
- BYOK для S3 для enterprise
