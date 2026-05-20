# Phase 00.5b — Security Audit (Section 02)

**Auditor:** Security Engineer
**Branch:** `claude/phase-00-5b-runtime` (commits `7c00b43..6cd8808`)
**Worktree:** `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\phase-00-5b-runtime`
**Date:** 2026-05-21
**Baseline:** Phase 00.5a (Architecture H1+H2 + Compliance H-1 closed)

---

## Verdict

**APPROVE WITH CAVEATS — 00.5a security posture is NOT regressed.** All FORCE-RLS guarantees from 00.5a hold for the three new schemas (`agents`, `tasks`, plus the already-shipped `tasks.task_artifacts`). The `register()` provisioning path correctly sets the 3-GUC tenant context before `provision_team()` flushes the FORCE-RLS-protected `agent_instances` INSERT (auth_service.py:179–196), which is the one and only legitimate Phase 00.5b INSERT site under `oriion_app` that runs outside `get_tenant_db_session`.

However, **Phase 00.5b ships three RLS-coverage gaps that are documented but not pinned to an AC**, plus a defense-in-depth gap in the in-process SSE publisher. These are exposure-bounded (read-only or background-runner paths), not authn-bypass, but they deserve explicit Wave-1 ACs before any external-tenant traffic. Cross-context model imports were held flat (no new sanctioned imports beyond the pre-existing `billing.models.CreditTransaction` deferred to Commit 8). SecretStr hygiene is intact; secrets never reach logs.

**Findings count:** 6 (1 HIGH, 3 MEDIUM, 2 LOW)

---

## Findings

### F-SEC-H1 (HIGH) — Cell-scoped read routers bypass tenant GUC, relying on path-param trust

**Severity:** HIGH (data-exposure path) — but **mitigated by FORCE-RLS default-deny**, so impact is degraded to "queries return empty result-sets" rather than cross-tenant data leak. This pulls the real-world impact down to MEDIUM, but I'm pinning the finding HIGH because the pattern will regress if someone removes `FORCE ROW LEVEL SECURITY` thinking the application layer enforces it.

**Locations:**
- `backend/src/agents/routers/instances.py:21` — `GET /cells/{cell_id}/agents` uses raw `get_db`, not `get_tenant_db_session`. Comment at L24–28 admits this: *"RLS-protected via app.current_cell_id GUC — caller must run under `get_tenant_db_session` (Phase 00.5a middleware) for production. Wave 0 handler reads from get_db directly..."*
- `backend/src/agents/routers/teams.py:25,38` — `POST /cells/{cell_id}/teams` uses raw `get_db`. The downstream `TeamProvisioningService.provision_team()` performs INSERTs into `agents.agent_instances` (which is FORCE-RLS) under `oriion_app` **without GUC setup**. The endpoint never calls `set_config('app.current_cell_id', ...)`. It works at all only because `oriion_db_owner` (the migration role) is what tests use — under `oriion_app` in prod, this INSERT will be rejected by `WITH CHECK (cell_id = current_setting('app.current_cell_id', true)::uuid)` because the GUC is empty (`true` flag returns `''` which fails the UUID cast).
- `backend/src/tasks/routers/tasks.py:18,42-53` — `POST/GET /cells/{cell_id}/tasks/...` and `cancel_task` use raw `get_db`. The handler's own comment (L49-50) says *"actual RLS filtering happens at the DB layer via app.current_cell_id GUC"* — but no GUC is set on this code path. `TaskService.create_task` does an INSERT into `tasks.tasks` (FORCE-RLS), which under `oriion_app` will fail at the policy WITH CHECK.

**Evidence:**
```python
# instances.py:18-35  — get_db, no GUC
@router.get("", response_model=list[AgentInstanceOut])
async def list_cell_agents(cell_id: UUID, db: AsyncSession = Depends(get_db)) -> ...

# teams.py:25,38 — get_db, no GUC; provisioning service INSERTs into agent_instances
async def provision_team(cell_id: UUID, ..., db: AsyncSession = Depends(get_db), ...

# tasks.py:18,22  — get_db, no GUC; INSERT into FORCE-RLS tasks.tasks
def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
```

