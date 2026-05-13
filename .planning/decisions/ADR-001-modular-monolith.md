# ADR-001: Модульный монолит — Python+FastAPI backend + Vite+React frontend (monorepo)

- **Status:** Accepted

## Decision

**Backend:** Python 3.12 + FastAPI + asyncio + uvicorn. Модульный монолит, разделённый на bounded contexts: `iam`, `cells`, `agents`, `runtime`, `artifacts`, `billing`, `memory`, `mcp`, `audit`, `notifications`.

**Frontend (главный SPA):** Vite 6 + React 19 + TypeScript 5.6+ + TanStack Router + TanStack Query v5 + Tailwind v4 + shadcn/ui + Zustand.

**Marketing-site (Wave 2+):** Astro 5 — static SSG для landing-pages, blog, use-cases.

**Связь фронт↔бек:** REST + JSON (FastAPI auto-генерит OpenAPI → orval/openapi-typescript генерит type-safe клиент), WebSocket для real-time events.

## Tech stack (full)

| Слой | Решение |
|---|---|
| Backend язык | Python 3.12, strict type hints, async-first |
| Backend framework | FastAPI 0.115+ + uvicorn |
| Agent runtime | Pydantic-AI (latest) + наш `Team / Role / Coordinator` слой |
| ORM | SQLAlchemy 2.x + Alembic |
| DB | PostgreSQL 16 + pgvector |
| Cache/queues | Redis 7 + Dramatiq |
| Frontend bundler | Vite 6 |
| Frontend language | TypeScript 5.6+ strict |
| Frontend framework | React 19 |
| Frontend routing | TanStack Router v1 (file-based, type-safe) |
| Server state | TanStack Query v5 |
| Global state | Zustand |
| Styling | Tailwind v4 |
| UI components | shadcn/ui (copy-paste, кастомизируем) |
| Forms | react-hook-form + zod |
| 2D rendering | Native HTML5 Canvas API (ADR-004) |
| Real-time | WebSocket (native) |
| Animation | Motion (Framer Motion v11+) для UI; CSS keyframes для Pixel |
| i18n | react-i18next (default ru-RU) |
| Testing FE | Vitest + Playwright |
| Testing BE | pytest + pytest-asyncio + testcontainers |
| Marketing site | Astro 5 (отдельный трек, Wave 2) |

## Repository structure

```
TEAMLY_RU/                        # monorepo
├── backend/                      # Python FastAPI
│   ├── src/
│   │   ├── iam/                  # auth, users, workspaces (cells)
│   │   ├── cells/                # cell lifecycle
│   │   ├── agents/               # roles, agent runtime
│   │   ├── runtime/              # task execution, workflows
│   │   ├── artifacts/            # files, Yjs docs
│   │   ├── billing/              # subscriptions, credits, ЮKassa
│   │   ├── memory/               # workspace + role memory
│   │   ├── mcp/                  # MCP client + curated catalog
│   │   ├── audit/                # immutable audit log
│   │   ├── notifications/        # email, Telegram-bot
│   │   └── shared/               # common utils, db, settings
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml
├── frontend/                     # Vite + React SPA
│   ├── src/
│   │   ├── routes/               # TanStack Router file-based
│   │   ├── features/             # per-bounded-context UI
│   │   ├── components/           # shadcn/ui + custom
│   │   ├── lib/                  # API client, utils
│   │   └── styles/
│   ├── public/
│   └── package.json
├── marketing/                    # Astro 5 (Wave 2+)
├── infra/                        # Docker Compose, Terraform, Helm
│   ├── docker-compose.dev.yml
│   ├── docker-compose.staging.yml
│   ├── terraform/
│   └── helm/
├── docs/                         # mkdocs site, runbook'и
├── .planning/                    # roadmap, ADR, risks
│   └── _meta/contracts/          # authoritative DDL + OpenAPI + CloudEvents per bounded context (ADR-024)
├── .claude/                      # AI-dev agent configs (ADR-023: .claude/agents/<role>/)
└── AGENTS.md
```

**Authoritative spec vs implementation:**
- `.planning/_meta/contracts/<context>/` — single source of truth для DB schema, API spec, domain events (см. [ADR-024](./ADR-024-bounded-context-contracts.md)).
- `backend/src/<context>/` — implementation layer, conform'ит контракту.
- Phase-spec'ы импортируют контракт через cross-link, не дублируют DDL.

В таблице bounded contexts термин для агентов: канонический ID — `agent_archetype_id` (FK к `agent_archetypes`); прежние термины `ui_sprite_archetype` / `sprite-ID` deprecated. См. [ADR-024 — naming corrections](./ADR-024-bounded-context-contracts.md#2-naming-corrections).

## Consequences

- Один язык backend, один — frontend. Pydantic-модели = единая граница типов.
- Vite dev-server fast HMR (~50ms).
- AI-dev-agents знают связку наизусть.
- При вертикальном масштабе bounded contexts extract'ятся в отдельные сервисы без переписывания доменной логики.

## Links

- Stack: [_meta/stack.md](../_meta/stack.md)
- Related ADRs: ADR-003 (Pydantic-AI), ADR-004 (Canvas), ADR-013 (MCP), [ADR-023](./ADR-023-ai-team-runtime.md) (AI-team runtime), [ADR-024](./ADR-024-bounded-context-contracts.md) (bounded-context contracts)
