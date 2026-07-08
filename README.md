# Oriion

Облачная платформа AI-команд для СМБ + personal-users сегмента РФ.

> **Рабочее имя проекта — «Oriion»** (прежнее TEAMLY_RU; per [ADR-040 D3](.planning/decisions/ADR-040-execution-spec-contract.md); финальный бренд — OQ-09, до Wave 2). Остаточные упоминания TEAMLY_RU в коде убираются в Phase 01.8c.
>
> Universal team-preset **«Твои личные ассистенты»** (Coordinator + Researcher + Writer + Analyst) + 5 РФ-vertical-templates с Master-Agent layer. Подробнее — [.planning/PROJECT.md](.planning/PROJECT.md).

## Quickstart (target ≤10 min cold-start per AC1)

```bash
git clone <repo-url> && cd oriion
cp .env.example .env
make dev-bootstrap
```

После bootstrap:
- Backend API: <http://localhost:8000> (Swagger: `/docs`)
- Frontend: <http://localhost:5173>
- Caddy reverse proxy: <http://localhost> (`/api/*` → backend, `/` → frontend)
- MinIO console: <http://localhost:9001> (user `oriion`, password `oriion-dev-s3`)

Prerequisites: Docker Desktop, `uv`, Node ≥ 20, GNU make (доступно через Git Bash on Windows).

## Stack

- **Backend:** Python 3.12 + FastAPI + Pydantic-AI + SQLAlchemy 2.0 async + Alembic
- **Frontend:** Vite 6 + React 19 + TypeScript strict + TanStack Router + Tailwind v4 + shadcn/ui
- **DB:** PostgreSQL 16 + pgvector
- **Cache/queue:** Redis 7 + Dramatiq
- **Object storage:** MinIO (dev) → Yandex Cloud Object Storage (prod)
- **Reverse proxy:** Caddy 2 (auto-HTTPS в prod)
- **Cloud:** Yandex Cloud ru-central-1
- **LLM:** DeepSeek V3/R1 + YandexGPT + GigaChat (BYOK с дня 1)

Полный stack: [`.planning/_meta/stack.md`](.planning/_meta/stack.md).

## Documentation

| Файл | Содержание |
|---|---|
| [.planning/README.md](.planning/README.md) | Project entry-point + navigation схема |
| [.planning/STATUS.md](.planning/STATUS.md) | Активная phase + блокеры (rolling) |
| [.planning/HANDOFF.md](.planning/HANDOFF.md) | Снимок состояния от прошлой сессии |
| [.planning/PROJECT.md](.planning/PROJECT.md) | USP, команда, vertical-templates |
| [.planning/agent-handbook/00-START-HERE.md](.planning/agent-handbook/00-START-HERE.md) | **AI-agent workflow protocol** (bootstrap) |
| [.planning/roadmap/README.md](.planning/roadmap/README.md) | Wave 0–5+ roadmap |
| [.planning/decisions/README.md](.planning/decisions/README.md) | ADR catalog (30+ решений) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Conventions + PR workflow |

## Make targets

```bash
make help               # self-documenting list
make install            # uv sync + npm ci
make dev                # docker compose up -d
make dev-bootstrap      # install + dev + wait + seed  [AC1]
make test               # pytest + vitest with coverage  [AC2]
make lint               # ruff + eslint + format checks  [AC7]
make typecheck          # mypy strict + tsc strict  [AC7]
make security           # bandit + pip-audit + npm audit
make clean              # wipe everything (compose -v + .venv + node_modules)
```

## Project structure

```
oriion/
├── backend/                # Python 3.12 + FastAPI + Pydantic-AI
│   ├── pyproject.toml      # uv-managed deps + ruff/mypy/pytest config
│   ├── src/                # backend package
│   ├── tests/              # pytest + async fixtures
│   ├── migrations/         # Alembic multi-version per ADR-024 (Phase 00.3+)
│   ├── alembic.ini         # migrations config
│   └── Dockerfile          # multi-stage (dev + prod)
│
├── frontend/               # Vite + React 19 + TypeScript + Tailwind v4
│   ├── package.json        # npm-managed deps
│   ├── src/                # React app
│   ├── tsconfig.json       # strict + noUncheckedIndexedAccess
│   └── Dockerfile          # multi-stage (dev + prod)
│
├── infra/                  # Local dev infrastructure
│   ├── docker-compose.dev.yml
│   ├── caddy/Caddyfile.dev
│   └── postgres/init-pgvector.sh
│
├── scripts/                # Bootstrap helpers
│   ├── wait_for_db.py
│   └── seed_dev_data.py
│
├── docs/                   # Plain markdown (MkDocs returns Wave 2+)
│
├── .github/workflows/      # CI: backend / frontend / security
│
├── .planning/              # Project planning + ADR + roadmap
└── .claude/agents/         # 11 persistent Opus AI-agent roles per ADR-023
```

## Status

**Wave 1 (Core MVP) — in progress.** Смержено: 01.1-retro … 01.8 (Master-Agent, billing-core, memory + auto-extraction, artifacts, security-substrate, RBAC, SMTP, 2FA/magic-link) + **01.4-ui memory panel**. Автономная очередь (product-first reorder, `/autonomy:run` 2026-07-09): **`01.4-ui ✅ → 01.9 → 01.10 → 01.12`**; 01.8c (dev-infra) отложена в конец. Актуальное состояние — [`.planning/STATUS.md`](.planning/STATUS.md); разблокировки — [`.planning/FOUNDER-RUNWAY.md`](.planning/FOUNDER-RUNWAY.md).

> Правило свежести (ADR-040 D9): эта секция обновляется в exit-ритуале каждой смерженной фазы.

## License

Proprietary — Kirill Uklonskiy <uklonskiy.k@gmail.com>.