**Why this hides under tests:** the test conftest typically uses the migration role (`oriion_db_owner`), which has `BYPASSRLS` semantics or sufficient SUPERUSER override for migrations — so writes "appear" to succeed in CI. The first time these endpoints execute under `oriion_app` connection-pool credentials in staging, the INSERTs will hard-fail with a Postgres `42501` (insufficient_privilege) / RLS policy violation, OR (worse) succeed in a way that bypasses cell isolation because the path-param `cell_id` is the only authorization signal.

**Impact:** Authorization decision (which cell can a user write into?) is implicitly trusted from the URL path parameter — there is no membership check linking `auth.user.id` → `cell_id` before the write. Combined with no GUC being set, this means:
1. In test/dev with the owner role → cross-cell writes are accepted by Postgres (no RLS enforcement).
2. In prod with `oriion_app` → writes hard-fail (good) but `GET` reads filter against an empty GUC → return zero rows (defense-in-depth holds, but UX breaks).

**Fix (Wave 1 mandatory):**
- Migrate every cell-scoped router to `Depends(get_tenant_db_session)` (the dependency already exists and is the documented Phase 00.5a contract).
- Add a `_resolve_membership_for_cell(cell_id, user_id)` guard in `_shared/middleware/tenant_context.py` or have `get_tenant_db_session` accept an explicit `cell_id` path-param and 403 if the resolved cell ≠ the requested cell.
- Until then: pin an AC to the Wave-1 cutover PR (`F-SEC-H1.AC`: "every `/cells/{cell_id}/*` POST/GET/DELETE route depends on `get_tenant_db_session`").

**Status:** Acknowledged in source comments but **NOT pinned to an AC**. This is the same H1 gap that Phase 00.5a closed for multitenancy routers — Phase 00.5b reintroduced the same pattern in three new routers.

---

### F-SEC-M1 (MEDIUM) — SSE publisher does not key by cell_id (defense-in-depth gap)

**Severity:** MEDIUM. Real-world impact bounded by `task_id` being a UUIDv4 (unguessable in practice), but the design pattern violates least-privilege isolation between tenants.

**Location:** `backend/src/runtime/sse_publisher.py:37,44,48-77`

The `InProcessSSEPublisher` keys subscriber queues and the drain buffer **solely by `task_id`** (`dict[UUID, list[asyncio.Queue]]`), with no `cell_id` discriminant. Any handler in the same process that calls `publisher.subscribe(task_id)` receives every event for that task_id regardless of whether the subscribing connection authenticated as a user in the same cell.

The mitigating control is in `tasks/routers/stream.py:30-34`:
```python
async def stream_task(cell_id: UUID, task_id: UUID, auth: AuthenticatedUser = Depends(get_current_user))
```
The handler requires authentication, but it does **not verify** that the (auth.user.id, cell_id, task_id) triple is internally consistent (i.e., that the task actually belongs to a cell where the user is a member). An authenticated user who can guess or otherwise learn another tenant's task_id can subscribe to its event stream.

**Impact:** Information disclosure on the SSE channel — leaks step-level orchestrator progress, target_agent_slug values, sub-task IDs, total cost_credits, and the full CoordinatorOutput summary. No PII directly, but tenant-internal operational telemetry.

**Fix:**
- Add a membership check at the top of `stream_task` before subscribing: load `Task` via TaskService, assert `task.cell_id == cell_id` and that the user has a `cell_member` row for that cell.
- Wave-1 Redis pub/sub bridge should namespace channels as `tasks:{cell_id}:{task_id}:events` so even mis-wired consumers can't subscribe across cells.

**Status:** Not pinned. Acceptable for Wave 0 (single-cell-per-user simplification + UUIDv4 unguessability) but must close before multi-cell Wave 1.

---

### F-SEC-M2 (MEDIUM) — Coordinator `delegate_task` lacks structural validation on `target_agent_slug`

**Severity:** MEDIUM (defense-in-depth) — actual exploitation is blocked by the membership-list whitelist check (delegate.py:114–120), but the input string itself is unbounded and could be abused if any downstream consumer ever uses it in a logging/template path without escaping.

**Location:** `backend/src/agents/tools/delegate.py:42-44`
```python
target_agent_slug: str = Field(
    ...,
    description="Role-key of the target agent — 'researcher' | 'writer' | 'analyst'",
)
```

