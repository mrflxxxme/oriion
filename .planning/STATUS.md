# STATUS — текущее состояние проекта

> Rolling-status. Обновляется при phase complete / blocker resolved / новом ADR.

## Wave-progress

| Wave | Status | Anchor target |
|---|---|---|
| Pre-Wave-0 | ✅ Complete | Roadmap reorg per [Session-2026-05-15](./JOURNAL.md) |
| Wave 0 (Foundation) | 🔄 In progress | Horizontal `productivity-core` team — internal demo «Market & content brief» |
| Wave 1 (Core MVP) | ⏳ Pending | Horizontal + 2 vertical (Marketing-agency + Telegram-крейтор) + Telegram Business API |
| Wave 2 (Pixel + каталог) | ⏳ Pending | +WB-Селлер vertical + Pixel + Pyodide + Mini App + Master-Agent first-instances |
| Wave 3 (Глубина) | ⏳ Pending | +ИП-Бух + СМБ-Sales vertical + Vertical Rituals + PARA Workspace |
| Wave 4 (Масштаб) | ⏳ Pending | K8s + Partner programme + Telegram Stars billing |
| Wave 5+ (Enterprise) | ⏳ Pending | On-premise + open marketplace |

## Recent roadmap revision (2026-05-15)

Per session-decision (11 развилок resolved):

1. Wave 0 anchor: horizontal `productivity-core` team-preset вместо WB-Селлер vertical
2. WB-Селлер вертикаль переезжает Wave 0 → Wave 2 (теперь vertical-anchor для public beta)
3. Wave 1 ships: horizontal + Marketing-agency + Telegram-крейтор (без WB)
4. Wave 2 reduced: ИП-Бух + СМБ-Sales переезжают W2 → W3 (Wave 2 = horizontal + Marketing + Telegram + WB + Pixel + Pyodide + Mini App)
5. Wave 3 grows: +ИП-Бух + СМБ-Sales (+2 нед)
6. Dual messaging positioning: «универсальная команда + РФ-вертикали поверх»
7. Master-Agent layer добавлен для vertical-templates per [ADR-029](./decisions/ADR-029-master-agent-vertical-templates.md)
8. Telegram-mcp v0.2 — Read + post + Business API per [ADR-030](./decisions/ADR-030-telegram-business-api.md) (W1); Mini App W2; Stars billing W4+
9. Deep role prompts для horizontal preset — в [`contracts/role-prompts/`](./contracts/role-prompts/) (first-draft в Phase 00.5, hardening pass в Phase 01.1 retro)

## Текущая активная фаза

