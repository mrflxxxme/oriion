# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-19 (Pre-Phase-00.5 cross-phase audit + navigation cleanup)
- Session: `pre-phase-05-audit` (worktree branch `claude/pre-phase-05-audit`)
- Agent: @claude-opus

## Project status

- **Wave:** Wave 0 (Foundation)
- **Phase 00.1 (Repo+CI/CD)**: ✅ Complete (merged 2026-05-17 via PR #25)
- **Architect-PR (pre-00.2)**: ✅ Complete (merged 2026-05-17 via PR #27)
- **Phase 00.2 (Custom JWT auth)**: ✅ Complete (merged 2026-05-18 via PR #28)
- **Phase 00.3 + Phase 00.4**: ✅ Complete (merged 2026-05-19 via PR #30, combined)
- **Phase 00.2.5 (integration)**: ✅ Complete (merged 2026-05-19 via PR #32)
- **Pre-Phase-05 audit + nav cleanup**: ✅ Code-complete on `claude/pre-phase-05-audit` (this session, pending PR)
- **Phase 00.5 (multi-agent tools + verticals scaffolding)**: ⏳ Pending — opens after this PR + RLS-fix decision lands

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | **Submitted** — dev unblocked. Final РКН confirmation required до prod-launch. |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку, нужно до открытия ЮKassa (Wave 1) |

## What just happened (this session)

Founder-requested pre-Phase-00.5 final audit — ensure repo is "complete + integrity + adequacy + alignment + contradiction-free + navigation-optimized" before Phase 00.5 begins.

### 4 decisions resolved via grill

| # | Topic | Resolution |
|---|---|---|
| Q1 | Audit basis | After PR #32 merge → main (this branch is off post-merge main) |
| Q2 | 5-agent composition | Cross-phase mix: Compliance + Architecture + Test-Adequacy + Info-Architect + Roadmap-Reviewer (different from per-PR composition; emphasizes navigation + next-phase readiness) |
| Q3 | Reorg mode | Hybrid (non-controversial in-loop + structural via AskUserQuestion) |
| Q4 | Completeness scope | Wave-0 AC + contracts + ADRs + Wave-1+ forward gaps |

### 4 structural decisions resolved via AskUserQuestion

| # | Topic | Resolution |
|---|---|---|
| F-ST-1 | 00.2.5 phase-spec | Created canonical retrospective spec at `roadmap/wave-0-foundation/phases/00.2.5-integration.md` + added to PHASES.md index |
| F-ST-2 | `_session-context/` discoverability | Created `README.md` index + archived PR #30 + PR #32 + launch-checklist + post-merge-audit to `archive/` |
| F-ST-3+4 | ADR amendments | ADR-024 "Sanctioned cross-context exceptions" amendment landed now; ADR-014 RLS honesty pass deferred to Phase 00.5 (lands with the practical fix) |
| F-ST-5 | JOURNAL.md broken links | Fixed as typos (not narrative rewrites; append-only invariant preserved) |

### 5-agent audit verdicts (cumulative Wave-0 state)

| Section | Auditor | Verdict | Headline |
|---|---|---|---|
| 01 Compliance | Compliance Auditor | FLAG | 1 HIGH (ADR-014 truthfulness re RLS bootstrap) + 2 MED contract drift + 4 LOW doc drift |
| 02 Architecture | Backend Architect | FLAG (Phase 00.5: 4/5) | 3 HIGH: RLS-on-register bootstrap (PR #32 H-DEFER-2 carryover) + `set_tenant_context` is dead code in production (zero callers) + sanctioned cross-context import |
| 03 Test Adequacy | Test Results Analyzer | FLAG (READY-WITH-CONDITIONS) | 3 HIGH: Phase 00.1 AC6 untested + 2 integration tests use in-memory fakes (false-flag) + Phase 00.4 AC10 BudgetExceeded untested |
| 04 Info Architecture | Technical Writer | FLAG | 6 HIGH: handoffs/ dir refs in 04-HANDOFF.md + Phase 00.1 spec status drift + no 00.2.5 phase-spec + no _session-context/ index + 4 broken markdown links |
| 05 Roadmap | Product Manager | FLAG, no blockers | Wave-0 anchor partial (Phase 00.5 owns HTTP wiring + Pydantic-AI runtime + agents/tasks contexts + demo); 2026-06-09 W0 target at ~65% confidence; recommends founder writes a cut-list before opening 00.5 |

### Fixes applied in-loop (this session)

* `_stubs/` docstring drift across `backend/src/multitenancy/services/workspace_service.py` + `backend/src/audit/{__init__.py, services/__init__.py, services/audit_service.py}` — historical references removed, replaced with current-state descriptions
* `contracts/billing/schema.sql`: `organization_id` → `workspace_id` across 6 occurrences + header comment
* `contracts/rbac/api.yaml` + `contracts/rbac/events.yaml`: enum `[organization, cell]` → `[workspace, cell]` (9 occurrences)
* `roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:3` — Status flipped to ✅ Complete (merge-commit + PR # added)
* `OPEN-QUESTIONS.md:11 + :66` — OQ-04 deadline phrasing modernised ("До Phase 00.2" → "До prod-launch")
* `agent-handbook/07-AI-TEAM-PIPELINE.md` — 2 broken `ADR-025-gate-format.md` links fixed to `ADR-025-acceptance-gate-format.md`
* `JOURNAL.md:48,50,51` — broken `(.planning/...)` relative-from-root links fixed to `(./...)`; append-only invariant preserved (typo-class corrections only)
* `agent-handbook/04-HANDOFF.md` — rewrote 6 references to deleted `.planning/handoffs/` directory; documented single-rolling HANDOFF.md pattern as canonical
* `agent-handbook/05-PR-WORKFLOW.md` — branch-naming table ratifies `claude/<slug>` as default for AI-led sessions; PR template `Handoff:` field updated; cheat-sheet aligned
* `_meta/conventions.md:42` — branch convention aligned with practice
* `PROJECT.md` "Текущая phase" — full rewrite to reflect Phase 00.1/00.2/00.3/00.4/00.2.5 ✅ + 00.5 next; STATUS.md pinned as single source of truth
* `decisions/ADR-024-bounded-context-contracts.md` — "Sanctioned cross-context exceptions" amendment added (documents `llm_gateway → billing.models` per llm-gateway invariant #7)
* `roadmap/wave-0-foundation/PHASES.md` — added Phase 00.2.5 row
* Deleted `verticals/wb-seller/golden-dataset/tasks/.gitkeep` (directory has 30 real files; the .gitkeep claimed the directory was empty)

### Structural changes applied this session

* Created `roadmap/wave-0-foundation/phases/00.2.5-integration.md` (canonical retrospective spec, 150 lines)
* Created `_session-context/README.md` (chronological index + naming convention + lifecycle)
* Archived `_session-context/2026-05-17-architect-pr-3-way-parallel.md` → `archive/2026-05-17-architect-pr-3-way-parallel.md`
* Archived `_session-context/PHASE-00-2-5-LAUNCH-CHECKLIST.md` → `archive/2026-05-19-phase-00-2-5-launch-checklist.md`
* Archived `_session-context/POST-MERGE-AUDIT-2026-05-19.md` → `archive/2026-05-19-post-merge-audit-pr-30.md`
* Archived `_session-context/AUDIT-2026-05-19/` → `archive/2026-05-19-audit-pr-30/`
* Archived `_session-context/AUDIT-2026-05-19-PR-00-2-5/` → `archive/2026-05-19-audit-pr-32/`
* Created 5 missing-README files: `contracts/role-prompts/README.md`, `gates/_schema/README.md`, `verticals/wb-seller/prompts/README.md`, `verticals/wb-seller/golden-dataset/{adversarial,tasks}/README.md`

### Findings explicitly deferred to Phase 00.5

* **H1 — RLS-on-register bootstrap + `set_tenant_context` dead code** (Architecture H1+H2 + Compliance H-1, all converging on same root cause): Phase 00.5 must land atomically: (a) GUC middleware setting `app.current_user_id/workspace_id/cell_id` from JWT claims, (b) bootstrap path for `register()` (SECURITY DEFINER OR loosen INSERT policy OR set GUCs to just-created user_id), (c) E2E fixture update `SET LOCAL ROLE oriion_app` to surface prod failure mode in CI, (d) ADR-014 honesty-pass amendment.
* **F-01 (Test) — Phase 00.1 AC6 dev-bootstrap test** retroactive
* **F-02 (Test) — byok_flow_full + cost_ledger_sum_match** migrate from in-memory fakes to real testcontainers PG
* **F-03 (Test) — Phase 00.4 AC10 BudgetExceeded** zero tests — needs Phase 00.5 LLM-router wiring before this can be tested via HTTP
* **F-W1-1 (carryover from PR #32) — slug-based cross-tenant linkage** in `provision_initial_workspace` — Wave-1 backlog
* **F-W1-2 (carryover from PR #30) — TOCTOU SSRF** in `mcp/tools/read_url.py` — Wave-1 hardening

## Next agent — read first

Standard bootstrap-4:

1. [`README.md`](./README.md)
2. [`STATUS.md`](./STATUS.md)
3. **this HANDOFF.md**
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md)

## Founder action (post-merge of this PR)

1. Review + merge PR `[audit] post-00.2.5 cross-phase integrity + navigation cleanup` from branch `claude/pre-phase-05-audit`.
2. **Decide on Phase 00.5 RLS approach** (this is the only structural call that wasn't already made by the audit pipeline):
   - **Option A:** Ship `multitenancy.bootstrap_first_workspace_security_definer(...)` SQL function as Phase 00.5 day-1 work — preserves "default-deny RLS" claim in ADR-014
   - **Option B:** Amend ADR-014 to honestly state register-flow uses DB-owner credentials in Wave-0
   - **Option C:** Restructure register() to call set_tenant_context with the just-created user_id BEFORE the workspace + cell INSERTs
3. Open Phase 00.5 session in a fresh worktree:
   ```bash
   git checkout main && git pull origin main
   git worktree add .planning/.claude/worktrees/phase-00-5-multi-agent -b claude/phase-00-5-multi-agent
   # Brief: "Phase 00.5 multi-agent tools + verticals scaffolding.
   #   * Land the RLS fix per founder Option A/B/C above (this is AC #1)
   #   * Wire multitenancy + LLM + MCP routers into src/main.py with /api/v1
   #     prefix; install MultitenancyError + LLMGatewayError + MCPError
   #     exception handlers (the iam mini-app test for workspaces router
   #     already shows the shape — see tests/multitenancy/test_workspaces_router.py)
   #   * Assemble LLM provider DI (DeepSeekProvider/YandexGPTProvider/
   #     GigaChatProvider + LocalAESKMS) inside the FastAPI lifespan
   #   * Replace test_e2e_auth_flow.py::test_llm_chat_endpoint_is_not_yet_wired
   #     with the full register → DeepSeek + Yandex + GigaChat + embeddings +
   #     BYOK matrix per launch-checklist Section 5
   #   * Migrate byok_flow_full + cost_ledger_sum_match from in-memory fakes
   #     to real testcontainers PG (F-02 from pre-phase-05 audit)
   #   * Add BudgetExceeded per-task cap test (F-03)
   #   * Scaffold first-vertical Master-Agent (productivity-core preset) per ADR-029
   #   * Update STATUS/HANDOFF/JOURNAL, mark 00.5 ✅ Complete."
   ```

## Known caveats (carryover + deferred)

- **LLM/multitenancy/MCP router DI wiring**: still owned by Phase 00.5. Routers exist as code; handlers return 501 today. Mini-app TestClient pattern (tests/multitenancy/test_workspaces_router.py) shows how to test routers in isolation pending full DI.
- **`set_tenant_context` is dead code in production** (NEW finding from this audit, Architecture H2): zero callers; must land Phase 00.5 first commit with GUC middleware.
- **Slug-based cross-tenant linkage** (carryover): `provision_initial_workspace` idempotency-on-slug means `alice@x.com` + `alice@y.com` silently share workspace. Wave-1 backlog.
- **TOCTOU SSRF in `read_url`**: Wave-1 hardening.
- **`alembic.ini` cp1251 on Windows**: Phase 00.6 cleanup. CI workaround in place.
- **Live LLM provider tests (`@pytest.mark.live`)**: zero consumers; Phase 00.6 once provider keys provisioned.
- **PROJECT.md PLACEHOLDERS.md and several contracts/llm-gateway/multitenancy files have uncommitted edits on main repo working tree** — separate concern, can be cleaned up via `git restore` on main repo independently of this PR.

## Exit ritual completed (this session)

- [x] JOURNAL.md entry will be appended in commit message + 1-line journal
- [x] HANDOFF.md rewritten (this file)
- [x] STATUS.md updated — Phase 00.2.5 ✅ Complete; Pre-Phase-05 audit code-complete; Phase 00.5 next
- [x] Phase-spec retro `00.2.5-integration.md` created
- [x] 5-agent audit swarm executed + consolidated report at `_session-context/AUDIT-2026-05-19-PRE-PHASE-05/AUDIT-REPORT.md`
- [ ] PR opened — final step of this session
