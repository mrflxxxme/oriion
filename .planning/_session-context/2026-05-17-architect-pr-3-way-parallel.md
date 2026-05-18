# Architect-PR + 3-way parallel execution plan — Wave 0 phases 00.2 / 00.3 / 00.4

> Authoritative in-repo copy of the founder's local plan
> `C:\Users\KUklonskiy\.claude\plans\start-phase-00-2-of-dreamy-truffle.md`
> (paths corrected: `backend/alembic/versions/` → `backend/migrations/versions/`).
> Read this when starting Phase 00.2 / 00.3 / 00.4 / 00.2.5 sessions.

## Context

Phase 00.1 (Repo & CI/CD) merged 2026-05-17 via PR #25. Founder wants to start Phase 00.2 (Custom JWT auth) and accelerate Wave 0 by running 00.2 / 00.3 / 00.4 in parallel where possible.

Discovered during the grill:
- **OQ-04 (РКН-уведомление) submitted** — dev work unblocked. Founder will confirm registry posting before prod-launch.
- **Phase-spec ↔ contract conflict on hashing**: spec mentions bcrypt; `contracts/iam/schema.sql` enforces `password_algo CHECK (... 'argon2id')`. **Contract wins per ADR-024** — argon2-cffi is already in deps (Phase 00.1 closed that debt).
- **Contract gap**: phase-spec references `iam.consents`, `iam.email_verification_tokens`, `iam.password_reset_tokens` — none present in contracts. Founder chose **Full-scope**, so contracts must be extended before 00.2 starts.
- **Hidden coupling**: 00.2 needs `multitenancy.workspaces/cells` (00.3 territory) for first-workspace provisioning at register, writes audit-events to `audit.audit_log` (00.3 schema), and 00.4 needs RLS context-setter + audit emission (00.3 territory). Pure 3-way parallel only works via contract-stub interfaces.
- **Phase-00.3 spec owns schema bootstrap** (CREATE SCHEMA iam/multitenancy/audit/llm_gateway/billing + extensions + `_shared` trigger function). For 3-way parallel to start cleanly, this bootstrap must move into the architect-PR so all 3 streams build on a stable foundation.

## Decisions resolved (this grill session)

