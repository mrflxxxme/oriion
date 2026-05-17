# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-17
- Session: `amazing-hamilton-8b9d2c` (Phase 00.1 Repo & CI/CD — monorepo + dev stack + CI workflows + pre-commit + bootstrap docs)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — started 2026-05-17
- **Active phase:** Phase 00.1 (Repo & CI/CD) — **implementation complete in branch, awaiting founder review + merge + local AC1/AC6 verification**
- **Next phase:** Phase 00.2 (Custom JWT auth) — depends on Phase 00.1 merge + OQ-04 РКН close. Parallel-ready: 00.3 (DB+RLS+Cell schema, depends 00.1) + 00.4 (LLM gateway + MCP, depends 00.1).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | Required до Phase 00.2 (НЕ блокирует merge 00.1) |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

Полный реестр — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## What just happened (this session — 16 commits)

### Spec amendments (commit #1)

Per founder decision — **small trim** для maximum MVP velocity:
- Drop `infra/terraform/` (cloud provisioning returns Phase 00.6 as YC manual runbook)
- Drop `docs/mkdocs.yml` (plain markdown sufficient until Wave 2+)
- Drop `docs/gitlab-mirror.md` + AC6 (GitLab mirror Wave 1+ deferred)
- Drop `infra/docker-compose.staging.yml` (Phase 00.6 deliverable)
- Merge license-check (forbid GPL/AGPL/LGPL) as step into `ci-backend.yml` + `ci-frontend.yml` (no standalone `ci-license.yml`)
- Renumber AC: 8 → 7 (original AC6 GitLab mirror removed, AC7→AC6, AC8→AC7)

### Implementation (commits #2-#16)

**Monorepo structure:**
- `.gitignore` extended для coverage/vite cache + claude-internal state (.omc/, .claude-flow/, .swarm/, .hive-mind/)
- `.gitattributes` для LF-enforcement on Makefile/shell/yaml/dockerfile/python/typescript
- Root `Makefile` (POSIX, 18 targets, TAB-indented) — `make help/install/dev/dev-bootstrap/test/lint/typecheck/security/clean`
- Root `README.md` (Quickstart 10-min + Stack + cross-refs + project tree)
- Root `CONTRIBUTING.md` (bootstrap-4 + tier-table + ADR workflow + PR checklist)
- Root `.env.example` (20 vars: dev defaults + TBD_ literals per PLACEHOLDERS.md)
- Root `.pre-commit-config.yaml` + `.markdownlint.json`

**Backend (`backend/`):**
- `pyproject.toml` — uv-managed deps: fastapi 0.115 / uvicorn / pydantic 2.9 / sqlalchemy[asyncio] 2.0.36+ / asyncpg / alembic / redis / dramatiq / httpx / python-jose / passlib + dev: pytest 8.3 + pytest-asyncio + pytest-cov + ruff 0.7 + mypy 1.13 strict + bandit + pip-audit + pip-licenses
- `src/__init__.py` — `__version__ = "0.1.0"`
- `src/main.py` — minimal FastAPI app с `/health` endpoint (drives AC6)
- `tests/conftest.py` — async db_engine + db_session fixtures (integration-only)
- `tests/test_smoke.py` (3 tests) + `tests/test_health.py` (5 tests) — 8 tests, 100% coverage
- `Dockerfile` (multi-stage dev + prod)
- `alembic.ini` + `migrations/env.py` (async runner) + `migrations/script.py.mako` + `migrations/README.md` — multi-version-directory config per ADR-024 (bounded contexts materialize Phase 00.3)
- `uv.lock` committed для reproducible CI