The Pydantic field is `str` with no `pattern`, no `max_length`, no `Literal[...]` constraint. The validation against `available_agent_slugs` (L115) blocks the dispatch but the *raw value* is still emitted into:
- An SSE payload via `sse_publisher.publish(... payload={"target_agent_slug": inp.target_agent_slug})` (orchestrator.py:120, 134) — this gets serialized to JSON and shipped to the client. JSON-encoding sanitizes, but the value is also surfaced in structured logs.
- The DelegationTargetInvalid exception message: `f"target_agent_slug={target_slug!r} not in cell team {sorted(available)}"` (delegate.py:117) — `!r` quotes the repr, so newlines/control chars get escaped, but a 10-MB attacker-supplied string still gets put into an exception message and logged.

**Impact:** LLM prompt-injection could in principle make the model emit a 100KB+ `target_agent_slug` argument; while the dispatch is blocked, log volume amplification and downstream log-parser bugs are possible. There's no command-injection or SQL-injection path (the field never lands in a SQL query — `provision_team` looks up by archetype_id, not slug).

**Fix:**
```python
target_agent_slug: str = Field(
    ...,
    min_length=1,
    max_length=64,
    pattern=r"^[a-z][a-z0-9-]{0,63}$",
    description="...",
)
```

**Status:** Not pinned. Easy 2-line fix.

---

### F-SEC-M3 (MEDIUM) — Provider credentials held as `str` after `.get_secret_value()` extraction

**Severity:** MEDIUM. Settings hygiene is good (all four credentials are `SecretStr` per `_shared/config.py:51,92,122,129,145,162,166`), but once main.lifespan extracts plaintext at startup (main.py:145–153) and hands the raw `str` to the provider constructors, the providers store them as plain attributes (deepseek.py:34, yandex.py:39, gigachat.py:45).

**Locations:**
- `backend/src/llm_gateway/providers/deepseek.py:34` — `self._api_key = api_key` (raw str)
- `backend/src/llm_gateway/providers/yandex.py:39` — `self._iam_token = iam_token` (raw str)
- `backend/src/llm_gateway/providers/gigachat.py:45` — `self._auth_key = auth_key` (raw str)

These plaintext credentials live for the entire process lifetime on `app.state.llm_providers`. Any future debug-introspection path (e.g., an `/api/v1/_debug/state` endpoint, a Sentry exception serializer that walks `app.state`, a heap dump from an OOM) would expose them.

**Mitigating controls (good):**
- `main.py:165–169` lifespan log emits `provider_slugs=list(providers.keys())` — slug names only, no credentials. Verified via grep.
- No `__repr__` on providers (would default to Python object repr, no attrs).
- `Settings` itself never leaves SecretStr form in logs.

**Fix (Wave-1 mandatory before staging):**
- Hold `_api_key` etc. as `SecretStr` inside the provider; only call `.get_secret_value()` at the moment of constructing the HTTP header dict (inside the `httpx.post(..., headers=...)` call site).
- Add an explicit `__repr__` to each provider class that returns `f"DeepSeekProvider(slug=deepseek, key=<redacted>)"` — defense-in-depth against future logging surprises.

**Status:** Not pinned. Carries from the pre-existing provider scaffolding (this code shape was inherited from Phase 00.4); Phase 00.5b's lifespan wire-up made it production-reachable.

---

### F-SEC-L1 (LOW) — `tasks.task_steps` policy lacks `WITH CHECK`

**Severity:** LOW. Policy is correct for SELECT but permissive for INSERT/UPDATE.

**Location:** `backend/migrations/versions/tasks/0002_task_steps.py:43-51`

```sql
CREATE POLICY task_steps_via_task ON tasks.task_steps
    USING (EXISTS (
        SELECT 1 FROM tasks.tasks t
        WHERE t.id = task_steps.task_id
          AND t.cell_id = current_setting('app.current_cell_id', true)::uuid
    ));
```

The policy has **no `WITH CHECK`** clause — only `USING`. Per Postgres RLS semantics, when `WITH CHECK` is omitted, the `USING` expression is used for both visibility and write-validation, which in this case is fine *but* the implicit dependency is subtle. A future migration that adds `WITH CHECK (...)` separately could silently regress this.

