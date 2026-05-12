# Wave 3 — Phase Index

> ⚠️ Phase-файлы Wave 3 — placeholders. Структура волны и phase-list финализируются при старте Wave 3 на основе:
> - Текущего scope из [README.md](./README.md)
> - Wave 2 retro outcomes
> - Актуальных ADR из [decisions/](../../decisions/README.md)

## Высокоуровневые phase-направления Wave 3

| Phase | Направление | Owner | Релевантные ADR |
|---|---|---|---|
| 03.1 | Vertical Rituals Catalog (per vertical-template + cron + webhook triggers) | Tech Lead + Senior Backend | [ADR-019](../../decisions/ADR-019-vertical-autonomous-mode.md) |
| 03.2 | «Знания команды» (PARA Workspace): Проекты / Сферы / Ресурсы / Архив | Senior Backend + Frontend | [ADR-011](../../decisions/ADR-011-memory-2-level.md), [ADR-019](../../decisions/ADR-019-vertical-autonomous-mode.md) |
| 03.3 | Workflow-шаблоны (DAG-executor + UI form-builder) | Senior Backend + Frontend | [ADR-003](../../decisions/ADR-003-pydantic-ai-runtime.md) |
| 03.4 | Corporate MCP-серверы (наши): 1c-rest-mcp, kontur-elba-mcp, kontur-extern-mcp, tinkoff-business-mcp | Middle Backend | [ADR-013](../../decisions/ADR-013-mcp-protocol.md) |
| 03.5 | Расширение community MCP-каталога (20+ серверов) + UI catalog | Middle Backend + Frontend | [ADR-013](../../decisions/ADR-013-mcp-protocol.md) |
| 03.6 | Approval mode + полный immutable audit log + аудит-журналы | Senior Backend | [ADR-014](../../decisions/ADR-014-security.md) |
| 03.7 | Telegram-бот для команды (нотификации + быстрые команды) | Middle Backend | [ADR-013](../../decisions/ADR-013-mcp-protocol.md) |
| 03.8 | Langfuse self-hosted + расширенный OpenTelemetry + agent-trace visibility | DevOps | [ADR-015](../../decisions/ADR-015-ai-dev-process.md) |
| 03.9 | Customer Success programme: Health Score + proactive outreach + образовательный контент | Founder + CS Manager + Backend | (process, не ADR) |
| 03.10 | 2D-сцена офиса (полная с anim transitions, не только карточки) | Senior Frontend + Designer | [ADR-004](../../decisions/ADR-004-pixel-department.md) |
| 03.11 | (опц.) Server-side gVisor sandbox если customer demand на long-running Analyst | DevOps + Senior Backend | [ADR-006](../../decisions/ADR-006-gvisor-then-firecracker.md) |

## Acceptance gate to Wave 4

См. [README.md](./README.md) — секция «Метрика успеха».

Конкретные phase-spec'ы (tasks + acceptance criteria + dependencies graph) генерируются при старте Wave 3.
