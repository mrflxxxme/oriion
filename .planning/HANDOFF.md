# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-20 (Phase 00.5b mid-session checkpoint — Commits 2-3 landed)
- Session: `phase-00-5b-runtime` (worktree branch `claude/phase-00-5b-runtime`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation)
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (merged 2026-05-17 via PR #25)
- **Architect-PR (pre-00.2)**: ✅ Complete (merged 2026-05-17 via PR #27)
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (merged 2026-05-18 via PR #28)
- **Phase 00.3 + Phase 00.4**: ✅ Complete (merged 2026-05-19 via PR #30)
- **Phase 00.2.5 (integration)**: ✅ Complete (merged 2026-05-19 via PR #32)
- **Pre-Phase-05 audit + nav cleanup**: ✅ Complete (merged 2026-05-19 via PR #33)
- **Phase 00.5a (RLS foundation)**: ✅ Complete (merged 2026-05-20 via PR #34, merge-commit `0360955`)
- **Phase 00.5b (Pydantic-AI runtime + router wiring + demo)**: 🔄 **In progress — Commits 2-3 of 8 landed on branch `claude/phase-00-5b-runtime`**. Commits 4-8 + MANDATORY 5-agent audit swarm + Exit-ritual-Phase-Complete flip + PR are the next session's deliverables.

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## What just happened (this session — Phase 00.5b Commits 2-3)

Per Phase 00.5b plan `C:\Users\KUklonskiy\.claude\plans\crispy-crunching-sunset.md` Commits 2-3 (out of 8 planned + audit + Exit ritual). Founder brief had ratified all grill decisions from Phase 00.5a — no re-grilling required.

This session shipped **2 atomic commits** off post-merge main = origin/main HEAD `0360955`:

### Commit 2 — `7c00b43` — feat(main,llm_gateway): wire multitenancy+LLM routers + lifespan provider DI

5 files, 452 insertions / 32 deletions.

| File | Status | Purpose |
|---|---|---|
| `backend/src/main.py` | OVERHAULED | Include multitenancy {workspaces, cells, workspace_cells} + llm_gateway {chat, embeddings, byok, providers, usage} routers under `/api/v1`; add exception handlers for `MultitenancyError` + `LLMGatewayException` + `MCPError` mirroring `IamError` problem+json envelope (`Retry-After` for `ToolRateLimitExceeded`); `lifespan` provider DI building DeepSeek + YandexGPT + GigaChat + per-slug `ProviderCircuit` + `LLMRouter` (chain `(deepseek, yandexgpt, gigachat)` per ADR-018) + KMS chosen via `settings.kms_backend`. Empty `BYOK_MASTER_KEY_B64` in dev/test → ephemeral key + loud warning; in prod → fail-fast `RuntimeError`. mcp routers intentionally NOT included (Wave 0 framework-only per ADR-013). |
| `backend/src/llm_gateway/deps.py` | NEW | `get_llm_router(request)`, `get_kms_provider(request)`, `get_byok_service()` factories pulling from `request.app.state`; 503 fail-loud when lifespan didn't run AND no `dependency_overrides`. |
| `backend/src/_shared/config.py` | MODIFIED | Promote 4 provider credentials to `Settings` (closes audit M3): `deepseek_api_key`, `yandex_iam_token`, `yandex_catalog_id`, `gigachat_auth_key`. BYOK + KMS fields already promoted in pre-Phase-00.5 work. |
| `backend/tests/integration/test_main_app_routes.py` | NEW | F-P5-5 mount-smoke — parametrised over 13 expected `(path, method)` pairs + aggregate gap-listing + `/health` probe. Static `app.routes` introspection — no HTTP — default filter. |
| `backend/tests/integration/test_e2e_auth_flow.py` | MODIFIED | Delete stale `test_llm_chat_endpoint_is_not_yet_wired` negative canary; archaeology comment kept. |

Verification:
- `python -c 'from src.main import app'` → 32 routes mounted (21 under `/api/v1`)
- `uv run pytest tests/integration/test_main_app_routes.py -v` → 15/15 pass
- `uv run pytest tests -q -m 'not integration'` → 386 pass, 23 deselected
- `uv run ruff check src tests` + `ruff format --check src tests` → clean

### Commit 3 — `e0aaba3` — ci,docs: per-module gate for billing + router-test convention

2 files, 35 insertions / 5 deletions.

| File | Status | Purpose |
|---|---|---|
| `.github/workflows/ci-backend.yml` | MODIFIED | Per-module ≥85% loop extended with `billing` gate (`tests/llm_gateway --cov=src/billing` — sanctioned cross-context import landing in Commit 8 ADR-024 amendment; current 100%). `_shared/db` + `_shared/middleware` unit gates DEFERRED to Commits 5-6 (integration coverage already exists via test_e2e_auth_flow.py under `oriion_app` canary). `agents`/`tasks`/`runtime` gates DEFERRED to their landing commits (don't exist yet). |
| `.planning/_meta/conventions.md` | MODIFIED | F-P5-5 ratified two-layer router-test convention documented: (a) mini-app pattern `tests/<context>/unit/test_routers.py` (throw-away `FastAPI()` + local handlers + ASGITransport) for handler logic; (b) main-app mount-smoke `tests/integration/test_main_app_routes.py` for "router dropped from main.include_router(...)" regressions. When-to-extend rule spelled out. |

## Decisions standing (verbatim from Phase 00.5a `/grill-me` 2026-05-20 — NOT re-grilled)

| Topic | Decision |
|---|---|
| **T1 — RLS Option** | ✅ Shipped 00.5a — SECURITY DEFINER `multitenancy.bootstrap_first_workspace(...)` SQL function |
| **T2 — Cut-list** | MUST-LAND `F-P5-1/2/4(DS+Y+GC chat_stream)/5/6`; SLIP-CANDIDATES `F-P5-3 + GigaChat-OAuth`; SKIP `M2/cost-relax/frontend` |
| **T3 — Mock pattern** | Custom stub at `LLMGatewayModel` level, `(role_key, scenario_id)` tuple keying — NOT pydantic_ai's `TestModel` |
| **T4 — Demo shape** | Hybrid (b) — CI canned-data flow + `scripts/demo_market_brief.py` runs Phase 00.6 staging |
| **T5 — Prompts** | First-pass alignment hardening (frontmatter + 9-section + output-schema sync + tooling allowlist + demo anti-patterns); 0.x first-draft per ADR-010; v1.0.0 lift Phase 01.1 retro |
| **E1 — M2 refactor** | SKIP this PR — Phase 00.6 standalone |
| **E2 — ADR-024 amendment** | LAND 3-line amendment in **Commit 8** of this branch — Commit 2 router wiring re-touched the `llm_gateway.services.billing_service → billing.models.CreditTransaction` import surface so the amendment lands in SAME PR per E5 policy |
| **E3 — ADR-014 honesty-pass** | ✅ Shipped 00.5a |
| **E4 — pytest-xdist** | DO NOT enable (F-12 preconditions unmet) |
| **E5 — Cross-context imports** | No new sanctioned exceptions without ADR-024 amendment in SAME PR |

## Audit findings status

- ✅ Architecture H1 — closed by Phase 00.5a
- ✅ Architecture H2 — closed by Phase 00.5a
- ✅ Compliance H-1 — closed by Phase 00.5a
- ⏳ Architecture H3 (sanctioned `llm_gateway → billing.models` import) — **ADR-024 amendment NOT YET LANDED**. Commit 2 router wiring re-touched the import surface without yet introducing the amendment. Amendment lands with **Commit 8** per the founder-resolved E2 decision.

## Next agent — read first (bootstrap-4 same as Phase 00.5a)

1. [`README.md`](./README.md)
2. [`STATUS.md`](./STATUS.md)
3. **this HANDOFF.md**
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md)

Then for Phase 00.5b continuation:

5. **`C:\Users\KUklonskiy\.claude\plans\crispy-crunching-sunset.md`** — full executable plan, Commits 4-8 detailed
6. [`_session-context/AUDIT-2026-05-19-PRE-PHASE-05/AUDIT-REPORT.md`](./_session-context/AUDIT-2026-05-19-PRE-PHASE-05/AUDIT-REPORT.md) — master audit + sections
7. [`roadmap/wave-0-foundation/phases/00.5-pydantic-ai-productivity-team.md`](./roadmap/wave-0-foundation/phases/00.5-pydantic-ai-productivity-team.md) — AC catalog + skeletons
8. [`contracts/role-prompts/`](./contracts/role-prompts/) — 4 first-draft roles for T5 alignment hardening (Commit 5)

## Founder action

1. **DO NOT merge this branch yet.** Phase 00.5b is a chunked deliverable but Commits 2-3 alone don't close the Wave 0 anchor. The PR opens after Commit 8 (Phase 00.5 ✅ Complete flip). Commits 2-3 are committed to `claude/phase-00-5b-runtime` and stay on the branch for the next session to extend.
2. **Open Phase 00.5b continuation session in the SAME worktree:**
   ```powershell
   cd C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\phase-00-5b-runtime
   # Bootstrap-4 reads: README.md + STATUS.md + this HANDOFF.md + 00-START-HERE.md
   # Then load plan + start at Commit 4. No grill required — all decisions stand.
   ```
   Brief for next session: *"Phase 00.5b continuation — execute Commits 4-8 of plan crispy-crunching-sunset.md + run mandatory 5-agent audit swarm + final Exit ritual + open PR. Commits 2-3 already landed on this branch (hashes 7c00b43 + e0aaba3). All grill-me decisions stay verbatim — paste-target in HANDOFF.md «Decisions standing» table is the source of truth. Pitfalls + verification protocol same as 00.5a."*

## Phase 00.5b session deliverables (remaining)

- **Commit 4:** `uv add pydantic-ai` first (verify pydantic 2.x compat in `uv.lock`). Write `src/llm_gateway/pydantic_ai_model.py::LLMGatewayModel(Model)` Pydantic-AI Model ABC subclass wrapping `LLMRouter` — `__init__(role_key, llm_router)`, `async def request(messages, ...)` → translates `ModelRequest` → `LLMRouter.chat(...)` → normalizes to `ModelResponse`; `async def request_stream(...)` similarly. Write `tests/_fixtures/canned_pydantic_ai/{__init__.py, market_brief_demo.py}` with `(role_key, scenario_id)`-keyed canned `ModelResponse` lists (artifacts shape-correct for AC9: brief ≥1500w RU, matrix 5×4, plan exactly 10 posts). Add `pydantic_ai_test_model` fixture to `tests/conftest.py` with `.set_response()` API + fail-loud on unknown key. `tests/llm_gateway/test_pydantic_ai_model_adapter.py` covers the adapter.
- **Commit 5:** `agents` bounded context. Migrations `backend/migrations/versions/agents/{0001_agent_archetypes.py, 0002_team_presets.py, 0003_agent_instances.py}` per `contracts/agents/schema.sql`. `src/agents/{__init__,models,schemas,exceptions,events}.py` + `services/{team_provisioning_service,archetype_service,role_prompt_loader}.py` + `routers/{teams,instances,archetypes}.py` + `tools/{__init__.py, delegate.py}` + `seed_data/productivity_core_v1.py` + 4 agent files `{coordinator,researcher,writer,analyst}.py` (each `Agent(model=LLMGatewayModel(role_key=...), deps_type=..., result_type=..., tools=[...])`). Wire `team_provisioning_service.provision_team(preset_key='productivity_core', cell_id, user_id)` into `src/iam/services/auth_service.py:151-160` register flow (AC1). First-pass alignment hardening of 4 role-prompts in `contracts/role-prompts/`. Extend per-module gate with `agents` + add unit-test stubs for `_shared/db` (rls.py mock-based) + `_shared/middleware` (tenant_context.py mock-based) to enable those gates.
- **Commit 6:** `tasks` + `runtime`. Migrations `backend/migrations/versions/tasks/{0001_tasks.py, 0002_task_steps.py, 0003_task_artifacts.py}` with FORCE RLS via `_shared.current_cell_id()` helpers. `src/tasks/{__init__,models,schemas,exceptions (DelegationDepthExceeded, BudgetExceeded, TaskCancelled),events}.py` + `services/{task_service,cost_rollup_service}.py` + `routers/{tasks (CRUD), stream (SSE GET)}.py`. `src/runtime/{__init__,orchestrator,sse_events,sse_publisher (Redis pub/sub),budget_guard (50 T-credit reservation)}.py`. `tests/llm_gateway/test_budget_cap.py::test_record_llm_cost_raises_budget_exceeded_above_50_credits` closes F-P5-2 (AC10 anchor). Extend per-module gates with `tasks` + `runtime`.
- **Commit 7:** Demo flow. `tests/agents/test_market_brief_demo_flow.py` E2E via `pydantic_ai_test_model` asserts SSE event order + 3-parallel delegation + CoordinatorOutput shape + cost rollup math + 3 artifact contracts. `tests/agents/test_cancel_cascade.py` AC12. `tests/llm_gateway/test_provider_{deepseek,yandex,gigachat}_chat_stream.py` respx-mocked SSE (F-P5-4 partial). `backend/scripts/demo_market_brief.py` runnable script: `--api-base-url --jwt --runs N --output dir` (Phase 00.6 runs against staging for gate evidence).
- **5-agent audit swarm (MANDATORY per founder brief)** — spawn IN PARALLEL via Agent tool, each writes section to `.planning/_session-context/AUDIT-2026-05-20-PHASE-00-5/section-XX.md`:
  1. **Code Reviewer** — MUST be here (paused PR #30, completed PR #32, mandatory)
  2. **Security Engineer** — RLS middleware integrity + provider DI + plaintext key handling in Settings propagation + SECURITY DEFINER function audit
  3. **Test Results Analyzer** — adequacy of `pydantic_ai_test_model` + provider matrix coverage + marker discipline + mock-vs-real boundaries
  4. **Backend Architect** — Pydantic-AI runtime patterns + new bounded contexts shape + main.py lifespan correctness + DI seams + cross-context import graph DAG
  5. **Vertical-Domain Evaluator** (productivity-core preset first-pass) OR **Compliance Auditor** (cross-phase: ADR-014 honesty-pass actual landing, ADR-024 amendment landing, vertical-domain readiness for Wave-1 Master-Agent extension per ADR-029)

  Consolidate findings → AUDIT-REPORT.md master, apply in-loop fixes per verdict, defer Wave-1 items with explicit AC pin.
- **Commit 8 (Exit ritual + PR):** `.planning/decisions/ADR-024-bounded-context-contracts.md` 3-line "Sanctioned cross-context model imports" amendment legitimising `llm_gateway.billing_service → billing.models.CreditTransaction` (closes Architecture H3). Rewrite STATUS.md + HANDOFF.md per Exit ritual. Append JOURNAL.md. Flip `roadmap/wave-0-foundation/PHASES.md` Phase 00.5 ✅ Complete. Open PR `[Phase-00.5b] Pydantic-AI runtime + router wiring + demo + 5-agent audit` with description referencing `gates/wave-0-to-1.md` AC8/AC10 deferral status (PROVEN-IN-CI canned / VALIDATED-IN-STAGING pending 00.6).

## SLIP-CANDIDATES (only if headroom — else 00.5c or 00.6)

- **Commit 9 (F-P5-3):** migrate `test_byok_flow_full.py` + `test_cost_ledger_sum_match.py` from in-memory fakes → real testcontainers PG `db_session`.
- **Commit 10 (F-P5-4 GigaChat OAuth):** `tests/llm_gateway/test_provider_gigachat_oauth.py::test_token_refresh_after_expiry_uses_new_credentials`.

## Known caveats (carryover + deferred)

- **AC8 + AC10 measurement** (p95 ≤120s; cost ≤30¢) — deferred to Phase 00.6 staging first run per T4 Hybrid (b). Phase 00.5b CI ships canned-data flow + runnable `scripts/demo_market_brief.py`; gate evidence (D5 of `wave-0-to-1.md`) collected when staging deploys with live keys.
- **5-agent audit swarm is Phase 00.5b deliverable**, not 00.5a (which was 1-commit foundation only).
- **F-P5-3 + GigaChat-OAuth** are explicit SLIP-CANDIDATES per Topic 2 — only ship in 00.5b if headroom exists; otherwise defer to 00.6.
- **2026-06-09 Wave-0 target at ~65% confidence** per pre-Phase-05 Section-05 audit. Phase 00.5a chunking pattern protects against the «one giant PR fails» mode but adds a merge cycle. Founder may opt to fold 00.5b chunks into a single review session if cadence permits.
- **Slug-based cross-tenant linkage** (Wave-1 backlog) — unchanged.
- **TOCTOU SSRF in `read_url`** — Wave-1 hardening, unchanged.
- **`alembic.ini` cp1251 on Windows** — Phase 00.6 cleanup, unchanged.
- **Live LLM provider tests (`@pytest.mark.live`)** — Phase 00.6 once provider keys provisioned.

## Pitfalls confirmed (carry-over from 00.5a + new)

- **Worktree-prefixed paths only.** Edit/Write absolute paths to `C:\...\worktrees\phase-00-5b-runtime\...`, NEVER main-repo paths (stale).
- **`oriion_app` role override in `override_get_db`** IS the canary — surfaces prod RLS posture in CI.
- **`rbac.system_roles` natural key is `slug`** (NOT `code`) per Phase 00.5a fix. If `team_provisioning_service` resolves roles (Commit 5), use `WHERE slug = ...`.
- **No new cross-context model imports without ADR-024 §3 amendment in SAME PR.** Phase 00.5b Commits 5-6 add 3 new bounded contexts (agents/tasks/runtime); all cross boundaries go through `emit_audit_event` (sanctioned port) and `LLMRouter` (FastAPI DI, NOT model import).
- **Do NOT enable pytest-xdist** (F-12 preconditions unmet).
- **`.claude/settings.local.json`** already gitignored (00.5a) — verify `git status` before staging.
- **CI environmental CVE drift** — pip-audit MAY find new disputed advisory; if so, add to ADR-014 «Pip-audit ignored advisories registry» + `--ignore-vuln` in CI workflow.
- **Lifespan + tests:** the new `lifespan` in `main.py` does NOT run when tests use `ASGITransport` without `LifespanManager`. The existing `tests/integration/test_e2e_auth_flow.py::app` fixture relies on `dependency_overrides` and doesn't hit llm_gateway endpoints, so it's unaffected. For Commit 7 demo-flow integration test that DOES hit llm_gateway: either wrap with `asgi_lifespan.LifespanManager(app)` OR override `get_llm_router` via `dependency_overrides[get_llm_router] = lambda: fake_router`.
- **pydantic-ai not yet in `pyproject.toml`** — Commit 4 first step is `uv add pydantic-ai` + lock-file commit hygiene.

## Exit ritual completed (this session — Phase 00.5b mid-session)

- [x] JOURNAL.md entry appended (top-of-file timestamped block)
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md updated — Phase 00.5b 🔄 In progress; Commits 2-3 enumerated; remaining Commits 4-8 + audit
- [x] Plan file persists at `C:\Users\KUklonskiy\.claude\plans\crispy-crunching-sunset.md` for continuation
- [ ] **NOT opening PR this session** — chunked deliverable; PR opens after Commit 8 + 5-agent audit complete
- [x] Branch `claude/phase-00-5b-runtime` ready for push (next: `git push -u origin claude/phase-00-5b-runtime`)
