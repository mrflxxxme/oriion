# AUDIT REPORT — Pre-Phase-00.5 cross-phase audit

> Consolidated 5-agent independent audit of repository state on
> `claude/pre-phase-05-audit` (off main post-PR-#32 merge,
> `git rev-parse HEAD = 20451e0`), executed 2026-05-19 per founder
> request for a "completeness + integrity + alignment + navigation"
> check before Phase 00.5 begins.

## Scope

Cross-phase audit covering Wave-0 phases 00.1, 00.2, 00.3, 00.4, 00.2.5.
Distinct from PR-scoped audits (PR #30, PR #32) — this audits the
**cumulative** repository state, not a single PR's diff. Plus Wave-1+
forward-gap check (founder grill Q4).

## Top-level verdict: **FLAG → PASS after fixes**

No BLOCK-class findings. All 5 auditors agree Phase 00.5 can start
once in-loop fixes are applied + structural decisions are taken.

| Section | Auditor | Verdict | High / Med / Low |
|---|---|---|---|
| 01 Compliance | Compliance Auditor | FLAG | 1 / 2 / 4 |
| 02 Architecture | Backend Architect | FLAG | 3 / 5 / 6 |
| 03 Test Adequacy | Test Results Analyzer | FLAG | 3 / 4 / 7 |
| 04 Info Architecture | Technical Writer | FLAG | 6 / cluster / cluster |
| 05 Roadmap Alignment | Product Manager | FLAG | 0 / 5 / 3 |

Phase 00.5 architectural readiness: **4 / 5** (per Architecture audit).
Phase 00.5 test-infra readiness: **READY-WITH-CONDITIONS** (per Test
audit). 2026-06-09 Wave-0 target feasibility: **~65 %** (per Roadmap).

## Cross-cutting threads (multiple audits flagged the same root cause)

### Thread A — RLS posture (Compliance H-1 + Architecture H1 + H2)

Three audits flagged the same underlying issue from different angles:

* **Compliance H-1**: ADR-014:9 amendment claims "default-deny RLS in
  Wave-0", but production wouldn't actually default-deny because…
* **Architecture H1** (carryover from PR #32 H-DEFER-2): `register()`
  writes to `multitenancy.{workspaces, cells, cell_members}` with FORCE
  RLS — passes only because testcontainers connects as `oriion` DB-owner
  (bypasses FORCE RLS); production `oriion_app` would fail.
* **Architecture H2** (NEW): `_shared/db/rls.py::set_tenant_context` is
  **dead code in production** — `grep -rn 'set_tenant_context'
  backend/src/` returns only 3 hits inside the rls.py module itself.
  Zero callers in any service / middleware / router. Even if register
  is fixed, every authenticated `GET /workspaces` would return an empty
  page in production because the GUCs are never set.

**Resolution**: Phase 00.5 must land **atomically** in a single commit:
  1. A GUC middleware (FastAPI dependency or request-scope tx hook) that
     sets `app.current_user_id`/`workspace_id`/`cell_id` GUCs from the
     JWT claims for every authenticated request
  2. A bootstrap path for `register()` — SECURITY DEFINER provisioning
     function, **or** loosen INSERT policy for the unauth bootstrap,
     **or** set GUCs to the just-created user_id before writes
  3. Test fixture update — `SET LOCAL ROLE oriion_app` in
     `tests/integration/test_e2e_auth_flow.py::override_get_db` so the
     production failure mode is surfaced by CI
  4. ADR-014 amendment honesty pass — either declare the bootstrap
     exception explicitly, or claim default-deny only after the fix lands

**Tracking**: Phase 00.5 AC #1 (already pinned in HANDOFF.md).

### Thread B — Phase 00.1 status drift (Compliance L-3 + Info-Arch H-2)

`00.1-repo-cicd.md:3` still reads `Status: 🔄 In progress` while
STATUS.md correctly says ✅ Complete and the PR (#25) merged
2026-05-17. Same finding from two angles — straightforward fix.

### Thread C — Contract drift to legacy `organization` term (Compliance M-1 + M-2)

The 2026-05-17 architect-PR + 03d06a4 cherry-pick supposedly cleaned up
the legacy `organization` → `workspace` rename. Two contracts still
slipped through:

* `contracts/billing/schema.sql` — `organization_id` in skeleton DDL
* `contracts/rbac/api.yaml` (6 places) + `contracts/rbac/events.yaml`
  (3 places) — enum `[organization, cell]` instead of `[workspace, cell]`

DB CHECK constraints + ORM use `workspace`; only the contract docs are
stale. Single doc-only commit closes both.

### Thread D — Phase 00.2.5 spec absence (Info-Arch H-3 + Roadmap)

No `00.2.5-integration.md` in `roadmap/wave-0-foundation/phases/`.
The launch checklist + post-merge audit serve as the historical record,
but the phase has no canonical spec where future agents would normally
look. Acknowledged debt (A-8 from PR #32 post-merge audit) — needs
explicit founder decision: write the spec or formally close A-8 with a
"this phase doesn't get a spec, see X instead" pointer.

### Thread E — `_session-context/` discoverability (Info-Arch H-4 + general)

`.planning/_session-context/` now contains 6 distinct artifacts (2 PR
audits × 5-6 sections each + 2 launch checklists + 1 architect-PR doc +
this audit). No README/index. A cold-start agent has no map.

### Thread F — `live` pytest marker zero consumers (Compliance L-4 + Test L-class)

Marker declared in pyproject.toml; zero tests use it. HANDOFF.md
honestly acknowledges this as Phase 00.6 reservation. No fix needed —
just confirmation that the docstring stays as intended.

## Findings classification

### In-loop fixes (apply this PR)

| ID | Source | File:line | Fix |
|---|---|---|---|
| F-IL-1 | Compliance M-1 | `contracts/billing/schema.sql` | Rename `organization_id` → `workspace_id` in skeleton DDL |
| F-IL-2 | Compliance M-2 | `contracts/rbac/api.yaml` (6 places) + `contracts/rbac/events.yaml` (3 places) | Rename enum `[organization, cell]` → `[workspace, cell]` |
| F-IL-3 | Compliance L-1 | 6 stale `src/_stubs/` docstring refs in `workspace_service.py:4-5,55`, `audit/__init__.py:9`, `audit/services/__init__.py:6`, `audit/services/audit_service.py:4-30,185-186` | Update to "Phase 00.2.5 integration" / remove ghost references |
| F-IL-4 | Compliance L-2 | `OPEN-QUESTIONS.md:11+66` | Change "До Phase 00.2" → "До prod-launch" (historical) |
| F-IL-5 | Compliance L-3 + Info-Arch H-2 | `roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:3` | Status: 🔄 In progress → ✅ Complete (merged 2026-05-17 via PR #25) |
| F-IL-6 | Info-Arch H-5 | `agent-handbook/07-AI-TEAM-PIPELINE.md` | Fix 2 broken ADR-025 links (`ADR-025-gate-format.md` → `ADR-025-acceptance-gate-format.md`) |
| F-IL-7 | Test L-cluster | various | Cleanup duplicated `live` marker declarations + alembic workaround triplication |
| F-IL-8 | Compliance L-4 + Test | `pyproject.toml` | Confirm `live` marker docstring states "reserved for Phase 00.6"; no action if already says that |
| F-IL-9 | Info-Arch H-1 | `agent-handbook/04-HANDOFF.md` | Replace `.planning/handoffs/` references with current single-rolling HANDOFF.md practice (6 places) |

### Structural — surfaced via AskUserQuestion before applying

| ID | Source | Decision needed |
|---|---|---|
| F-ST-1 | Info-Arch H-3 + Roadmap | Create `roadmap/wave-0-foundation/phases/00.2.5-integration.md` from the launch checklist + post-merge audit, OR formally close A-8 with a pointer in roadmap README? |
| F-ST-2 | Info-Arch H-4 | Add `.planning/_session-context/README.md` (index) + archive completed-phase audits to `_session-context/archive/`? |
| F-ST-3 | ADR-024 amendment (A-12 from PR #32) | Add ADR-024 "Sanctioned exceptions" amendment for `llm_gateway → src.billing.models` atomic 3-currency write? |
| F-ST-4 | ADR-014 + Thread A | Defer to Phase 00.5 (where the fix lands)? Or add a pre-Phase-05 "honesty pass" amendment now? |
| F-ST-5 | Info-Arch JOURNAL broken links | Fix 2 broken `(.planning/...)` relative-from-`.planning/` links in JOURNAL.md — does fixing typos violate the append-only invariant? |

### Phase 00.5 deferred (with explicit acceptance criteria in HANDOFF)

| ID | Source | Phase 00.5 AC |
|---|---|---|
| F-P5-1 | Architecture H1+H2 + Compliance H-1 | Wire `set_tenant_context` middleware + fix register bootstrap path + amend ADR-014 honestly (Phase 00.5 AC #1) |
| F-P5-2 | Test F-03 | Add `BudgetExceeded` per-task cap test (Phase 00.4 AC10 retroactive) |
| F-P5-3 | Test F-02 | Migrate `test_byok_flow_full.py` + `test_cost_ledger_sum_match.py` from in-memory fakes to real testcontainers PG |
| F-P5-4 | Test F-04/F-05 | Cover chat_stream SSE paths in all 4 providers + GigaChat OAuth2 `_ensure_token` |
| F-P5-5 | Test F-07 | Pick ONE router-test convention (mini-app vs main.py-app) and document |
| F-P5-6 | Test F-08 | Add `_shared/db` + `billing` to per-module coverage gate loop |
| F-P5-7 | Architecture H3 (cross-context import) | Either land ADR-024 amendment (F-ST-3) **or** refactor `billing_service → billing.models` to outbox / port |
| F-P5-8 | Test F-01 | Implement `test_compose_dev_starts_within_3_min` for Phase 00.1 AC6 retroactive (deferred originally because docker network EOF on founder's Windows box) |

### Wave-1+ deferred (catalogue only)

| ID | Source | Wave-1 owner |
|---|---|---|
| F-W1-1 | PR #32 H-DEFER-1 (carryover) | Slug-based cross-tenant linkage in `provision_initial_workspace` — uuid-suffix on collision OR raise WorkspaceSlugConflict OR per-user provisioning UUID |
| F-W1-2 | PR #32 architect-audit H1 | TOCTOU SSRF in `mcp/tools/read_url.py` — DNS-rebinding hardening |
| F-W1-3 | Roadmap audit (BYOK coverage) | Expand BYOK upstreams beyond OpenAI/Anthropic per ADR-008 (9 promised) |
| F-W1-4 | Roadmap audit (ROLE_TO_MODEL) | Restore per-agent model mapping vs current 4-key collapse |

## Validations confirmed clean by ≥1 auditor

* Migration chain: 8 heads chain via `_shared_0001_init` / `_0002`. CI uses `alembic upgrade heads` (plural).
* `backend/src/_stubs/` directory verified deleted.
* STATUS / HANDOFF / JOURNAL three-way agreement on current phase state.
* PLACEHOLDERS registry matches in-code TBD references.
* Per-module coverage gates uniform ≥85 % across all 6 contexts (iam 86.77, multitenancy 88.42, rbac 100, audit 100, llm_gateway 88.22, mcp 92.98).
* Bounded-context import graph is a DAG; only 1 sanctioned cross-context import (`llm_gateway → billing.models`).
* `audit.audit_log` + `billing.credit_transactions` append-only triggers + revoked UPDATE/DELETE grants.
* Failover chain `deepseek → yandex → gigachat` + circuit-breaker state machine.
* Per-cell schema provisioning atomic with cells INSERT (caller's outer TX).
* CloudEvents source + type values uniform (`oriion://contexts/<ctx>` + `oriion.<ctx>.<entity>.<action>.v1`).
* No Wave-1+ phase-spec references non-existent W0 artefact.
* No Telegram libs pre-emptively imported before Wave-1.
* `locale='ru-RU'` / `timezone='Europe/Moscow'` / `country_code='RU'` defaults in iam.users + multitenancy.workspaces (FZ-152 ready).
* RU-currency triad in `llm_usage_log` (cost_usd + cost_rub + fx_rate_usd_to_rub) atomic-write contract tested.

## Phase 00.5 readiness summary

* **Architecture**: 4/5 — clean DI extension points; Thread A is the single blocker (already AC #1).
* **Test infra**: READY-WITH-CONDITIONS — existing `conftest.py` fixtures extensible; need new fixtures `pydantic_ai_test_model`, `sse_client`, `seeded_team_preset`. Do NOT enable pytest-xdist (preconditions unmet).
* **Roadmap**: Phase 00.5 owns the heaviest single phase work (main.py router wiring + provider DI assembly + multi-agent runtime + verticals scaffolding + demo runner). 2026-06-09 W0 target at ~65 % confidence; founder should write a "what we'd cut if we slip" list.
* **Navigation**: After in-loop + structural fixes from this PR, ~20-40 min agent-time saved per future session.

## References

- Section reports in this directory: `section-01-compliance.md`,
  `section-02-architecture.md`, `section-03-test-adequacy.md`,
  `section-04-info-architecture.md`, `section-05-roadmap-alignment.md`.
- Prior PR-scoped audits:
  `.planning/_session-context/archive/2026-05-19-audit-pr-30/AUDIT-REPORT.md` (PR #30),
  `.planning/_session-context/archive/2026-05-19-audit-pr-32/AUDIT-REPORT.md` (PR #32).
- Roadmap: `roadmap/wave-0-foundation/phases/`.
- HANDOFF.md "Known caveats" + "Founder action" sections.