| # | Decision | Choice |
|---|---|---|
| D1 | OQ-04 status | Submitted — dev unblocked |
| D2 | Parallel topology | 3-way (00.2 + 00.3 + 00.4) via contract-first stubs |
| D3 | Phase 00.2 scope | Full (8 endpoints, email-verification, password-reset, consent, audit, rate-limit, ≥85% coverage) |
| D4 | SMTP availability | None yet — console-output stub in dev (`REQUIRE_EMAIL_VERIFICATION=false`) |
| D5 | Orchestration | Architect-PR session does extension PR + exits; founder starts 3 new sessions |
| D6 | Branch names | `claude/phase-00-2-jwt-auth`, `claude/phase-00-3-db-rls`, `claude/phase-00-4-llm-gateway` |
| D7 | Architect-PR location | Architect-PR branch `claude/dazzling-satoshi-0a293d` |
| D8 | Integration | Separate Phase 00.2.5 integration session after 3 merges |
| D9 | `_shared` bootstrap location | In architect-PR (absorbs Phase 00.3's bootstrap step) |
| D10 | Hashing | argon2id only (contract authoritative; spec's bcrypt is stale) |
| D11 | TTL / rate-limits | Spec defaults: Access JWT 15 min HS256, Refresh 7 days opaque+SHA-256 hash, Rate-limit 5/15min per (ip,email) |
| D12 | Coverage gate | ≥85% for `backend/src/iam/` |

---

## Step 0 — Architect contract-extension PR (DONE in branch `claude/dazzling-satoshi-0a293d`)

Done in this branch. Highlights:
- Extended `contracts/iam/{schema.sql, api.yaml, events.yaml, README.md}` for `consents` / `email_verification_tokens` / `password_reset_tokens` + 4 endpoints + 4 events + 4 invariants.
- Created `backend/migrations/versions/_shared/0001_init.py` foundation migration (5 extensions, 12 schemas, `set_updated_at` trigger, `oriion_app` role).
- Extended `backend/alembic.ini` `version_locations` with 12 bounded-context subdirs (+ `.gitkeep` placeholders).
- Updated `.planning/STATUS.md`, `HANDOFF.md`, `PROJECT.md`, `JOURNAL.md`.
- Added architect-PR override banners to 00.2 / 00.3 / 00.4 phase-specs.

After founder merges this PR → spawn 3 worktrees per "Founder action" below.

---

## Stub interfaces (the integration contract between parallel streams)

Each parallel worktree implements its own scope plus the stub side of cross-cutting calls. Integration phase 00.2.5 replaces stubs with real impls.

### Stub 1 — `backend/src/_stubs/multitenancy.py` (owned by 00.2 worktree)

```python
# Stub for multitenancy.provision_initial_workspace — replaced by real impl from 00.3
from uuid import UUID, uuid5, NAMESPACE_OID
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class WorkspaceProvisionResult(BaseModel):
    workspace_id: UUID
    cell_id: UUID

async def provision_initial_workspace(user_id: UUID) -> WorkspaceProvisionResult:
    """Returns deterministic stub IDs derived from user_id. Logs WARNING."""
    workspace_id = uuid5(NAMESPACE_OID, f"workspace:{user_id}")
    cell_id = uuid5(NAMESPACE_OID, f"cell:{user_id}")
    logger.warning("STUB multitenancy.provision_initial_workspace — replace via 00.3 integration",
                   user_id=str(user_id), workspace_id=str(workspace_id), cell_id=str(cell_id))
    return WorkspaceProvisionResult(workspace_id=workspace_id, cell_id=cell_id)
```

### Stub 2 — `backend/src/_stubs/audit.py` (owned by 00.2 + 00.4 worktrees)

```python
# Stub for audit.audit_log emission — replaced by real impl from 00.3
from uuid import UUID
import structlog

logger = structlog.get_logger()

async def emit_audit_event(
    actor_type: str, actor_id: UUID, action: str,
    resource_type: str, resource_id: UUID | None = None,
    payload: dict | None = None, ip: str | None = None, user_agent: str | None = None,
) -> None:
    """Writes structured log via structlog. No DB write. Real impl in 00.3."""
    logger.bind(audit_event=True).info(
        "audit.stub", action=action, actor_id=str(actor_id),
        actor_type=actor_type, resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        payload=payload, ip=ip, user_agent=user_agent,
    )
```

### Stub 3 — `backend/src/_stubs/rls.py` (owned by 00.4 worktree)

```python
# Stub for set_tenant_context — no-op context manager. Real impl in 00.3.
from contextlib import asynccontextmanager
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def set_tenant_context(session: AsyncSession, cell_id: UUID, user_id: UUID):
    logger.warning("STUB set_tenant_context — RLS not enforced in this worktree",
                   cell_id=str(cell_id), user_id=str(user_id))
    yield session
```

**Real-impl locations** that 00.3 must produce (so 00.2.5 can swap):
- `backend/src/multitenancy/services/workspace_service.py::provision_initial_workspace`
- `backend/src/audit/services/audit_service.py::emit_audit_event`
- `backend/src/_shared/db/rls.py::set_tenant_context`

---

## Step 1a — Worktree 1: Phase 00.2 (Custom JWT auth)

Branch: `claude/phase-00-2-jwt-auth`. Owner agents: `backend-implementer` + `reviewer-security` (tier 4). Spec: `.planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md`.

### Critical files to create

- `backend/src/iam/{__init__.py, models.py, schemas.py, middleware.py, exceptions.py, events.py}`
- `backend/src/iam/routers/{auth.py, me.py}`
- `backend/src/iam/services/{auth_service.py, token_service.py, password_service.py, email_service.py, consent_service.py, rate_limit_service.py}`
- `backend/src/iam/repositories/{user_repository.py, session_repository.py, refresh_token_repository.py, consent_repository.py, email_verification_repository.py, password_reset_repository.py}`
- `backend/migrations/versions/iam/0001_users.py` through `0005_password_reset_tokens.py` (down_revision of `0001` = `_shared_0001_init`)
- `backend/tests/iam/{test_auth_service.py, test_token_service.py, test_password_service.py, test_rate_limit.py, test_auth_endpoint.py, test_refresh_rotation.py, test_email_verification.py, test_password_reset.py}`
- `backend/src/_stubs/{multitenancy.py, audit.py}` (stub interfaces — see above)

### Reuse from existing code

- `backend/src/_shared/db/session.py` — async SQLAlchemy session factory (Phase 00.1)
- `backend/src/_shared/config.py` — pydantic-settings env loader (Phase 00.1)
- `backend/src/_shared/logging.py` — structlog setup (Phase 00.1)
- `backend/tests/conftest.py` — pytest fixtures (db_session, client) (Phase 00.1)

> If any of these don't yet exist in `backend/src/_shared/`, create them as part of 00.2 (they're foundational utilities all 3 worktrees expect). Coordinate via stub/wrapper if collision risk.

### Implementation defaults (locked per D11)

- JWT alg: HS256; secret env: `JWT_SECRET_ACCESS_V1` (rotated quarterly post-launch)
- Access TTL: 900s (15 min); Refresh TTL: 604800s (7 days)
- Refresh token: opaque random 256-bit (`secrets.token_urlsafe(32)`); stored as SHA-256 hex hash
- Refresh rotation: per OWASP chain-revoke (reuse of used token → revoke entire `rotation_chain_id`)
- Argon2id params: memory=64MB, iterations=3, parallelism=4 (argon2-cffi defaults — confirm against ADR-014)
- Rate-limit: Redis `INCR + EXPIRE 900` keyed on `ratelimit:{ip}:{email}`, threshold 5
- Cookies: HttpOnly, Secure, SameSite=Lax (set via Caddy; FastAPI sets cookie attrs)
- Email service: `EmailSender` Protocol interface + `ConsoleEmailSender` impl (dev) + `OutboxEmailSender` (writes `iam.email_outbox` table for inspection); Yandex SMTP impl deferred to Wave 1
- `REQUIRE_EMAIL_VERIFICATION` env flag (default `false` in dev `.env.example`, `true` in prod)
- Coverage gate: `pytest --cov=backend/src/iam --cov-fail-under=85`

### Acceptance Criteria (from phase-spec AC1–AC10)

All 10 AC inherited from `.planning/roadmap/wave-0-foundation/phases/00.2-custom-jwt-auth.md` §Acceptance Criteria. Modifications for dev-mode stub:
- AC7 (email verification mandatory) → enforced only when `REQUIRE_EMAIL_VERIFICATION=true`; in dev, test uses env-flip to verify gate
- AC10 (audit emission) → tests assert `audit.stub` log records (real DB persistence verified in 00.2.5 integration)

---

## Step 1b — Worktree 2: Phase 00.3 (DB + RLS + cell schema)

Branch: `claude/phase-00-3-db-rls`. Owner agents: `backend-implementer` + `architect`. Spec: `.planning/roadmap/wave-0-foundation/phases/00.3-db-rls-multitenancy.md`.

**Scope reduction from spec**: schema bootstrap + extensions + `_shared` trigger are **done in architect-PR**. Phase 00.3 starts directly at multitenancy DDL. The architect-PR override banner at the top of the spec is authoritative.

### Critical files to create

- `backend/migrations/versions/multitenancy/0001_workspaces_cells.py` (down_revision = `_shared_0001_init`)
- `backend/migrations/versions/multitenancy/0002_rls_policies.py`
- `backend/migrations/versions/audit/0001_audit_log_partitioned.py`
- `backend/src/multitenancy/{models, schemas, routers, services, repositories}.py`
- `backend/src/audit/services/audit_service.py` — `emit_audit_event` real impl
- `backend/src/_shared/db/rls.py` — `set_tenant_context` real impl
- `backend/tests/multitenancy/test_rls_isolation.py` — cross-cell SELECT returns 0 rows
- `backend/tests/audit/test_audit_log_append_only.py`

### Acceptance Criteria (from phase-spec)

RLS isolation 100% verified (cross-cell SELECT returns 0 rows); cell-provisioning < 30s; audit_log partitioned by month, append-only via trigger.

---

## Step 1c — Worktree 3: Phase 00.4 (LLM gateway + MCP infra)

Branch: `claude/phase-00-4-llm-gateway`. Owner agents: `backend-implementer` + `mcp-builder` (spawn per phase). Spec: `.planning/roadmap/wave-0-foundation/phases/00.4-llm-gateway.md`.

**Stub dependencies from 00.3**: `set_tenant_context` (via `backend/src/_stubs/rls.py`), `emit_audit_event` (via `backend/src/_stubs/audit.py`). 00.4 uses inline SKELETON `billing.credit_transactions` migration per spec §billing.credit_transactions.

### Critical files to create

- `backend/src/llm_gateway/providers/{base.py, deepseek.py, yandex_gpt.py, gigachat.py}`
- `backend/src/llm_gateway/{router.py, services/router_service.py, services/cost_service.py, services/byok_service.py}`
- `backend/src/llm_gateway/routers/{chat.py, embeddings.py, providers.py, byok.py}`
- `backend/migrations/versions/llm_gateway/0001_byok_keys_provider_config_usage_log.py` (down_revision = `_shared_0001_init`)
- `backend/migrations/versions/billing/0001_credit_transactions_skeleton.py` (Wave 0 SKELETON per spec)
- `backend/src/mcp/{client.py, connection_service.py}` (Wave 0 client only — no production servers)
- `backend/tests/llm_gateway/{test_provider_routing.py, test_failover.py, test_cost_ledger.py, test_byok.py}`
- Optional: live integration tests gated by `pytest -m live` (skipped if no `TBD_DEEPSEEK_API_KEY` / etc.)

### Acceptance Criteria (from phase-spec)

p95 latency < 2.5s for DeepSeek chat (non-streaming, requires `TBD_DEEPSEEK_API_KEY` — else skip live tests); failover detection ≤ 5s; cost ledger 100% accuracy (`sum(credit_transactions) == sum(llm_usage_log)`).

---

## Step 2 — Phase 00.2.5 integration session

Spawned after all 3 PRs merged. New worktree `claude/phase-00-2-5-integration`.

### Tasks

1. Delete `backend/src/_stubs/` directory and replace imports with real services from 00.3:
   - `from src._stubs.multitenancy import provision_initial_workspace` → `from src.multitenancy.services.workspace_service import provision_initial_workspace`
   - `from src._stubs.audit import emit_audit_event` → `from src.audit.services.audit_service import emit_audit_event`
   - `from src._stubs.rls import set_tenant_context` → `from src._shared.db.rls import set_tenant_context`
2. Run `make dev-bootstrap`, verify all schemas + RLS + extensions present.
3. E2E smoke test:
   - register → verify-email (capture token from outbox) → login → call /api/llm/chat/completions with stub provider → refresh → logout → confirm access-token blacklisted
4. Run full test suite under real (non-stub) wiring — must pass with ≥85% coverage on `iam/`.
5. Update `STATUS.md`, `HANDOFF.md`, `JOURNAL.md`, `PROJECT.md`. Mark Wave 0 phases 00.2/00.3/00.4 ✅ Complete.
6. Open integration PR.

---

## Founder action — how to start the 3 parallel sessions

After architect-PR merges:

```bash
# From repo root, on freshly-pulled main
git checkout main && git pull origin main

# Worktree 1 — Phase 00.2
git worktree add .planning/.claude/worktrees/phase-00-2-jwt-auth -b claude/phase-00-2-jwt-auth
# Open Claude Code session in that dir, say:
#   "Start Phase 00.2 per .planning/_session-context/2026-05-17-architect-pr-3-way-parallel.md §Step 1a"

# Worktree 2 — Phase 00.3
git worktree add .planning/.claude/worktrees/phase-00-3-db-rls -b claude/phase-00-3-db-rls
# Open Claude Code session, say:
#   "Start Phase 00.3 per .planning/_session-context/... §Step 1b"

# Worktree 3 — Phase 00.4
git worktree add .planning/.claude/worktrees/phase-00-4-llm-gateway -b claude/phase-00-4-llm-gateway
# Open Claude Code session, say:
#   "Start Phase 00.4 per .planning/_session-context/... §Step 1c"
```

Each session bootstraps per `agent-handbook/00-START-HERE.md` (read README + STATUS + HANDOFF + handbook), reads its phase-spec + this in-repo plan, and executes.

---

## Verification (end-to-end)

After all 3 phase PRs merge + Phase 00.2.5 integration PR opens:

```bash
# In integration worktree
make dev-bootstrap                             # All services up
make test                                      # Full suite green, coverage ≥85% on iam/
pytest backend/tests/integration/test_register_to_llm_flow.py -v  # E2E smoke

# Manual sanity (optional)
curl -X POST localhost:8000/api/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"smoke@oriion.dev","password":"Test123!","consent_pdn":true}'
# Expect 201 with {user_id, workspace_id, cell_id}

# Verify schemas present
docker compose exec postgres psql -U oriion -d oriion -c "\dn"
# Expect: _shared, iam, multitenancy, audit, llm_gateway, billing, etc.

# Verify RLS enabled
docker compose exec postgres psql -U oriion -d oriion -c \
  "SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE schemaname IN ('multitenancy','billing') AND rowsecurity=true;"
```

---

## Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Contract drift between 00.2 stubs and 00.3 real impls | Medium | Stubs defined inline in this plan with explicit signatures; integration phase has explicit replacement task list |
| 00.3 RLS policies break 00.2 endpoints after merge | Medium | Integration smoke-test catches; rollback via single PR revert if needed |
| Architect-PR _shared scope conflicts with 00.3 phase-spec | Low (resolved) | Phase-00.3 spec carries architect-PR override banner instructing the 00.3 agent to skip bootstrap. |
| OQ-04 RKN posting denied → prod-launch blocked | Low | Dev work proceeds on dev DB only; no real PDn processed until prod merge gated by RKN confirmation |
| SMTP stub leaves email-verification untested in prod-mode | Medium | `REQUIRE_EMAIL_VERIFICATION=true` test exists with mocked SMTP; full live test deferred to Wave 1 SMTP integration phase |
| 3 parallel sessions confuse founder review | Medium | PR titles tagged `[00.2]`, `[00.3]`, `[00.4]`; each PR description references this plan section |
| 00.4 live tests fail without API keys | Low | Live tests gated by `pytest -m live`; CI runs only unit + integration with mocked providers |

---

## Out-of-scope (deferred)

- OAuth (Yandex ID / VK ID) — Wave 1
- 2FA TOTP — Wave 1
- HIBP password breach check — Wave 1
- Yandex 360 SMTP integration — Wave 1 (when founder provisions credentials)
- pen-test pass — before Wave 2 public-launch
- JWT secret rotation tooling — Wave 1+ (manual env-var rotation in Wave 0)
