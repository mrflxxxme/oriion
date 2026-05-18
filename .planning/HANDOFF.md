# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-17 (architect-PR — iam contract extension + `_shared` bootstrap)
- Session: `architect-pre-00-2-contract-extension` (branch `claude/dazzling-satoshi-0a293d`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation) — Phase 00.1 ✅ **Complete** (merged 2026-05-17 via [PR #25](https://github.com/mrflxxxme/oriion/pull/25), merge-commit `b192c6b`)
- **Active phase:** **architect-PR (pre-00.2)** — extends `contracts/iam/*` для full-scope 00.2 + lands `_shared` foundation migration (поглощает Phase 00.3 bootstrap step). После merge — founder стартует 3 parallel sessions: 00.2 + 00.3 + 00.4.
- **3-way parallel** unblocked: `claude/phase-00-2-jwt-auth` (full-scope JWT auth + email verification + password reset + consent + audit emission via stub), `claude/phase-00-3-db-rls` (multitenancy + audit + RLS — bootstrap done in architect-PR), `claude/phase-00-4-llm-gateway` (LLM gateway + MCP infra using RLS + audit stubs). Integration в отдельной session `claude/phase-00-2-5-integration` после merge всех 3-х PR.
- **Wave 0 timeline:** 00.1 closed 2 дня раньше plan (-2 нед buffer); 3-way parallel должен сэкономить ~5-6 дней на 00.2/00.3/00.4; Wave 0 complete target unchanged at 2026-06-09 (могут оказаться раньше).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных, реальная обработка ПДн запрещена до closure. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

> **Closed `N/A`** per [P-INIT-5](./decisions/ADR-028-policies-registry.md): OQ-13, OQ-14, OQ-15, OQ-16 (hiring; solo + 11 AI model).
> **Closed `out-of-scope`** per Session-2026-05-15: OQ-17 (funding), OQ-18 (burn-budget).
> Полный реестр — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## What just happened (this session — architect-PR pre-00.2)

### Pre-grill discoveries

Founder grilled план для старта Phase 00.2 + одновременной параллелизации с 00.3 + 00.4. Grill вскрыл несколько contradictions/gaps в repo, которые нужно было закрыть **до** старта 3-х параллельных streams, иначе вышел бы integration drift:

1. **Hashing contradiction**: phase-spec 00.2 говорил `bcrypt cost 12`, но `contracts/iam/schema.sql` enforce'ит `password_algo CHECK (password_algo IN ('argon2id'))`. Phase 00.1 уже заменил passlib → argon2-cffi per ADR-014. **Resolved:** contract authoritative per ADR-024 → argon2id.
2. **OQ-04 contradiction**: phase-spec говорил «submitted ДО prod-launch, не блокирует dev work»; STATUS/HANDOFF говорили «Required до Phase 00.2». **Resolved:** Founder подтвердил submitted → dev unblocked.
3. **Contract gap**: phase-spec 00.2 references `iam.consents`, `iam.email_verification_tokens`, `iam.password_reset_tokens` — отсутствовали в `contracts/iam/schema.sql`. Founder выбрал Full-scope → extend contracts в architect-PR.
4. **Hidden coupling**: 00.2 нуждается в `multitenancy.provision_initial_workspace` (00.3) + `audit.audit_log` emission (00.3); 00.4 — в RLS context-setter (00.3) + audit emission. Чистый 3-way parallel возможен только через **contract-first stubs**.
5. **Phase 00.3 spec owns schema bootstrap** (CREATE SCHEMA + extensions + `_shared` trigger). Чтобы 3-way parallel заработал чисто, bootstrap нужно поднять «выше» 00.3 в architect-PR. Founder одобрил.
6. **Path correction**: plan upd referenced `backend/alembic/versions/`, но реальная директория — `backend/migrations/versions/` per alembic.ini line 13.

### Architect-PR — what landed in this branch

- **`contracts/iam/schema.sql`**: +3 таблицы (consents / email_verification_tokens / password_reset_tokens) с indexes + COMMENTs
- **`contracts/iam/api.yaml`**: +4 endpoints (verify-email / resend-verification / forgot-password / reset-password); `RegisterRequest` теперь требует `consent_pdn`; `RegisterResponse` schema с `{user_id, workspace_id, cell_id}`; +tag `verification`
- **`contracts/iam/events.yaml`**: +4 CloudEvents v1 (email_verification_requested / password_reset_requested / password_reset_completed / consent_recorded)
- **`contracts/iam/README.md`**: +4 инварианта (consent pdn mandatory, verification TTL 24h SHA-256, reset TTL 1h chain-revoke, anti-enumeration always-202); обновлён Phase references блок
- **`backend/migrations/versions/_shared/0001_init.py`** (НОВЫЙ): bootstrap migration — 5 extensions, 12 schemas, `_shared.set_updated_at()` trigger, `oriion_app` NOLOGIN role + USAGE grants. Branch label `_shared`.
- **`backend/migrations/versions/{iam,multitenancy,audit,billing,llm_gateway,rbac,agents,tasks,artifacts,memory,mcp}/.gitkeep`** (НОВЫЕ): placeholder для bounded-context migration dirs.
- **`backend/alembic.ini`**: `version_locations` extended 12-ю bounded-context subdirs
- **`.planning/STATUS.md`**: рассказ про architect-PR, OQ-04 updated to submitted, 3-way parallel unblocked
- **этот HANDOFF.md**: переписан с новой ориентацией на 3-way parallel

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

## Next steps — 3-way parallel after architect-PR merges

После merge architect-PR founder открывает **3 worktrees в 3 terminals** (sessions работают независимо). План — `C:\Users\KUklonskiy\.claude\plans\start-phase-00-2-of-dreamy-truffle.md` (доступен на founder machine), разделы Step 1a / 1b / 1c.

```bash
# Из репо root, на свежем main
git checkout main && git pull origin main

# Worktree 1 — Phase 00.2 (Custom JWT auth, full-scope)
git worktree add .planning/.claude/worktrees/phase-00-2-jwt-auth -b claude/phase-00-2-jwt-auth
# Открыть Claude Code session в этой дире, brief: "Start Phase 00.2 per plan Step 1a"
# Owner agents: backend-implementer + reviewer-security (tier 4)
# Stubs: backend/src/_stubs/multitenancy.py + audit.py (определены в плане)
# Defaults: argon2id, HS256, access 15min, refresh 7 days, rate-limit 5/15min, ≥85% coverage
# Env: REQUIRE_EMAIL_VERIFICATION=false в dev (console-stub SMTP)

# Worktree 2 — Phase 00.3 (DB + RLS + multitenancy)
git worktree add .planning/.claude/worktrees/phase-00-3-db-rls -b claude/phase-00-3-db-rls
# Brief: "Start Phase 00.3 per plan Step 1b. NOTE: schema bootstrap уже done в architect-PR;
#         00.3 стартует сразу с multitenancy DDL. Down_revision твоего первого migration = _shared_0001_init."
# Owner agents: backend-implementer + architect
# Producer real impls для: provision_initial_workspace + emit_audit_event + set_tenant_context

# Worktree 3 — Phase 00.4 (LLM gateway + MCP infra)
git worktree add .planning/.claude/worktrees/phase-00-4-llm-gateway -b claude/phase-00-4-llm-gateway
# Brief: "Start Phase 00.4 per plan Step 1c. Использует stubs из backend/src/_stubs/{rls,audit}.py;
#         inline SKELETON billing.credit_transactions per phase-spec line 37-64."
# Owner agents: backend-implementer + mcp-builder (spawn per phase)
# Live tests skipped без TBD_DEEPSEEK_API_KEY (gated via pytest -m live)
```

### Integration после merge 3-х PR

```bash
git checkout main && git pull origin main
git worktree add .planning/.claude/worktrees/phase-00-2-5-integration -b claude/phase-00-2-5-integration
# Brief: "Phase 00.2.5 integration. Delete backend/src/_stubs/, replace imports
#         to real impls from 00.3, run E2E smoke (register → verify → login → /api/llm/chat → refresh → logout),
#         update STATUS/HANDOFF/JOURNAL/PROJECT, mark 00.2/00.3/00.4 ✅ Complete."
```

## How a new session bootstraps

Bootstrap-4 как обычно:

1. [`README.md`](./README.md)
2. [`STATUS.md`](./STATUS.md) — current state включая architect-PR landing
3. **этот HANDOFF.md** — snapshot + next steps
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

Затем agent читает phase-spec из `.planning/roadmap/wave-0-foundation/phases/00.X-*.md` + раздел плана соответствующий Step 1a/1b/1c (founder может paste план inline или передать путь).

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

## Exit ritual completed (architect-PR session)

- [x] HANDOFF.md rewritten (this file) — 3-way parallel orientation
- [x] STATUS.md reflects current state (architect-PR landed, OQ-04 submitted, 3-way unblocked)
- [ ] JOURNAL.md — to append post-merge entry за architect-PR
- [ ] PROJECT.md — current-phase pointer to be updated к "architect-PR pre-00.2 → next: 3-way parallel 00.2/00.3/00.4"
- [ ] PR opened — pending (этот commit на ветке `claude/dazzling-satoshi-0a293d`)