**Phase 00.5a (RLS foundation)** — ✅ **Code-complete** on branch `claude/admiring-chaplygin-7da2f7` (2026-05-20). Chunked deliverable per Topic 2 cut-list philosophy from /grill-me session. Closes Architecture H1 (RLS-on-register bootstrap, carryover from PR #32 H-DEFER-2) + H2 (`set_tenant_context` dead-code finding from pre-Phase-05 audit) + Compliance H-1 (ADR-014 default-deny truthfulness). 1 atomic commit, 8 files, 754 insertions / 95 deletions.

Per Phase 00.5 Topic 1 (founder-resolved 2026-05-20, RLS Option A): two SECURITY DEFINER SQL functions land in migration `multitenancy/0005_bootstrap_first_workspace_function.py`:
* `multitenancy.bootstrap_first_workspace(p_user_id, p_workspace_slug, p_display_name)` — register-time bootstrap escape. Provisions 4-row tuple (workspace + cell + cell_member with `rbac.system_roles.cell.owner` + per-cell schema) atomically; idempotent replay on slug lookup; returns `(workspace_id, cell_id, schema_name, was_replay)`.
* `multitenancy.resolve_user_first_membership(p_user_id)` — companion for the tenant_context middleware chicken-and-egg lookup; bypasses RLS to resolve `(workspace_id, cell_id)` before the GUC can be set.

New `backend/src/_shared/middleware/tenant_context.py::get_tenant_db_session` is the SOLE production caller of `set_tenant_context` — closes Architecture H2. `backend/src/multitenancy/services/workspace_service.py::provision_initial_workspace` refactored to delegate to the bootstrap SQL function. `backend/tests/integration/test_e2e_auth_flow.py::override_get_db` tightened with `SET LOCAL ROLE oriion_app` so CI surfaces the production RLS posture. Focused test in `tests/multitenancy/test_bootstrap_first_workspace_function.py` validates the SECURITY DEFINER escape under `oriion_app`. ADR-014 §1 honesty-pass amendment lands per F-ST-4 deferral. ADR-009 §5 cross-references same.

**Phase 00.5b (runtime)** — 🔄 **In progress — Commits 2-3 of 8 landed on branch `claude/phase-00-5b-runtime`** (2026-05-20 mid-session checkpoint). Commits 4-8 + MANDATORY 5-agent audit swarm + Exit-ritual-Phase-Complete flip + PR are deliverables for the next session in the SAME worktree. Per Topic 2 cut-list (chunked deliverable):

* ✅ **Commit 2** `7c00b43` — feat(main,llm_gateway): wire multitenancy+LLM routers + lifespan provider DI. 5 files, +452/-32. `src/main.py` overhaul (multitenancy + llm_gateway routers + 4 exception handlers + lifespan provider DI from Settings + LLMRouter chain `(deepseek, yandexgpt, gigachat)` per ADR-018); `src/llm_gateway/deps.py` NEW (`get_llm_router`/`get_kms_provider`/`get_byok_service` factories from `request.app.state`); `src/_shared/config.py` promotes 4 LLM provider credentials to `Settings` (closes audit M3); `tests/integration/test_main_app_routes.py` NEW (mount-smoke parametrised over 13 (path, method) pairs); stale `test_llm_chat_endpoint_is_not_yet_wired` canary deleted. Verification: 32 routes mounted, 15/15 mount-smoke pass, 386 unit tests pass, ruff clean. mcp routers intentionally NOT included (Wave 0 mcp framework-only per ADR-013).
* ✅ **Commit 3** `e0aaba3` — ci,docs: per-module gate for billing + router-test convention. 2 files, +35/-5. CI per-module loop extends with `billing` gate (current 100%); F-P5-5 two-layer router-test convention documented in `_meta/conventions.md` (mini-app `tests/<context>/unit/test_routers.py` + main-app mount-smoke `tests/integration/test_main_app_routes.py`). `_shared/db` + `_shared/middleware` + `agents`/`tasks`/`runtime` gates deferred to Commits 5-6 landing commits.
* ⏳ **Commit 4** (Pydantic-AI mock fixture + LLMGatewayModel adapter): `uv add pydantic-ai` first; `src/llm_gateway/pydantic_ai_model.py::LLMGatewayModel(Model)` Pydantic-AI Model ABC subclass + `tests/_fixtures/canned_pydantic_ai/market_brief_demo.py` with `(role_key, scenario_id)`-keyed canned `ModelResponse` lists + `pydantic_ai_test_model` fixture in `tests/conftest.py` + adapter unit tests (T3 resolution).
* ⏳ **Commit 5** (`agents` bounded context + 4 Pydantic-AI agents + role_prompt_loader + first-pass alignment hardening per T5).
* ⏳ **Commit 6** (`tasks` + `runtime` orchestrator + SSE publisher + budget guard; F-P5-2 BudgetExceeded test = AC10 anchor).
* ⏳ **Commit 7** (Demo flow integration test via `pydantic_ai_test_model` per T4 hybrid + 3 chat_stream SSE provider tests F-P5-4 partial + runnable `scripts/demo_market_brief.py` for Phase 00.6 staging gate-evidence collection).
* ⏳ **5-agent audit swarm (MANDATORY per founder brief)**: Code Reviewer + Security Engineer + Test Results Analyzer + Backend Architect + Vertical-Domain Evaluator (productivity-core preset readiness for Wave-1 Master-Agent extension).
* ⏳ **Commit 8** (ADR-024 §3 amendment for sanctioned `llm_gateway → billing.models` per E2 — still NOT YET LANDED; Architecture H3 closure pending + Exit ritual + Phase 00.5 ✅ Complete flip + PR open).

**AC8 (p95 ≤120s) + AC10 (cost ≤30¢) measurement deferred to Phase 00.6 staging first run** per T4 resolution (Hybrid (b)). Phase 00.5 CI ships canned-data flow + runnable demo script; gate evidence (D5 of `wave-0-to-1.md`) collected when staging deploys with live keys.

**Pre-Phase-00.5 audit + nav cleanup** — ✅ **Merged** 2026-05-19 via [PR #33](https://github.com/mrflxxxme/oriion/pull/33), merge-commit `60e327e`. Original code-complete entry below preserved for cross-ref:

**Pre-Phase-00.5 audit + nav cleanup (PR #33 history)** — ✅ **Code-complete** on branch `claude/pre-phase-05-audit` (2026-05-19). Cross-phase 5-agent independent audit (Compliance / Architecture / Test-Adequacy / Info-Architect / Roadmap-Reviewer) covering cumulative Wave-0 state. Top-level verdict: PASS-WITH-FIXES (0 BLOCK; 4 HIGH addressed in-loop, 2 HIGH explicitly deferred to Phase 00.5 with named ACs). In-loop fixes applied: stale `_stubs/` docstring refs across 4 backend src files; contract drift (`contracts/billing/schema.sql` + `contracts/rbac/{api,events}.yaml` renamed `organization` → `workspace`); Phase 00.1 spec Status flip; OPEN-QUESTIONS.md historical phrasing; 6 broken markdown links in JOURNAL.md + `agent-handbook/07-AI-TEAM-PIPELINE.md`; `agent-handbook/04-HANDOFF.md` rewrite (deleted handoffs/ directory pattern → single-rolling HANDOFF.md); branch-naming convention documented (`claude/<adjective-noun-hash>` ratified). Structural fixes: ADR-024 "Sanctioned cross-context exceptions" amendment (documents `llm_gateway → billing.models` as known-good per llm-gateway invariant #7); created canonical Phase 00.2.5 phase-spec; added `_session-context/README.md` index + archived completed-phase audits to `_session-context/archive/`; created 5 missing READMEs (contracts/role-prompts, gates/_schema, verticals/wb-seller/{prompts, golden-dataset/{adversarial, tasks}}). Full report in [`_session-context/AUDIT-2026-05-19-PRE-PHASE-05/AUDIT-REPORT.md`](./_session-context/AUDIT-2026-05-19-PRE-PHASE-05/AUDIT-REPORT.md).

**Phase 00.2.5 (integration)** — ✅ **Complete** (merged 2026-05-19 via [PR #32](https://github.com/mrflxxxme/oriion/pull/32), merge-commit `20451e0`). 8 atomic commits. Deletes `backend/src/_stubs/`; rewires `emit_audit_event` + `provision_initial_workspace` at all 4 production call-sites; adds `session: AsyncSession` to `AuthService.__init__` so audit_log inserts + workspace provisioning share the request's outer TX. Session-scoped testcontainers PG fixture + SAVEPOINT-rollback + `commit_required` marker carve-out. 5-test E2E suite (register → verify-email → login → refresh → logout) against real PG. 45 new unit tests for router glue. Per-module coverage uniformly ≥85% on unit-only runs (iam 87, multitenancy 88, rbac 100, audit 100, llm_gateway 88, mcp 93). `Base.type_annotation_map` fix (`Mapped[datetime]` → `TIMESTAMP WITH TIME ZONE`). 5-agent independent audit (Code-Reviewer + Security + Test-Adequacy + Architecture + Compliance) verdict PASS-WITH-FIXES; 4 HIGH fixed in-loop, 2 HIGH deferred to Phase 00.5 (slug-based cross-tenant linkage in `provision_initial_workspace` + RLS-on-register bootstrap requires SECURITY DEFINER OR role re-wire). Full audit report in [`_session-context/archive/2026-05-19-audit-pr-32/AUDIT-REPORT.md`](./_session-context/archive/2026-05-19-audit-pr-32/AUDIT-REPORT.md). Canonical phase-spec at [`roadmap/wave-0-foundation/phases/00.2.5-integration.md`](./roadmap/wave-0-foundation/phases/00.2.5-integration.md).

**Phase 00.3 (DB + RLS + multitenancy + audit) + Phase 00.4 (LLM Gateway + MCP + RU-billing)** — ✅ **Complete** (merged 2026-05-19 via PR #30, merge-commit `b3837f0`). Combined PR shipped 8 atomic commits + 9 follow-up CI/test fixes. 5-agent independent audit swarm (Compliance / Security / Test Adequacy / Architecture + Code Reviewer paused) ran; 4 HIGH-severity findings fixed in-loop (forward-reference policy, unsafe RLS GUC cast, append-only triggers for llm_usage_log + credit_transactions, write policies for multitenancy). Full audit report in [`_session-context/archive/2026-05-19-audit-pr-30/AUDIT-REPORT.md`](./_session-context/archive/2026-05-19-audit-pr-30/AUDIT-REPORT.md). Post-merge consistency audit in [`_session-context/archive/2026-05-19-post-merge-audit-pr-30.md`](./_session-context/archive/2026-05-19-post-merge-audit-pr-30.md).

**Phase 00.2 (Custom JWT auth, full-scope)** — ✅ **Complete** (merged 2026-05-18 via PR #28).

**Phase 00.1 (Repo & CI/CD)** — ✅ **Complete** (merged 2026-05-17 via [PR #25](https://github.com/mrflxxxme/oriion/pull/25), merge-commit `b192c6b`).

**Pre-Phase-00.3 contract extension PR (2026-05-19)** — ✅ **Code-complete on same branch** as part of 00.3+00.4 combined PR. Renames `multitenancy.organizations → multitenancy.workspaces` end-to-end (DDL + API + events + RLS GUC `app.current_organization_id → app.current_workspace_id` + rbac scope_type + llm_gateway.byok_keys + 5 ADR amendments with «Wave 0 implementation decisions» sections). Adds RU-currency triad (cost_usd + cost_rub + fx_rate_usd_to_rub) per ADR-018 amendment. Adds vector(1024) provenance columns per ADR-005 amendment. Adds 3-GUC RLS layered model per ADR-009 amendment. Adds 4 new PLACEHOLDER tokens (BYOK_MASTER_KEY_B64, YANDEX_CLOUD_KMS_KEY_ID, FX_RATE_USD_TO_RUB_OVERRIDE, YANDEX_SEARCH_API_KEY).

**Final AC scoreboard:**
- ✅ **AC2** (coverage ≥ 70%) — local-verified backend 100% (8 tests, 16/16 stmts), frontend utils.ts 100% (5 tests)
- ✅ **AC3** (3 CI workflows ≤ 8 min) — all 6 status checks PASS on PR (ci-backend / ci-frontend / ci-security 3 jobs / gitleaks / trivy / grype)
- ✅ **AC4** (gitleaks blocks AWS key) — gitleaks job green; full repo scanned
- ✅ **AC5** (license-check blocks GPL/AGPL/LGPL) — pip-licenses + license-checker-rseidelsohn run, 0 forbidden licenses
- ✅ **AC7** (lint + typecheck) — backend ruff + ruff-format + mypy --strict; frontend eslint + prettier + tsc -b — all green локально + в CI
- ⚠️ **AC1** (dev-bootstrap ≤ 600s) + **AC6** (compose healthchecks ≤ 180s) — **founder action**: верифицировать локально на машине со стабильным Docker Hub access (`cp .env.example .env && time docker compose -f infra/docker-compose.dev.yml up -d --build`). Session attempt failed на network EOF errors, не related к spec.

**Следующая фаза:** Phase 00.2 (Custom JWT auth). **3-way parallel разблокирован** для phases 00.2 + 00.3 + 00.4 после landing'а architect-PR (2026-05-17). OQ-04 — submitted (dev unblocked; финальное подтверждение РКН — до prod-launch). Founder стартует 3 worktrees: `claude/phase-00-2-jwt-auth`, `claude/phase-00-3-db-rls`, `claude/phase-00-4-llm-gateway`. После merge всех 3-х PR — отдельная integration session `claude/phase-00-2-5-integration`.

## Architect-PR (2026-05-17) — pre-Phase-00.2 contract extension

Чтобы открыть 3-way parallel execution для Wave-0 phases 00.2 / 00.3 / 00.4 без race conditions и contract gaps, отдельный architect-PR (branch `claude/dazzling-satoshi-0a293d`) landed:

- **`contracts/iam/schema.sql`** расширен 3 таблицами: `iam.consents` (FZ-152 ledger, версия pinned at grant), `iam.email_verification_tokens` (single-use, 24h TTL, SHA-256 hashed), `iam.password_reset_tokens` (single-use, 1h TTL, chain-revoke pattern по аналогии с refresh tokens).
- **`contracts/iam/api.yaml`** расширен 4 новыми endpoint'ами (`/auth/verify-email`, `/auth/resend-verification`, `/auth/forgot-password`, `/auth/reset-password`). `RegisterRequest` теперь требует `consent_pdn: true` (else 422 `iam.consent.pdn_missing`); response — новый `RegisterResponse` schema с `{user_id, workspace_id, cell_id}`. Anti-enumeration инвариант на forgot/resend (всегда 202).
- **`contracts/iam/events.yaml`** расширен 4 CloudEvents: `user.email_verification_requested.v1`, `user.password_reset_requested.v1`, `user.password_reset_completed.v1`, `user.consent_recorded.v1`.
- **`contracts/iam/README.md`** обновлён 4 новыми инвариантами (consent pdn mandatory, verification token TTL/hashing, reset chain-revoke, anti-enumeration).
- **`backend/migrations/versions/_shared/0001_init.py`** — новая foundation migration (поглощает scope ранее назначенный Phase 00.3): создаёт extensions (pgcrypto, citext, uuid-ossp, vector, pg_stat_statements), 12 bounded-context schemas, `_shared.set_updated_at()` trigger function, `oriion_app` NOLOGIN role с USAGE grants. Каждая phase'овая первая migration MUST set `down_revision = "_shared_0001_init"`.
- **`backend/alembic.ini`** `version_locations` расширен 12-ю bounded-context subdirs (+ `.gitkeep` файлами).

**Impact на Phase 00.3 scope:** schema-bootstrap step (CREATE SCHEMA + extensions + `_shared` trigger) **больше НЕ в скоупе 00.3** — done в architect-PR. 00.3 стартует прямо с multitenancy DDL.

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных, реальная обработка ПДн запрещена до closure. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

> **Note:** OQ-13/14/15/16 (hiring) закрыты как `N/A` per [P-INIT-5](./decisions/ADR-028-policies-registry.md#policies-canonical-home) (solo founder + 11 AI model). OQ-17 (funding) + OQ-18 (burn-budget) закрыты как `out-of-scope` per Session-2026-05-15 — founder-personal financial decisions не tracked в project docs (AI dev cost caps живут в `.claude/agents/_shared/cost-budget.yaml`).

## Phase 00.2 prerequisites (HIGH security debt — must clear перед auth merge)

⚠️ **Security debt уже закрыт в Phase 00.1 PR** — `python-jose` (CVE-2024-33663/33664) заменён на `PyJWT[crypto]`, `passlib` заменён на `argon2-cffi` per [ADR-014](./decisions/ADR-014-security.md). Auth code в Phase 00.2 уже может использовать чистые deps.

Полный список — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## Top-priority risks (active monitoring)

См. [`risks/REGISTER.md`](./risks/REGISTER.md).

1. R-04 (runaway costs) — high + high
2. R-05 (data leak) — critical + medium
3. R-08 (регуляторные изменения) — high + high
4. R-11 (retention/churn) — high + high
5. R-12 (scope creep) — critical + high

## Tech-стек snapshot

Полный список — [`_meta/stack.md`](./_meta/stack.md).

- Backend: Python 3.12 + FastAPI + Pydantic-AI
- Frontend: Vite 6 + React 19 + TanStack Router + Tailwind + shadcn/ui
- DB: PostgreSQL 16 + pgvector + Yandex Managed
- Cache: Redis 7 + Dramatiq
- 2D: Native Canvas
- Code-exec: Pyodide WASM (browser)
- Auth: Custom JWT (W0–1) → Logto (W2–3) → Keycloak (Enterprise)
- LLM: DeepSeek V3/R1 + YandexGPT + GigaChat + BYOK
- Cloud: Yandex Cloud ru-central-1

## Целевые сроки (revision 2026-05-15)

| Дата | Milestone | Delta vs prior |
|---|---|---|
| 2026-05-17 | Wave 0 Phase 00.1 **started + merged** (2 дня раньше plan) | **-2 нед** |
| 2026-06-09 | Wave 0 complete → Internal demo (horizontal `productivity-core`) | unchanged (compensates с 00.1 early-merge buffer) |
| 2026-07-21 | Wave 1 complete → Pre-alpha с 10–15 friends (3 templates) | unchanged |
| ~2026-09-22 | Wave 2 complete → Public beta (4 templates + Pixel + Mini App) | **+1 нед** vs prior 2026-09-15 |
| ~2026-12-01 | Wave 3 complete → GA-release (6 templates + Rituals + PARA) | **+3 нед** vs prior 2026-11-10 |
| ~2027-02-22 | Wave 4 complete → Scale + Partner | **+3 нед** vs prior 2027-02-02 |

## Update protocol

При phase complete / blocker resolved / новом ADR:

1. Обновить этот STATUS.md
2. Cross-ref в commit-message: `chore(status): wave 0 phase 00.1 complete`
