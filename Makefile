# TEAMLY_RU — top-level Makefile
#
# POSIX make targets для local dev + CI. Работают на:
#   - Linux + macOS (system make)
#   - Windows (Git Bash + GNU make from chocolatey/scoop)
#   - WSL2 (Linux make)
#
# Quickstart (fresh clone):
#
#     cp .env.example .env
#     make dev-bootstrap   # → AC1: should complete ≤ 600s
#
# AC reference:
#   AC1: `make dev-bootstrap` ≤ 600s
#   AC2: `make test` passes, coverage ≥ 70%
#   AC6: `make dev` healthchecks ≤ 180s
#   AC7: `make lint` + `make typecheck` exit 0

SHELL := /bin/sh
.SHELLFLAGS := -eu -c
.DEFAULT_GOAL := help

COMPOSE_FILE := infra/docker-compose.dev.yml
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE)
UV := uv
NPM := npm

# ─────────────────────────────────────────────────────────────
# Self-documenting help — `make` без аргументов печатает targets

.PHONY: help
help: ## Print this help (default target)
	@printf '\nTEAMLY_RU — available targets:\n\n'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nQuickstart:  cp .env.example .env  &&  make dev-bootstrap\n\n'

# ─────────────────────────────────────────────────────────────
# Install — fetch dependencies для backend + frontend

.PHONY: install
install: install-backend install-frontend ## Install backend + frontend deps (uv sync + npm ci)

.PHONY: install-backend
install-backend:
	@printf '→ Installing backend dependencies via uv...\n'
	cd backend && $(UV) sync

.PHONY: install-frontend
install-frontend:
	@printf '→ Installing frontend dependencies via npm...\n'
	cd frontend && $(NPM) ci --no-audit --no-fund

# ─────────────────────────────────────────────────────────────
# Dev stack — docker-compose up/down

.PHONY: dev
dev: ## Start dev stack via docker compose (postgres + redis + minio + backend + frontend + caddy)
	@printf '→ Starting dev stack...\n'
	$(DOCKER_COMPOSE) up -d
	@printf '\n→ Backend:  http://localhost:8000  (docs: /docs)\n'
	@printf '→ Frontend: http://localhost:5173\n'
	@printf '→ Caddy:    http://localhost      (proxies above)\n'
	@printf '→ MinIO:    http://localhost:9001 (credentials in .env — MINIO_ACCESS_KEY / MINIO_SECRET_KEY)\n\n'

.PHONY: dev-stop
dev-stop: ## Stop dev stack (keeps volumes)
	$(DOCKER_COMPOSE) stop

.PHONY: logs
logs: ## Tail dev stack logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: dev-bootstrap
dev-bootstrap: ## Full cold-start: install + dev + wait + seed  [AC1: ≤ 600s]
	@printf '→ Phase 00.1 bootstrap (AC1: target ≤ 600s)\n'
	@printf '─────────────────────────────────────────────\n'
	@time ( \
		$(MAKE) install && \
		$(MAKE) dev && \
		cd backend && $(UV) run python ../scripts/wait_for_db.py && \
		$(UV) run python ../scripts/seed_dev_data.py \
	)
	@printf '\n✓ Bootstrap completed — verify via acceptance criteria\n'

# ─────────────────────────────────────────────────────────────
# Test / lint / typecheck

.PHONY: test
test: test-backend test-frontend ## Run backend pytest + frontend vitest with coverage [AC2: ≥ 70%]

.PHONY: test-backend
test-backend:
	@printf '→ Backend: pytest + coverage (fail-under 70%%)\n'
	cd backend && $(UV) run pytest --cov=src --cov-report=term-missing --cov-fail-under=70 -m "not integration"

.PHONY: test-backend-integration
test-backend-integration:
	@printf '→ Backend: integration tests (requires dev stack up)\n'
	cd backend && $(UV) run pytest -m integration

.PHONY: test-frontend
test-frontend:
	@printf '→ Frontend: vitest + coverage\n'
	cd frontend && $(NPM) test

.PHONY: lint
lint: lint-backend lint-frontend ## Run ruff + eslint  [AC7]

.PHONY: lint-backend
lint-backend:
	cd backend && $(UV) run ruff check src tests
	cd backend && $(UV) run ruff format --check src tests

.PHONY: lint-frontend
lint-frontend:
	cd frontend && $(NPM) run lint
	cd frontend && $(NPM) run format:check

.PHONY: format
format: ## Auto-fix lint/format issues (ruff format + prettier write)
	cd backend && $(UV) run ruff check --fix src tests
	cd backend && $(UV) run ruff format src tests
	cd frontend && $(NPM) run lint:fix
	cd frontend && $(NPM) run format

.PHONY: typecheck
typecheck: typecheck-backend typecheck-frontend ## Run mypy strict + tsc strict  [AC7]

.PHONY: typecheck-backend
typecheck-backend:
	cd backend && $(UV) run mypy --strict src

.PHONY: typecheck-frontend
typecheck-frontend:
	cd frontend && $(NPM) run typecheck

# ─────────────────────────────────────────────────────────────
# Security — local-runnable subset CI workflows

.PHONY: security
security: ## Run security scanners (bandit + pip-audit + npm audit)
	cd backend && $(UV) run bandit -r src -c pyproject.toml
	cd backend && $(UV) run pip-audit --strict
	cd frontend && $(NPM) audit --audit-level=high || true

# ─────────────────────────────────────────────────────────────
# Clean — wipe everything

.PHONY: clean
clean: ## Stop dev stack + remove volumes + remove .venv + node_modules
	-$(DOCKER_COMPOSE) down -v --remove-orphans
	-rm -rf backend/.venv frontend/node_modules
	-rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/coverage.xml
	-rm -rf frontend/.vite frontend/dist frontend/coverage
	@printf '✓ Clean complete\n'

.PHONY: clean-soft
clean-soft: ## Stop dev stack (keeps volumes + node_modules + .venv)
	-$(DOCKER_COMPOSE) down
	@printf '✓ Dev stack stopped (volumes preserved)\n'
