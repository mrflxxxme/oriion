# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-07-09
- Session: `/autonomy:run` — Wave-1 completion (product-first reorder)
- Agent: @claude (autonomous runner, ADR-037/040)

## Project status

- **Wave:** Wave 1 (Core MVP). Смержено всё до 01.8 включительно (`origin/main = 02cdb68`, #93) + инфра VPS-пилот (#91/#92) + search-fix (#93).
- **Эта сессия:** автономный раннер к «проверенно и полнофункционально закончить Wave 1», верификация на **VPS `staging.профики.online` (194.87.187.207)**, не в Docker.

## Run decisions (this session)

- **Reorder product-first** (DECISIONS-LOG `run-2026-07-09`): очередь исполнения **`01.4-ui → 01.9 → 01.10 → 01.12`**; **01.8c** (dev-infra service phase) отложена в конец / только-если-нужна. Причина: founder run-args = верифицируемое завершение **продукта** Wave 1 на сервере; 01.8c не в must-set и не даёт server-verifiable результата; нет жёсткой зависимости (независимые аудит-сабагенты спавнятся через Agent tool без нативных файлов 01.8c).
- Локальные гейты без `make` (нет на Windows): `cd backend && uv run ruff check/format --check src tests`, `uv run mypy --strict src`, `uv run pytest ... -m "not integration"`, `uv run bandit -r src -c pyproject.toml`; frontend `npm run lint/format:check/typecheck/test`.
- Deploy на VPS = ручной: GH Actions `build-images-ghcr` (main) → ssh `dc pull && dc up -d` (+ `alembic upgrade heads` при новых миграциях), где `dc='docker compose --env-file infra/vps-minimal.env -f infra/docker-compose.vps-minimal.yml'` (repo на боксе `/home/deploy/oriion`). Frontend server-verifiable (Caddy отдаёт `/srv/frontend` из one-shot-volume).

## What just happened — Phase 01.4-ui MERGED-READY

**Memory panel «Что помнит команда/агент»** — code-complete + locally verified (branch `claude/auto-01.4-ui-memory-panel`). Frontend-фича поверх live `/api/v1/memory/*`:
- Два таба: **Ячейка** (cell-memory) / **Агент** (role-memory, picker по `GET /cells/{id}/agents`).
- list + семантический поиск (`?q=`) + add (`source=manual`) + delete c confirm (Radix Dialog); source-бейджи (manual/filter_agent/summary); edit = delete+add (append-only, PATCH нет).
- API-клиенты `frontend/src/api/memory.ts` + `agents.ts` — схемы pinned к реальному бэку (проверено: поля MemoryEntryOut, param `q`, endpoint `/cells/{id}/agents` существует).
- Форки (2, agent-owned, logged): delete-права = любой член cell (match live RLS, Owner-gate отсутствует); edit=delete+add.
- **Гейты green (независимо перепрогнаны):** eslint --max-warnings=0 · prettier · tsc strict · vitest 181 pass / features-memory 94% cov · axe 0 violations (jest-axe).
- Tripwire: чистый frontend → exit 0 → **auto-merge** (без founder ack). Live-golden **N/A ($0)**.
- Артефакты: `PLAN.md`, `UI-SPEC-01.4-ui.md`, runbook `docs/runbooks/memory-panel.md`.

## In progress / not done (deliberately)

- **Server-verify 01.4-ui** — после deploy на VPS (build-images-ghcr → dc pull frontend → браузер-проверка панели). Не блокирует merge (tripwire-free FE).
- Следующая фаза: **01.9 MCP-серверы + DLP-активация** (hard, tripwire: secrets_keys_crypto + возможно db_migrations; live-golden ~$1-2; SECURE-priority adversarial audit). Ожидается founder ack на tripwire.
- 01.8c отложена (см. Run decisions).

## Next agent — read first

1. [`README.md`](./README.md) · 2. **this HANDOFF** · 3. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) · 4. раннер-контракты: [`DEFINITION-OF-READY.md`](./roadmap/DEFINITION-OF-READY.md) + [`FOUNDER-RUNWAY.md`](./FOUNDER-RUNWAY.md) + [`DEFERRED-VERIFICATION.md`](./DEFERRED-VERIFICATION.md).

## Exit ritual (this phase)

- [x] JOURNAL.md entry appended (2026-07-09)
- [x] HANDOFF.md rewritten (this file)
- [x] Doc-sync (ADR-040 D9): README status/queue actual · 01.4-ui spec Status ≠ Pending · runbook `docs/runbooks/memory-panel.md` created · no roadmap reorg → no gate-file sync needed
- [ ] PR opened + CI green + tripwire exit 0 → auto-merge → deploy → server-verify
