# Wave 2 — Phase Index

> ⚠️ Phase-файлы Wave 2 — placeholders. Структура волны и phase-list будут финализированы при старте Wave 2 на основе:
> - Текущего scope из [README.md](./README.md)
> - Wave 1 retro outcomes
> - Актуальных ADR из [decisions/](../../decisions/README.md)

## Высокоуровневые phase-направления Wave 2

| Phase | Направление | Owner | Релевантные ADR |
|---|---|---|---|
| 02.1 | Pixel Department — **опциональный skin/office-режим** (Native Canvas 2D + AI-generated archetypes + 3 hand-drawn героев W2, ещё 2 — W3); базовый UI/брендинг строго professional nordic | Senior Frontend + Designer | [ADR-004](../../decisions/ADR-004-pixel-department.md), [ADR-021](../../decisions/ADR-021-ai-generated-pixel-pipeline.md), [ADR-031](../../decisions/ADR-031-design-direction-restyling.md) |
| 02.2 | Расширение каталога vertical-templates до 5 шт. (+ ИП-Бухгалтерия, СМБ-Sales) | Tech Lead + Middle Backend | [ADR-017](../../decisions/ADR-017-vertical-templates.md), [ADR-010](../../decisions/ADR-010-role-versioning.md) |
| 02.3 | Pyodide-runner для Analyst (WASM в браузере) | Senior Frontend | [ADR-006](../../decisions/ADR-006-gvisor-then-firecracker.md), [ADR-020](../../decisions/ADR-020-pyodide-code-execution.md) |
| 02.4 | MCP-серверы для vertical-коннекторов (Bitrix24, amoCRM, WB, Ozon) + community-MCP | Middle Backend | [ADR-013](../../decisions/ADR-013-mcp-protocol.md) |
| 02.5 | Полный onboarding wizard + 5 пресет-сценариев + live demo | Frontend + Designer | [ADR-016](../../decisions/ADR-016-team-first-ux.md), [ADR-022](../../decisions/ADR-022-coordinator-wizard-llm-hybrid.md) |
| 02.6 | RBAC расширение (Admin + Viewer + Bot/Service) | Senior Backend | [ADR-014](../../decisions/ADR-014-security.md) |
| 02.7 | Vertical-marketing pages (Astro 5) для 5 templates | Founder + Marketing + Frontend | [ADR-001](../../decisions/ADR-001-modular-monolith.md), [ADR-017](../../decisions/ADR-017-vertical-templates.md) |
| 02.8 | Golden datasets per vertical-template (30-50 задач каждый) | Tester + Tech Lead | [ADR-010](../../decisions/ADR-010-role-versioning.md) |
| 02.9 | **Real-time co-editing** — y-websocket sync-сервер поверх 01.5 Yjs-субстрата (deferred из 01.5 per RQ-20260701-001, grill 2026-07-03; триггер = многопользовательские cells + первая редактируемая Dashboard-поверхность). Схема 01.5 переиспользуется без изменений (`state`+`state_vector`+update-log) | Senior Backend + Frontend | [ADR-012](../../decisions/ADR-012-artifacts.md), [ADR-038](../../decisions/ADR-038-artifacts-envelope-schema.md) |
| 02.10 | **Storage-quota enforcement** — admission-check на upload по тарифным лимитам (Trial 1ГБ / Solo 5ГБ / Команда 10–200ГБ), **HARD-REJECT** при превышении + алерт на 90% (deferred из 01.5 per RQ-20260701-002, grill 2026-07-03; триггер = реальные тарифы live). 01.5 `cell_storage_usage` — готовый субстрат учёта | Senior Backend | [ADR-012](../../decisions/ADR-012-artifacts.md), [ADR-008](../../decisions/ADR-008-credits-billing.md) |

## Acceptance gate to Wave 3

См. [README.md](./README.md) — секция «Метрика успеха».

Conkretные phase-spec'ы (tasks + acceptance criteria + dependencies graph) генерируются при старте Wave 2.