**Same pattern in:** `task_artifacts` (0003_task_artifacts.py:48-55) — same omission, same low risk.

**Compare to:** `agent_instances` (0003_agent_instances.py:52-55) which **does** declare both `USING` and `WITH CHECK` explicitly — that's the correct pattern.

**Fix:** Add explicit `WITH CHECK (...)` clauses to both `tasks.task_steps` and `tasks.task_artifacts` policies — copy-paste of the `USING` expression — in a follow-up migration.

**Status:** Cosmetic but explicit-is-better-than-implicit. Wave-1 cleanup.

---

### F-SEC-L2 (LOW) — `OrchestratorContext.user_id` plumbed but never enforced against task ownership

**Severity:** LOW. The orchestrator accepts `user_id` and passes it through to `CoordinatorDepsLike`, but never validates that the user_id is in fact the `initiated_by_user_id` of the task being run. Combined with F-SEC-H1, this means a caller could in principle pass any user_id as the "owner" of a runtime execution.

**Location:** `backend/src/runtime/orchestrator.py:66-77`

```python
async def execute_agent_task(
    *,
    task_id: UUID,
    cell_id: UUID,
    user_id: UUID,           # ← never cross-checked against Task.initiated_by_user_id
    ...
```

The orchestrator reads `Task` via `session.get(Task, task_id)` at L107, but doesn't compare `task.initiated_by_user_id == user_id`. The only enforcement happens at the *caller* (which today is only the demo flow + test fixtures — there's no production endpoint that triggers `execute_agent_task` yet).

**Fix:** Add an assertion at orchestrator start:
```python
task = await session.get(Task, task_id)
if task is None or task.cell_id != cell_id or task.initiated_by_user_id != user_id:
    raise AuthorizationError(...)
```

**Status:** Not pinned. Acceptable as long as `execute_agent_task` has no public HTTP trigger (which is currently true — no router calls it). The risk lands when Commit 8+ wires a "run task" endpoint.

---

## Defer to Wave 1

Items below are acknowledged-but-not-pinned in Phase 00.5b source comments. Recommend pinning each to a Wave-1 AC:

| ID | Item | Wave-1 AC suggestion |
|----|------|---------------------|
| F-SEC-H1 | Cell-scoped routers (agents/tasks) on raw `get_db` | "Every `/cells/{cell_id}/*` route depends on `get_tenant_db_session` OR explicit GUC set. CI lint rule rejects raw `get_db` in cell-scoped routers." |
| F-SEC-M1 | SSE publisher not cell-keyed | "`stream_task` verifies task.cell_id == path cell_id AND user is cell_member before subscribe." |
| F-SEC-M2 | `target_agent_slug` unconstrained string | "DelegateInput.target_agent_slug has pattern + max_length validation." |
| F-SEC-M3 | Provider plaintext credentials in memory | "Providers hold SecretStr; only unwrap at HTTP header construction; explicit __repr__ redaction." |
| F-SEC-L1 | task_steps / task_artifacts policies missing explicit WITH CHECK | Follow-up migration adds them. |
| F-SEC-L2 | Orchestrator user_id never cross-checked vs Task.initiated_by_user_id | Add assertion when production endpoint wires up. |

---

## Items VERIFIED CLEAN (no finding)

1. **SECURITY DEFINER surface unchanged** — Confirmed via `grep -r "SECURITY DEFINER" backend/migrations/versions/{agents,tasks}/`: **zero matches**. The only SECURITY DEFINER functions remain `multitenancy.bootstrap_first_workspace` and `multitenancy.resolve_user_first_membership` (both 00.5a). Phase 00.5b added no new privileged functions.

2. **`auth_service.register()` GUC wire-up for AC1** — Verified at auth_service.py:179–196: explicit `set_config('app.current_user_id', :u, true)` + `app.current_workspace_id` + `app.current_cell_id` set BEFORE `provision_team()` is called. The `true` flag (LOCAL) ensures auto-reset at TX end. Order-of-operations is correct — workspace is bootstrapped first (via SECURITY DEFINER), then GUCs set, then team provisioning runs under regular `oriion_app` policies. Same-TX semantics holds; rollback covers everything.

