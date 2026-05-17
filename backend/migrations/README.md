# backend/migrations — Alembic multi-version directory

Phase 00.1: config skeleton. Per [ADR-024](../../.planning/decisions/ADR-024-bounded-context-contracts.md) каждый bounded context получает свой подкаталог в `versions/` с **независимой linear history**:

```
migrations/
├── env.py                # async-compatible runner (multi-version aware)
├── script.py.mako        # revision template
└── versions/
    ├── iam/              # Phase 00.2 — auth/jwt/users
    ├── multitenancy/     # Phase 00.3 — cells, workspaces, RLS
    ├── billing/          # Wave 1 — credits, ЮKassa
    ├── agents/           # Phase 00.5 — agent runtime tables
    ├── artifacts/        # Wave 1 — pixel department artifacts
    ├── llm-gateway/      # Phase 00.4 — provider routing
    ├── mcp/              # Wave 2 — MCP tool registry
    ├── memory/           # Wave 1 — agent + team memory
    ├── rbac/             # Wave 1 — roles, permissions
    └── tasks/            # Wave 1 — task lifecycle
```

## Commands

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Create new revision в default branch (Phase 00.1 — single default)
uv run alembic revision -m "add foo"

# Phase 00.3+ — create revision в specific bounded context
uv run alembic revision --branch-label iam -m "add users table"

# Apply only one bounded context
uv run alembic upgrade iam@head
```

## Configuration

- `alembic.ini` — `version_locations` enumerates active context paths
- `env.py` — async runner, reads `DATABASE_URL` env override
- `script.py.mako` — modern Python type-hints (`str | None`, no Optional)

## Phase 00.1 status

Skeleton only. Real schema появляется в Phase 00.3 (DB + RLS + Cell schema).
