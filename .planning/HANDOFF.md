# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-17 (post-merge memory-curator pass)
- Session: `post-00.1-memory-curator` (после merge PR #25)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — Phase 00.1 ✅ **Complete** (merged 2026-05-17 via [PR #25](https://github.com/mrflxxxme/oriion/pull/25), merge-commit `b192c6b`)
- **Active phase:** **none** — между Phase 00.1 (done) и Phase 00.2 (gated by OQ-04). Founder action или parallel-start 00.3/00.4 — see "Next steps" ниже.
- **Wave 0 timeline:** 00.1 closed 2 дня раньше plan (-2 нед buffer); Wave 0 complete target unchanged at 2026-06-09.

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Required до Phase 00.2** (auth = ПДн обработка; nuance в [OPEN-QUESTIONS.md](./OPEN-QUESTIONS.md)) |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

> **Closed `N/A`** per [P-INIT-5](./decisions/ADR-028-policies-registry.md): OQ-13, OQ-14, OQ-15, OQ-16 (hiring; solo + 11 AI model).
> **Closed `out-of-scope`** per Session-2026-05-15: OQ-17 (funding), OQ-18 (burn-budget).
> Полный реестр — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## What just happened (this session — 1 memory-curator commit, separate from Phase 00.1)

### Phase 00.1 — merged (PR #25)

**21 atomic commits на ветке `claude/amazing-hamilton-8b9d2c`** (теперь merged + ветка может быть удалена):

1-18. Phase 00.1 implementation: spec trim → monorepo skeleton (backend + frontend + infra + scripts) → Makefile + .gitattributes → Alembic config → 3 CI workflows → pre-commit → bootstrap docs → lock files → format fixes → test_health → exit ritual → gitignore tweak
19. Final consistency audit fix pass (4 BLOCK + 5 WARN resolved inline)
20-21. CI fix passes (security dep replacement + Trivy action version + pip-audit --skip-editable)

**Final CI verdict:** все 6 checks PASS (ci-backend / ci-frontend / 3 ci-security jobs / gitleaks). AC3/AC4/AC5 self-verified в CI.

### Security debt resolved inline (originally tagged Phase 00.2 prerequisite)

- `python-jose` v3.5 (CVE-2024-33663 ECDSA, CVE-2024-33664 DoS — both HIGH) → **PyJWT[crypto] ≥ 2.10**
- `passlib` v1.7.4 (unmaintained since 2020) → **argon2-cffi ≥ 23.1** per [ADR-014](./decisions/ADR-014-security.md)
- FastAPI 0.115 → 0.129 (pulls **starlette 0.52.1**, fixes CVE-2025-54121 + CVE-2025-62727)
- pytest 8.3 → 9.0 (fix CVE-2025-71176); pytest-asyncio → 1.x; pytest-cov → 7.x

Backend deps теперь чистые для `pip-audit --skip-editable` (0 vulnerabilities).

### Memory-curator pass (this commit)

- STATUS.md: Phase 00.1 → ✅ Complete; final AC scoreboard; OQ-04 explicitly tagged как 00.2 blocker
- JOURNAL.md: post-merge entry appended (append-only protocol respected)
- PROJECT.md: current phase pointer → "Phase 00.1 Complete; Next: 00.2 (gated OQ-04), parallel 00.3/00.4"
- HANDOFF.md: this file rewritten

## Next agent — read first

Bootstrap (4 файла, как обычно):

1. [`README.md`](./README.md) — что за проект (~2 KB)
2. [`STATUS.md`](./STATUS.md) — текущее состояние, blockers, AC scoreboard Phase 00.1
3. **этот HANDOFF.md** — snapshot
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

После bootstrap → выбор фазы (см. Next steps ниже).

## Founder action (post-merge verification — НЕ обязательно перед next AI session)

Эти AC были deferred в session из-за docker-pull network failure. Founder верифицирует когда удобно:

```bash
# В чистой клон main:
git clone https://github.com/mrflxxxme/oriion teamly-test && cd teamly-test
cp .env.example .env
time docker compose -f infra/docker-compose.dev.yml up -d --build
# Expect: AC1 ≤ 600s cold-start
docker compose -f infra/docker-compose.dev.yml ps
# Expect: AC6 — all 6 services `healthy` ≤ 180s
```

Если что-то сломается → revision-loop через short follow-up PR.

## Next steps (priority order)

### Option A — Phase 00.2 (если OQ-04 закрыт)

**Phase 00.2: Custom JWT auth** — [`roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md`](./roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md).

- Owner: `backend-implementer` + `reviewer-security` (tier 4)
- Prerequisites: ✅ Phase 00.1 merged · ✅ PyJWT + argon2-cffi уже в deps · ⚠️ **OQ-04 РКН должно быть closed**
- Estimated: 3 дня
- Deliverables: JWT issue/verify, refresh tokens, password hashing (Argon2id), `iam` bounded-context migrations (first user в `migrations/versions/iam/`), `/auth/register` + `/auth/login` + `/auth/refresh` endpoints

### Option B — Phase 00.3 (parallel-ready, NOT gated by OQ-04)

**Phase 00.3: DB + RLS + Cell schema** — [`roadmap/wave-0-foundation/phases/00.3-db-rls-multitenancy.md`](./roadmap/wave-0-foundation/phases/00.3-db-rls-multitenancy.md).

- Owner: `backend-implementer` + `architect` (cell-isolation review)
- Prerequisites: ✅ Phase 00.1 merged · ✅ pgvector + pg_trgm + unaccent ready · ✅ Alembic multi-version-directory configured
- First action: extend `backend/alembic.ini` `version_locations` с bounded-context subdirs per ADR-024 §4 (multitenancy/iam/billing/agents/...)
- Estimated: 4 дня

### Option C — Phase 00.4 (parallel-ready, NOT gated by OQ-04)

**Phase 00.4: LLM gateway + MCP** — [`roadmap/wave-0-foundation/phases/00.4-llm-gateway.md`](./roadmap/wave-0-foundation/phases/00.4-llm-gateway.md).

- Owner: `backend-implementer` + `mcp-builder` (spawn per phase)
- Prerequisites: ✅ Phase 00.1 merged · ✅ httpx + Dramatiq + Redis ready · `TBD_DEEPSEEK_API_KEY` + `TBD_YANDEX_GPT_API_KEY` + `TBD_GIGACHAT_AUTH_KEY` могут быть set founder если ключи зарегистрированы
- Estimated: 4 дня

### Recommendation

**Если OQ-04 closed** → Option A (Phase 00.2 первой, dependency root для других phases).

**Если OQ-04 ещё открыт** → Option B + Option C в parallel (2 worktrees). 00.3 строит data foundation для 00.5 productivity-core team, 00.4 строит LLM gateway для всех downstream agent calls. После closure OQ-04, добавится 00.2 в parallel.

## How to start next session

```bash
# Из репо root:
git checkout main && git pull origin main
git worktree add .planning/.claude/worktrees/<new-slug> -b claude/<phase-slug>

# В worktree:
cd .planning/.claude/worktrees/<new-slug>
# Затем agent делает bootstrap-4 (README + STATUS + HANDOFF + 00-START-HERE)
# и выбирает фазу per Next steps выше.
```

Suggested next slug: `phase-00-2-jwt-auth` или `phase-00-3-db-rls` или `phase-00-4-llm-gateway` (per option chosen).

## Build / test state

- backend: pytest 8/8 ✅, ruff ✅, mypy --strict ✅, coverage 100%, pip-audit clean
- frontend: vitest 5/5 ✅, eslint ✅, prettier ✅, tsc -b ✅, npm audit clean
- docker compose: AC1/AC6 — founder local-verify pending
- CI workflows: all 6 status checks PASS на final PR run; branch protection ready принимать future PRs

## Tracked для downstream phases (Phase 00.6 polish)

Не блокирующие, но запланированные на Phase 00.6 (deploy + observability):

- Caddyfile.prod — explicit X-Forwarded-* trusted_proxies (security WARN из audit)
- Restore backend + frontend Dockerfile prod stages с правильным COPY ordering + build context (root context instead of subdir)
- MinIO healthcheck → `curl /minio/health/ready` (mc alias setup overhead avoidance)
- Sentry DSN provisioning (TBD_SENTRY_DSN)
- YC Compute VM provision via manual runbook

## Known caveats

- Pre-commit hooks: дев должен запустить `uv run pre-commit install` или `pre-commit install` после clone. CI gates всё равно дублируют все проверки.
- `frontend/coverage/` directory — gitignored, генерируется vitest --coverage.
- Phase 00.1 spec line 3 says "Status: 🔄 In progress" — это историческая запись на момент implementation; реальный статус = ✅ Complete per STATUS.md (single source of truth).

## Exit ritual completed

- [x] JOURNAL.md updated (post-merge entry 2026-05-17 appended)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md reflects current state (Phase 00.1 ✅ Complete; Wave 0 in progress)
- [x] PROJECT.md current phase pointer updated
- [ ] PR opened — pending (this commit будет на ветке `claude/post-00.1-memory-curator`)