**Frontend (`frontend/`):**
- `package.json` — Vite 6 / React 19 / TypeScript 5.7 / TanStack Router 1.85 / Tailwind v4 / @tailwindcss/vite / shadcn-style utils (clsx + tailwind-merge + class-variance-authority + lucide-react) + ESLint 9 flat config + Prettier 3.4 + vitest 2.1 + @testing-library
- `tsconfig.json` — strict + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`
- `vite.config.ts` + `vitest.config.ts` (jsdom env, coverage thresholds 70%)
- `eslint.config.js` (flat config, strictTypeChecked)
- `tailwind.config.ts` (minimal v4 shim; real config в CSS @theme)
- `components.json` (shadcn marker, new-york + neutral)
- `index.html` + `src/main.tsx` (React 19 createRoot + placeholder UI)
- `src/styles/index.css` (Tailwind v4 @import + @theme placeholder)
- `src/lib/utils.ts` + `src/lib/utils.test.ts` (cn() helper, 5 tests, 100% coverage)
- `src/test/setup.ts` (jest-dom + RTL cleanup)
- `Dockerfile` (multi-stage dev + prod)
- `package-lock.json` committed для reproducible CI

**Infrastructure (`infra/`):**
- `docker-compose.dev.yml` — 6 services (postgres pgvector/pgvector:pg16 + redis 7 + minio + backend + frontend + caddy) с healthchecks, 7 named volumes
- `caddy/Caddyfile.dev` — dev reverse proxy с WebSocket upgrade headers для Vite HMR
- `postgres/init-pgvector.sh` — CREATE EXTENSION vector + pg_trgm + unaccent

**Helper scripts (`scripts/`):**
- `wait_for_db.py` — async poll loop Postgres + Redis readiness (configurable WAIT_TIMEOUT)
- `seed_dev_data.py` — verify DB + pgvector extension; domain seed stub (Phase 00.3 fills real)

**CI workflows (`.github/workflows/`):**
- `ci-backend.yml` — ruff + mypy strict + pytest --cov 70% + bandit + pip-audit + pip-licenses + Codecov; pgvector+redis service containers
- `ci-frontend.yml` — eslint + prettier + tsc + vitest + Vite build smoke + npm audit + license-checker + Codecov
- `ci-security.yml` — 3 parallel jobs: gitleaks+trufflehog / Trivy filesystem SARIF / Syft SBOM + Grype SARIF
- All workflows: timeout-minutes 8, concurrency cancel-in-progress, permissions minimal

## Local verification (30-min timebox)

| AC | Status | Notes |
|---|---|---|
| **AC1** dev-bootstrap ≤ 600s | ⚠️ **DEFERRED** | docker pull failed с "unexpected EOF" — network/registry connectivity issue; founder верифицирует post-merge |
| **AC2** coverage ≥ 70% | ✅ | backend 100% (8 tests), frontend utils.ts 100% (5 tests) |
| **AC3** PR triggers 3 CI workflows ≤ 8 min | 📋 | Self-verifies при открытии PR |
| **AC4** gitleaks blocks AWS key | 📋 | Self-verifies через CI workflows (можно проверить test-PR с planted secret) |
| **AC5** license-check blocks GPL-3.0 | 📋 | Self-verifies через CI workflows |
| **AC6** compose healthchecks ≤ 180s | ⚠️ **DEFERRED** | Same root cause as AC1 (docker pull network) |
| **AC7** lint + typecheck exit 0 | ✅ | backend ruff + ruff-format + mypy strict pass; frontend eslint + prettier + tsc pass |

**Founder action для AC1/AC6:** запустить `cp .env.example .env && docker compose -f infra/docker-compose.dev.yml up -d --build` на своей машине с stable Docker Hub access. Должно завершиться <600s + все healthchecks зелёные <180s.

## Next agent — read first

Bootstrap (4 файла):
1. [`README.md`](./README.md) — что за проект
2. [`STATUS.md`](./STATUS.md) — текущее состояние, blockers
3. этот HANDOFF.md
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

После bootstrap → Phase 00.2 spec (когда merged) или Phase 00.1 revision-loop (если AC fail при founder verification).

## Next steps (priority order)

### Founder action — pre-merge

1. **Local AC1 + AC6 verification:**
   ```bash
   cp .env.example .env
   docker compose -f infra/docker-compose.dev.yml up -d --build
   # wait for healthchecks
   docker compose -f infra/docker-compose.dev.yml ps
   # all 6 services should be `healthy` within 180s
   ```
   Если pull fails — повторить `docker compose pull` отдельно (network may be transient).

2. **Push branch + open PR (tier 4):**
   ```bash
   git push -u origin claude/amazing-hamilton-8b9d2c
   gh pr create --title "feat: Phase 00.1 — Repo & CI/CD" --body-file <AUDIT-REPORT>
   ```

3. **CI workflows self-verify AC3/AC4/AC5** when PR opens — wait for green checks before merge.

4. **Founder approve + merge** (tier 4 per [ADR-027](./decisions/ADR-027-solo-ai-git-pr-workflow.md) + [P-INIT-3](./decisions/ADR-028-policies-registry.md#policies-canonical-home)).

### AI-agent action — после merge в main

5. **Memory-curator session** обновляет:
   - STATUS.md: Phase 00.1 → Done; Wave 0 progress
   - PLACEHOLDERS.md: TBD_DEEPSEEK_API_KEY если founder зарегистрировал ключ
   - JOURNAL: short merge entry

6. **Start Phase 00.2 (Custom JWT auth):**
   - REQUIRES OQ-04 (РКН) closed first
   - Owner: backend-implementer + reviewer-security
   - Phase spec: `roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md` (existing)

7. **Parallel-ready phases после 00.1 merge:**
   - 00.3 (DB + RLS + Cell schema) — depends 00.1 only
   - 00.4 (LLM gateway + MCP) — depends 00.1 only

## Ready-to-merge checklist

- ✅ Spec amendments applied (commit #1)
- ✅ Backend skeleton (uv + ruff + mypy strict + pytest + FastAPI + Alembic)
- ✅ Frontend skeleton (Vite 6 + React 19 + TS strict + Tailwind v4 + shadcn + ESLint 9 + Prettier + vitest)
- ✅ Infrastructure (docker-compose.dev.yml + Caddy + pgvector init + Dockerfiles)
- ✅ Helper scripts (wait_for_db + seed_dev_data)
- ✅ Makefile (POSIX, 18 targets) + .gitattributes
- ✅ CI workflows (ci-backend + ci-frontend + ci-security, all tier 4)
- ✅ Pre-commit config + markdownlint
- ✅ Bootstrap docs (.env.example + README + CONTRIBUTING)
- ✅ Lock files committed (uv.lock + package-lock.json)
- ✅ AC2 local-verified (≥70% coverage)
- ✅ AC7 local-verified (lint + typecheck)
- ⚠️ AC1 + AC6 local-deferred (Docker pull network issue) — founder verifies
- 📋 AC3/AC4/AC5 self-verify через CI when PR opens

## Files modified this session

- **CREATED (45+ files):** see file-tree in [`README.md`](./README.md). Highlights:
  - Root: `Makefile`, `.env.example`, `.pre-commit-config.yaml`, `.markdownlint.json`, `.gitattributes`, `README.md`, `CONTRIBUTING.md`, `.gitignore` (extended)
  - `backend/`: `pyproject.toml`, `Dockerfile`, `.dockerignore`, `alembic.ini`, `src/__init__.py`, `src/main.py`, `migrations/{env.py, script.py.mako, versions/.gitkeep, README.md}`, `tests/{__init__.py, conftest.py, test_smoke.py, test_health.py}`, `uv.lock`
  - `frontend/`: `package.json`, `Dockerfile`, `.dockerignore`, `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `tailwind.config.ts`, `eslint.config.js`, `.prettierrc.json`, `.prettierignore`, `components.json`, `index.html`, `src/{main.tsx, vite-env.d.ts, styles/index.css, lib/utils.ts, lib/utils.test.ts, test/setup.ts}`, `package-lock.json`
  - `infra/`: `docker-compose.dev.yml`, `caddy/Caddyfile.dev`, `postgres/init-pgvector.sh`
  - `scripts/`: `wait_for_db.py`, `seed_dev_data.py`
  - `.github/workflows/`: `ci-backend.yml`, `ci-frontend.yml`, `ci-security.yml`
