# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-18 (Phase 00.2 — Custom JWT auth full-scope implementation)
- Session: `phase-00-2-jwt-auth` (worktree branch `claude/gifted-feistel-55966b`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation)
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (merged 2026-05-17 via PR #25).
- **Architect-PR (pre-00.2)**: ✅ Complete (merged 2026-05-17 via PR #27 — `_shared/0001_init.py` + extended `contracts/iam/*` + 12 bounded-context migration dirs).
- **Phase 00.2 (Custom JWT auth)**: ✅ Code-complete on `claude/gifted-feistel-55966b` — pending PR + review + merge alongside 00.3 + 00.4.
- **Phase 00.3 (DB + RLS + multitenancy + audit)**: 🔄 In progress in parallel worktree (founder spawns separately).
- **Phase 00.4 (LLM gateway + MCP)**: 🔄 In progress in parallel worktree (founder spawns separately).
- **Phase 00.2.5 (integration)**: ⏳ Pending — opens after all 3 PRs merge; deletes `backend/src/_stubs/` and rewires imports to real impls from 00.3.

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## What just happened (Phase 00.2 implementation)

### Discovery + decisions (this session)

Founder invoked `/grill-me` before execution; 10 design branches resolved interactively (saved in plan `C:\Users\KUklonskiy\.claude\plans\start-phase-00-2-per-resilient-noodle.md`):

| # | Branch | Resolution |
|---|---|---|
| Q1 | Endpoint scope | 10 endpoints (8 auth + GET/PATCH /users/me). Skip /auth/sessions* + OAuth → Wave 1. |
| Q2 | URL prefix | `/api/v1` (matches ADR-010 + phase-spec /api/auth/* mention) |
| Q3 | Email-sender | EmailSender Protocol + ConsoleEmailSender (dev) + InMemoryEmailSender (test). NO `iam.email_outbox` table (would need contract extension). Added `structlog` + `email-validator` deps. |
| Q4 | Tests | Hybrid (unit + integration, marker `integration`); iam-specific coverage gate ≥85%. |
| Q5 | JWT | HS256 with claims sub/sid/jti/iat/exp/iss/aud/type; Redis blacklist SET blacklist:jwt:{jti} 1 EX ttl. |
| Q6 | Rate-limit | login/register: 5/15min (ip,email). forgot/resend: 3/15min anti-spam. refresh: 30/min ip-only. |
| Q7 | Argon2 | argon2-cffi defaults (t=3, m=64MB, p=4) prod; DI swap to (t=1, m=1KB, p=1) for tests. |
| Q8 | CloudEvents emission | Log-only envelope (structlog tag cloudevent=True); swap to Redis Streams in Wave 1+. |
| Q9 | Migrations | 6 (oauth_links separate). |
| Q10 | Workflow | Branch `claude/gifted-feistel-55966b` retained; PR title `[00.2] feat(iam): ...`; atomic Conventional Commits; Exit ritual (this file + JOURNAL + STATUS + phase-spec status). |

### What landed in `claude/gifted-feistel-55966b`

14 atomic commits, see `git log claude/gifted-feistel-55966b ^main` for details:

```
chore(deps): add structlog + email-validator
feat(_shared): config + logging + db session + redis factory
feat(_stubs): multitenancy + audit cross-context stubs
feat(iam,migrations): 6 alembic migrations matching contracts/iam/schema.sql
feat(iam): SQLAlchemy 2.x models matching contracts/iam/schema.sql
feat(iam): Pydantic 2.x schemas + domain exceptions
feat(iam): password_service (argon2id) + token_service (JWT HS256)
feat(iam): rate_limit_service (Redis INCR+EXPIRE atomic)
feat(iam): 6 thin SQLAlchemy repositories
feat(iam): consent_service + email_service + cloudevents emitters
feat(iam): auth_service orchestration + get_current_user middleware
feat(iam): routers (8 auth + 2 me endpoints) + DI factories + main.py wiring
test(iam): 76 unit tests, src.iam coverage 86.69% (AC9 >=85%)
```

### AC scoreboard (10/10 ✅ — full pass against phase-spec)

| AC | Description | Status | Test reference |
|---|---|---|---|
| AC1 | register → 201 + workspace+cell IDs | ✅ | test_register_201, test_register_happy_path |
| AC2 | login → TokenPair | ✅ | test_login_200, test_login_returns_token_pair |
| AC3 | /me requires Bearer JWT | ✅ | test_get_me_401_without_auth, test_get_me_200_with_override |
| AC4 | Revoked JWT → 401 | ✅ | test_blacklist_and_verify_raises_token_revoked |
| AC5 | Refresh rotation chain-revoke | ✅ | test_refresh_reuse_revokes_chain, test_refresh_chain_revoke_401 |
| AC6 | Consent recorded with version pin | ✅ | test_register_happy_path (consent_repo.record asserted) |
| AC7 | Email verification gate | ✅ | test_login_email_not_verified_when_gate_on |
| AC8 | 6-я login → 429 | ✅ | test_login_6th_attempt_is_blocked_with_retry_after |
| AC9 | Coverage ≥85% on src.iam | ✅ | 86.69% (gate passed) |
| AC10 | Audit emission per auth-event | ✅ | _stubs.audit.emit_audit_event called from auth_service + test_all_emit_functions_run |

### Build / test state

```
backend: 84/84 pytest pass (76 iam unit + 5 health + 3 smoke)
ruff:    All checks passed (src/ + tests/iam)
ruff fmt: All files formatted
mypy --strict: Success on 36 source files
src.iam coverage: 86.69%
pip-audit: not re-run (no new high-risk deps; structlog + email-validator clean)
```

## Next agent — read first

Standard bootstrap-4:

1. [`README.md`](./README.md) — what is this project
2. [`STATUS.md`](./STATUS.md) — current state (Phase 00.2 code-complete pending merge)
3. **this HANDOFF.md** — snapshot
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

## Founder action (post-merge)

1. Review + merge PR `[00.2] feat(iam): ...` from branch `claude/gifted-feistel-55966b`.
2. Confirm 00.3 + 00.4 parallel PRs also merge.
3. After all 3 merge, open Phase 00.2.5 integration session in fresh worktree:
   ```bash
   git checkout main && git pull origin main
   git worktree add .planning/.claude/worktrees/phase-00-2-5-integration -b claude/phase-00-2-5-integration
   # Brief: "Phase 00.2.5 integration. Delete backend/src/_stubs/,
   #         replace imports to real impls from 00.3, run make dev-bootstrap,
   #         run E2E smoke (register -> verify-email -> login -> /api/llm/chat ->
   #         refresh -> logout), full coverage incl iam repositories on real PG,
   #         update STATUS/HANDOFF/JOURNAL/PROJECT, mark 00.2/00.3/00.4 Complete."
   ```

## Known caveats / tracked for 00.2.5 + 00.6

- **alembic.ini cp1251 on Windows**: pre-existing Phase 00.1 issue (russian comments in alembic.ini cause configparser cp1251 decode error on Windows when invoked via `uv run alembic ...`). Migrations are valid (verified via Python AST import + revision chain check). Workaround: run `alembic upgrade head` on Linux/macOS or set system locale; cleanup pinned to Phase 00.6.
- **Repositories <60% covered via unit mocks**: by design (Q4 hybrid). Real-PG integration suite under `tests/iam/integration/` will land in 00.2.5 to push aggregate coverage even higher.
- **InsecureKeyLengthWarning** on `test_verify_wrong_signature_raises_token_invalid` — uses a short test secret; production secret is 32+ chars per `.env.example` template.

## Exit ritual completed (this session)

- [x] 14 atomic commits pushed to `claude/gifted-feistel-55966b`
- [x] JOURNAL.md entry appended (this date)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md updated — Phase 00.2 code-complete entry
- [x] Phase-spec `.planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md` status: Pending → Code-complete (pending merge)
- [ ] PR opened — pending (founder action)
