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

## Acceptance gate to Wave 3

См. [README.md](./README.md) — секция «Метрика успеха».

Conkretные phase-spec'ы (tasks + acceptance criteria + dependencies graph) генерируются при старте Wave 2.