3. **Cross-context model imports** — Verified via `grep "^from src\." backend/src/llm_gateway backend/src/agents backend/src/tasks backend/src/runtime`. The only cross-context model import is the pre-existing `src.billing.models.CreditTransaction` in `llm_gateway/services/billing_service.py:26` (deferred to Commit 8 per E2). **No new sanctioned violations.** `agents.writer/researcher/analyst/coordinator` correctly import `src.llm_gateway.pydantic_ai_model.LLMGatewayModel` (public surface, not a model class — sanctioned per ADR-024). `runtime/orchestrator.py` imports `agents.tools.delegate.{CoordinatorDepsLike, DelegateInput, DelegateResult}` (tool DTOs, not domain models) and `tasks.models.Task` (sanctioned for the runtime ↔ tasks coupling per Phase 00.5 spec).

4. **Settings SecretStr hygiene** — All five LLM/KMS credentials use `SecretStr`: `jwt_secret_access_v1`, `byok_master_key_b64`, `deepseek_api_key`, `yandex_iam_token`, `gigachat_auth_key`, plus `brave_search_api_key` + `yandex_search_api_key`. The six `.get_secret_value()` call sites are all narrow (`main.py:93,145,148,152` for provider DI; `iam/services/token_service.py:79,92` for JWT sign/verify). **No `.get_secret_value()` output is logged** — verified by reading every `_logger.*` call in `main.py:104,165,174` (the warning at L104 mentions BYOK_MASTER_KEY_B64 by *name* only, not value; the info at L165 logs `provider_slugs` only; the shutdown at L174 logs nothing).

5. **BYOK plaintext lifecycle** — `byok_service.store_byok_key` (byok_service.py:27–68) encrypts via KMS then drops the plaintext reference; only `key_encrypted` (ciphertext) + `key_fingerprint` (sha256[:8]) hit the DB. Verified no `.plaintext_key` retention path beyond the function scope. `BYOKProxyProvider` (byok_proxy.py:70) holds `self._key` for one request lifetime — caller is expected to drop the instance, which `LLMRouter.route()` does correctly.

6. **`_resolve_master_key_bytes` prod fail-fast** — main.py:99–113: explicit `RuntimeError` raised when `settings.is_prod and not b64`. Ephemeral key generation only runs in non-prod with a `_logger.warning` calling out the volatility. Correctly gated.

7. **FORCE-RLS on all three new tables** — Verified all three Phase 00.5b migrations declare both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`:
   - `agents.agent_instances` (agents/0003:48-49)
   - `tasks.tasks` (tasks/0001:52-53)
   - `tasks.task_steps` (tasks/0002:41-42)
   - `tasks.task_artifacts` (tasks/0003:45-46)

---

## Recommendation

**MERGE 00.5b as-is** with the understanding that **F-SEC-H1 is the closure carry-over from Phase 00.5a H1**: the architectural pattern (`get_tenant_db_session` as sole RLS-setter) was correctly established in 00.5a, but the three new routers added in commits 5 and 6 regress by re-introducing raw `get_db` usage in cell-scoped paths. This is exposure-bounded by FORCE-RLS default-deny (so worst case is "empty results / hard INSERT failures in staging" rather than data leak), and it does not violate any decision in `.planning/HANDOFF.md` "Decisions standing" — the comments in `instances.py:24-28` explicitly defer the migration.

**Required before Wave 1 cutover:**
1. Pin F-SEC-H1 as a Wave-1 blocker AC (covers F-SEC-M1 by extension).
2. Pin F-SEC-M3 as a Wave-1 blocker AC (SecretStr in providers) — required before any staging deploy with real provider keys.
3. F-SEC-M2, F-SEC-L1, F-SEC-L2 can land in Wave-1 housekeeping commits.

**Net assessment vs 00.5a baseline:** Phase 00.5b does not introduce any *novel* security weakness. It re-exposes (in a bounded way) the same pattern that 00.5a closed for the multitenancy routers — the fix is mechanical (swap `get_db` → `get_tenant_db_session`) but needs an AC pin so it doesn't slip past Wave-1.