- **MODIFIED:** `.planning/roadmap/wave-0-foundation/phases/00.1-repo-cicd.md` (trim), `.planning/JOURNAL.md` (this session entry), `.planning/HANDOFF.md` (this file), `.planning/STATUS.md` (Phase 00.1 In Progress)
- **16 commits:** spec trim → monorepo skeleton → backend → frontend → infra → scripts → Makefile → Alembic → 3 CI workflows → pre-commit → bootstrap docs → lock files → format fixes → test_health → exit ritual

## Known caveats

- **AC1 + AC6 deferred** — Docker registry pull failed в этой сессии с EOF errors. Не related к Phase 00.1 spec corrections, network/connectivity issue. Founder верифицирует на машине с stable Docker Hub access.
- **Pre-commit hooks НЕ installed** в этой ветке — `pre-commit install` ran бы установил git hooks. Founder может сделать `uv run pre-commit install` или `pre-commit install` после clone. CI gates всё равно дублируют все проверки.
- **`infra/postgres/init-pgvector.sh` shebang** — `#!/usr/bin/env sh` для POSIX. На Windows shebang ignored, но скрипт executes correctly в Linux container (постгрес init-dir mechanism).
- **Frontend coverage = 100% только на `utils.ts`** — `main.tsx` excluded из coverage (UI bootstrap). По мере роста frontend (Phase 00.7) coverage будет расти органически.

## Build / test state

- backend: pytest 8/8 ✅, ruff ✅, mypy --strict ✅, coverage 100%
- frontend: vitest 5/5 ✅, eslint ✅, prettier ✅, tsc -b ✅, coverage 100% on utils.ts
- docker compose: AC1/AC6 not verified в этой session (network)
- CI workflows: not triggered (branch not pushed yet)

## Exit ritual completed

- [x] JOURNAL.md updated (Session-2026-05-17 entry appended in commit #17 — exit ritual)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md reflects current state (Phase 00.1 In Progress → Pending merge)
- [x] OPEN-QUESTIONS.md reviewed (no new questions opened this session)
- [ ] Final consistency audit (4 parallel subagents) — running next
- [ ] PR opened — founder action after audit verdict 🟢/🟡
