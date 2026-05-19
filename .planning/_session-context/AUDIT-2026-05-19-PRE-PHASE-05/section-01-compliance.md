# Section 01 — Cross-Phase Compliance & Consistency Audit (Pre-Phase-00.5)

**Auditor:** Compliance Auditor (sub-agent)
**Date:** 2026-05-19
**Branch under audit:** `claude/pre-phase-05-audit` (off main, post-PR-#32 merge)
**Audit window:** cumulative Wave-0 state — Phase 00.1 (PR #25) + architect-PR (#27) + Phase 00.2 (PR #28) + post-00.2 cleanup (PR #29) + Phase 00.3+00.4 (PR #30) + Phase 00.2.5 integration (PR #32)
**Scope:** 12-dimension consistency check + Wave-1+ forward-gap check. Read-only.

---

## Top-level verdict: **FLAG**

The cumulative repo state is **internally consistent at the executable layer** — migrations chain, code compiles, tests pass, no orphan stubs, no unsanctioned cross-context model imports. STATUS / HANDOFF / JOURNAL three-way agree on the headline ("Phase 00.2.5 Complete; Phase 00.5 next").

However, **four FLAG-class drifts persist** that the PR #32 in-flight audit already identified as `defer-acceptable`. None block Phase 00.5 from starting, but each represents a documentation-vs-reality mismatch that will silently mislead future agents / auditors if not closed:

1. **ADR-014 amendment is not truthful about Wave-0 RLS posture** (H-DEFER-2 carryover). The amendment claims "Integration tests assert default-deny" but in fact the E2E suite passes only because the testcontainers DSN is a superuser that bypasses `FORCE ROW LEVEL SECURITY`. Register-flow requires DB-owner / `BYPASSRLS` to work. **HIGH** severity for honesty-of-record; **structural** because the fix is either an ADR rewrite or a real `SECURITY DEFINER` shim.
2. **`contracts/billing/schema.sql` still uses `organization_id`** while the implementation already uses `workspace_id` (`billing/0001_credit_transactions_skeleton.py`). Contract-as-authority (ADR-024) is inverted here. **MEDIUM**; non-controversial (skeleton DDL only) but founder should sign off on a contract amendment.
3. **`contracts/rbac/api.yaml` scope_type enum is `[organization, cell]`** while DB CHECK is `('workspace','cell')` and rbac models say `('workspace','cell')`. **MEDIUM**; trivial one-line edit per API spec line (6 occurrences), non-controversial.
4. **OQ-04 "До Phase 00.2" historical phrasing** in `OPEN-QUESTIONS.md:11` + `:66` — Phase 00.2 has been Complete for 1 day. **LOW**; one-cell doc edit, non-controversial in-loop.

Plus 1 LOW-class **stale phase-spec status**: `00.1-repo-cicd.md:3` still says `Status: 🔄 In progress` while PR #25 merged days ago. STATUS.md correctly shows ✅ Complete — three-way drift between STATUS / HANDOFF / phase-spec file.

Plus the 6 `src/_stubs/...` docstring references in production source (L-1 carryover from PR #32 audit) — still unfixed in post-merge state. Pure docstring drift, **LOW**, non-controversial in-loop.

**Recommendation:** safe to start Phase 00.5 immediately, but bundle the 4 docstring/text fixes (#2, #3, #4, plus the Phase 00.1 status flip) into Phase 00.5's exit-ritual commit. Finding #1 (ADR-014 truthfulness) is the only one that genuinely deserves founder review — it touches production security claims.

---

## 12-Dimension Consistency Matrix

| # | Dimension | Status | Summary |
|---|---|---|---|
| 1 | STATUS.md vs `git log main` | **PASS** | `STATUS.md:33-39` lists 00.2.5 + 00.3+00.4 + 00.2 + 00.1 all ✅ Complete with correct PR numbers (#25/#28/#30) and merge dates. `git log main --oneline -50` confirms PRs #25, #26, #27, #28, #29, #30, #32 all merged in that order. No stale "In progress" markers in STATUS.md. |
| 2 | HANDOFF.md scrutiny | **PASS (1 minor caveat)** | `HANDOFF.md:14-19` enumerates all 4+1 phases ✅; "Active blockers" (OQ-04 + OQ-02) match `OPEN-QUESTIONS.md`. "Known caveats" section (`:120-130`) honestly carves out Phase 00.5 router DI wiring, the SSRF TOCTOU in `read_url`, alembic cp1251, A-5/A-8 deferrals, and the `live` marker w/o consumers — all true. Founder action (`:96-118`) lists concrete steps; no broken references. **Caveat**: line 123 cites `billing_service → src.billing.models` as "sanctioned per llm-gateway invariant #7" — verified at `contracts/llm-gateway/README.md:59` (atomic 3-currency write). PASS. |
| 3 | JOURNAL.md append-only + latest entry | **PASS** | Diff against pre-PR-#32 baseline shows pure append; latest entry (`heuristic-rhodes-f7a3ef`, lines 176-189) matches HANDOFF + git log 1:1 — same 6 commits, same scope-correction language ("E2E adjusted to wired surface"), same next-step pointer to Phase 00.5. No duplicate session entries. |
| 4 | Phase-spec Status fields | **FLAG** | `00.2:10` ✅ Complete; `00.3:12` ✅ Complete; `00.4:11` ✅ Complete (with honest carve-out of router DI). **`00.1-repo-cicd.md:3` still says `🔄 In progress (implementation complete на branch claude/amazing-hamilton-8b9d2c, awaiting founder review + merge)`** — stale by 2 days (PR #25 merged 2026-05-17). 00.2.5 has no phase-spec file by design (A-8 deferral, documented at HANDOFF.md:128). |
| 5 | ADR amendments dated 2026-05-19 | **FLAG** | All 5 ADRs (005, 009, 014, 018, 024) carry "Accepted (amendment 2026-05-19, see …)" status lines (heading text varies per ADR — not a literal grep for "Wave 0 implementation decisions" everywhere; that exact phrase appears only in ADR-009). **ADR-014 amendment is NOT TRUTHFUL** about register-flow RLS posture — see Finding H-1 below. ADR-005, 009, 018, 024 amendments check out against code (vector(1024) cols, 3-GUC RLS, RU-currency triad, naming bridge). |
| 6 | PLACEHOLDERS.md vs in-code TBD refs | **PASS** | All 5 new tokens (`TBD_BYOK_MASTER_KEY_B64`, `TBD_YANDEX_CLOUD_KMS_KEY_ID`, `TBD_FX_RATE_USD_TO_RUB_OVERRIDE`, `TBD_YANDEX_SEARCH_API_KEY`, `TBD_BRAVE_SEARCH_API_KEY`) all present in registry (`PLACEHOLDERS.md:94, 95, 102, 103, 104`). In-code refs match: `backend/src/_shared/config.py:98+102` cites `TBD_YANDEX_CLOUD_KMS_KEY_ID`; `backend/tests/llm_gateway/conftest.py:26` references "TBD_* env keys" generically. No orphan TBDs in code. |
| 7 | Contract drift (`contracts/*/schema.sql` vs migrations + code) | **FLAG (HIGH)** | **2 unambiguous contradictions** — see Findings M-1 and M-2 below. iam / multitenancy / llm-gateway / mcp / rbac (schema) / audit / artifacts / tasks / agents / memory all align with migrations. The contradictions: (a) `contracts/billing/schema.sql` still uses `organization_id` while `migrations/billing/0001_credit_transactions_skeleton.py` uses `workspace_id`; (b) `contracts/rbac/api.yaml:64,101,134,150,202,215` enum `[organization, cell]` while `migrations/rbac/0004_role_assignments.py:33` CHECK is `('workspace','cell')` + `src/rbac/models.py:117`. Per ADR-024 contract-authority, contracts should be SoT — but here code is post-rename and contracts are stale. |
| 8 | `backend/src/_stubs/` ghost references | **FLAG (LOW)** | Directory verified deleted (`Test-Path backend/src/_stubs` = False). **6 stale docstring/comment refs remain** in production source: `backend/src/audit/__init__.py:9`, `backend/src/audit/services/__init__.py:6`, `backend/src/audit/services/audit_service.py:6+185`, `backend/src/multitenancy/services/workspace_service.py:5+55`. Identical to PR #32 audit L-1 finding — **not fixed in subsequent commits**. No active import path is broken; pure docstring drift. |
| 9 | Cross-context model imports (ADR-024) | **PASS** | Full `grep "^from src\."` over `backend/src/` confirms only ONE cross-context model import: `backend/src/llm_gateway/services/billing_service.py:26: from src.billing.models import CreditTransaction` — sanctioned via `contracts/llm-gateway/README.md:59` invariant #7 (atomic 3-currency write). Note: `multitenancy/routers/{workspaces,cells}.py` import `from src.iam.middleware` for `get_current_user` — this is a **middleware/dependency import, not a domain model**, so it does not violate ADR-024's domain-model boundary rule. No new violations introduced by Phase 00.2.5. |
| 10 | Migration chain integrity | **PASS** | 23 migration files across 8 branch labels — chain verified by grep over `down_revision`. Heads: `_shared` (→ 0002), `iam` (→ 0006), `multitenancy` (→ 0004), `rbac` (→ 0005), `audit` (→ 0001), `llm_gateway` (→ 0003), `billing` (→ 0001), `mcp` (→ 0001). All 7 non-`_shared` branches root at `_shared_0001_init` or `_shared_0002_current_user_id_helper`. **`ci-backend.yml:118` uses `alembic upgrade heads` (plural)** ✅. The pre-create alembic_version step (`.github/workflows/ci-backend.yml:99-111`) widens version_num to VARCHAR(255) — present ✅. |
| 11 | Test marker consistency | **FLAG (LOW)** | `pyproject.toml:152-156` declares 3 markers (`integration`, `live`, `commit_required`). `--strict-markers` enforced (`:151`). `addopts` deselect: `-m 'not live and not integration'` — works as documented. **`integration` marker**: ≥7 consumers (`tests/integration/test_e2e_auth_flow.py`, `tests/audit/test_audit_partitions.py` ×3, `tests/audit/test_audit_log_append_only.py` ×3, `tests/llm_gateway/test_cost_ledger_sum_match.py`, `test_byok_flow_full.py`). **`commit_required` marker**: 1 consumer (`tests/integration/test_e2e_auth_flow.py:64`). **`live` marker: zero `@pytest.mark.live` consumers** — only referenced in docstrings (`tests/mcp/__init__.py:5`) and one conftest filterstring. Honestly carved out in HANDOFF.md:129. Not blocking, but the marker carry-cost is real until Phase 00.6 adds consumers. |
| 12 | OQ-04 status (3-way) | **FLAG (LOW)** | `STATUS.md:70` "Submitted — dev unblocked. Final РКН confirmation required до prod-launch" ✅. `HANDOFF.md:25` identical phrasing ✅. **`OPEN-QUESTIONS.md:11` still says deadline `До Phase 00.2`** (now historical — Phase 00.2 Complete) **and `:66` still says `Required до Phase 00.2: OQ-04 (РКН-уведомление)`** (same issue). Identical to PR #32 audit L-2/L-3 finding — **not fixed**. Functionally the three sources agree on "submitted", but the deadline phrasing is stuck pre-Phase-00.2. |

**Summary: 7 PASS, 5 FLAG.** The FLAGs cluster around documentation drift (dimensions 4, 5, 7, 8, 12) — substantively the codebase + contracts + ADRs are consistent at the load-bearing level, but the human-readable narrative layer has small but persistent drift that the PR #32 audit already flagged and the post-merge exit ritual did not close.

---

## Wave-1+ Forward-Gap Findings

| ID | Check | Result |
|---|---|---|
| W1-A | `roadmap/wave-1-core-mvp/*` references vs Wave-0 reality | **PASS** — `wave-1-core-mvp/PHASES.md` lists 10 phases (01.1-01.10) at directional level only; no spec files yet. References to functions/columns are abstract (Master-Agent, ЮKassa, RBAC tiers) — none claim Wave-0 deliverables that don't exist. The PHASES.md `:10-22` table maps each Wave-1 phase to relevant ADRs (017, 022, 029, 011, 008, 014, 013, 030) — all 8 ADRs exist in `decisions/`. |
| W1-B | `contracts/billing/` skeleton vs Wave-1 ЮKassa plan | **PASS (with caveat from M-1 above)** — `contracts/billing/README.md:5-7` explicitly marks Wave-0 as SKELETON with Wave 2-3 ownership of full `credit_balances`, `pricing_table`, `tariff_plans`, `subscriptions`, `invoices`. `wave-1-core-mvp/PHASES.md:15` lists phase 01.4 (T-credits + ЮKassa + Trial + Solo + BYOK) — coherent with ADR-008. **Caveat**: the contract drift in M-1 (still `organization_id` in skeleton schema.sql but `workspace_id` in actual implementation) will surface in 01.4 if not fixed first. Recommend fixing M-1 before 01.4 starts. |
| W1-C | ADR-029 (Master-Agent) + `verticals/` + `contracts/role-prompts/` coherence | **PASS** — ADR-029 status `Proposed` (line 3, 2026-05-15). `contracts/role-prompts/` exists with 4 horizontal-team prompts (analyst.md / coordinator.md / researcher.md / writer.md) for `productivity-core`. `verticals/` exists with ONE vertical (`wb-seller/`) carrying prompts + golden-dataset; per ADR-017 revision, WB-Seller moved W0→W2, so its presence is forward-prep not Wave-0 commitment. ADR-029:38-45 cleanly distinguishes horizontal (single-layer, Wave-0) from vertical (two-layer Master-Agent, Wave-1+). Phase 00.5 spec (`:6, :11`) names role-prompts as a first-draft deliverable. **Coherent** — first-draft Wave-0 role-prompts exist; full Master-Agent layer is correctly tagged Wave-1+. |
| W1-D | ADR-030 (Telegram Business API) pre-emptive imports | **PASS** — `grep "telegram\|Telegram" backend/` returns zero matches. No Telegram libs, no `python-telegram-bot`, no Telegram-related env vars in `.env.example` (apart from `TBD_TEAM_TELEGRAM_BOT_TOKEN` + `TBD_TELEGRAM_NOTIFICATION_BOT_TOKEN` which are observability/team placeholders, not Wave-0 code consumers). Phase 01.10 owns `telegram-mcp v0.2`. |

---

## Findings by Severity

### Severity: HIGH

#### H-1 — ADR-014 amendment misrepresents Wave-0 RLS posture (register flow requires DB-owner / `BYPASSRLS`)

- **Source of truth disagreement**: `ADR-014:9` (amendment 2026-05-19) reads: *"3-GUC default-deny RLS posture … Missing GUC → NULL → policy evaluates FALSE → zero rows visible. Integration tests assert default-deny (`tests/multitenancy/test_rls_isolation.py`)."* This implies the production register-flow operates under default-deny.
- **Reality**: `backend/migrations/versions/multitenancy/0001_workspaces.py:74-75` enables `FORCE ROW LEVEL SECURITY` on `workspaces`. Same on `cells` (`0002:80`) and `cell_members` (`0003:70`). The register codepath (`AuthService.register` → `provision_initial_workspace`) does **3 inserts** into these tables, but the only way INSERTs land is if the connection is a superuser (which bypasses `FORCE`) or has `BYPASSRLS`. The E2E test passes only because `tests/conftest.py` uses the testcontainers default DSN — a superuser. The PR #32 architecture audit explicitly flagged this as H-DEFER-2 (`AUDIT-2026-05-19-PR-00-2-5/AUDIT-REPORT.md:128`, `section-04-architecture.md:12`).
- **Code-level evidence**: `tests/multitenancy/test_rls_isolation.py:90` literally says: *"… RLS for superusers even with FORCE ROW LEVEL SECURITY (the dev DB user …)"* — acknowledging the bypass.
- **Why this matters**: Phase 00.5 will wire the multitenancy/LLM/MCP routers under real authenticated traffic. If the runtime continues to use a superuser DSN to satisfy `FORCE ROW LEVEL SECURITY` on the register path, every claim in ADR-014 about Wave-0 production-grade RLS is materially false. The honest amendment should state either (a) Wave-0 uses DB-owner credentials for the register path (≠ default-deny), or (b) we ship a `SECURITY DEFINER` SQL function `multitenancy.bootstrap_first_workspace(user_id, email_localpart)` analogous to `multitenancy.provision_cell_schema(uuid)` and document the pattern in ADR-014.
- **Suggested fix**:
  1. **Architecturally correct path** (mirrors PR #32 audit recommendation): wrap `provision_initial_workspace` in a `SECURITY DEFINER` SQL function or a one-shot bootstrap role (`oriion_provisioner` with `BYPASSRLS`). Either fix is Phase 00.5 prerequisite.
  2. **Honesty-first path**: amend ADR-014 to explicitly state that register-flow operates as DB-owner in Wave-0 (the only DDL-level invariant that holds is `FORCE ROW LEVEL SECURITY` on read paths), and that the SECURITY DEFINER refactor is scheduled for Phase 00.5.
- **Type**: **structural** — needs founder review. Either ship the bootstrap helper (small migration + service refactor) or accept the ADR rewrite as the source-of-truth update.
- **Files to touch**:
  - `.planning/decisions/ADR-014-security.md:9` — rewrite the "3-GUC default-deny RLS posture" bullet to mention the register-flow asymmetry, OR
  - New migration `backend/migrations/versions/multitenancy/0005_bootstrap_workspace_security_definer.py` + `backend/src/multitenancy/services/workspace_service.py::provision_initial_workspace` refactor to call the SQL function instead of doing `Session.add()` directly.

### Severity: MEDIUM

#### M-1 — `contracts/billing/schema.sql` still uses `organization_id`, contradicting implementation

- **Files**:
  - `.planning/contracts/billing/schema.sql:8` (cross-context dep comment): *"multitenancy.organizations (organization_id is billing entity)"*
  - `.planning/contracts/billing/schema.sql:22, 31, 39, 56, 74, 87` — `organization_id uuid NOT NULL`, `FOREIGN KEY (organization_id) REFERENCES multitenancy.organizations(id)`, etc.
- **Contradicts**:
  - `backend/migrations/versions/billing/0001_credit_transactions_skeleton.py:31` — `workspace_id uuid NOT NULL` (real DDL applied to DB)
  - `backend/src/billing/models.py` — `workspace_id` Mapped column
  - `.planning/contracts/billing/README.md:21` already documents the rename in narrative (`workspace_id (was organization_id)`), but the `schema.sql` is the formal contract file per ADR-024 and was never edited.
- **Why this matters**: per ADR-024, `contracts/*/schema.sql` is authoritative. Future agents reading the contract will believe `organization_id` is canonical. The "Naming bridge" note at `contracts/README.md:7-14` partially mitigates by saying narrative refs are bridged, but `schema.sql` is *not* narrative — it's the source-of-truth DDL.
- **Suggested fix**: rewrite `contracts/billing/schema.sql` SKELETON DDL to use `workspace_id` consistently. Lines 22, 31, 39, 56, 74, 87 — 6 simple substitutions. Add a header comment block matching `contracts/multitenancy/schema.sql:6-10` style ("⚠️ NAMING (2026-05-19): renamed `organization_id` → `workspace_id` …").
- **Type**: **non-controversial in-loop** — skeleton DDL only, no live consumer of this file (the real implementation already uses `workspace_id`). Single-file ~15-line edit.

#### M-2 — `contracts/rbac/api.yaml` scope_type enum is `[organization, cell]`, contradicting DB CHECK + ORM

- **Files**:
  - `.planning/contracts/rbac/api.yaml:64, 101, 134, 150, 202, 215` — 6 occurrences of `enum: [organization, cell]`
  - `.planning/contracts/rbac/events.yaml:21, 36, 50` — 3 more occurrences of `enum: [organization, cell]`
- **Contradicts**:
  - `backend/migrations/versions/rbac/0004_role_assignments.py:33`: `scope_type text NOT NULL CHECK (scope_type IN ('workspace','cell'))`
  - `backend/src/rbac/models.py:117`: `"scope_type IN ('workspace','cell')"`
  - `backend/migrations/versions/rbac/0005_seed_built_in_roles.py:64-72` — all seeded permissions use `workspace.*` slugs (`workspace.view`, `workspace.update`, `workspace.delete`)
  - ADR-024 amendment table line 17 explicitly states `rbac.role_assignments.scope_type enum: 'organization' → 'workspace'`
- **Why this matters**: any client generated from `contracts/rbac/api.yaml` would 422 when posting `scope_type: "workspace"` (not in declared enum) and would erroneously include `organization` as a valid value. Both events.yaml + api.yaml diverge from the database.
- **Suggested fix**: replace `[organization, cell]` with `[workspace, cell]` in all 9 lines (api.yaml + events.yaml). Header note: "NOTE (2026-05-19): renamed `organization` → `workspace` per ADR-024 naming bridge."
- **Type**: **non-controversial in-loop** — 9 single-token substitutions across 2 files.

### Severity: LOW

#### L-1 — 6 stale `src/_stubs/...` docstring references in production source

- **Carryover from PR #32 audit (`AUDIT-2026-05-19-PR-00-2-5/section-05-compliance.md` finding L-1).** Not closed in subsequent commits.
- **Files & lines**:
  - `backend/src/multitenancy/services/workspace_service.py:5` — *"(currently wired to the stub in src._stubs.multitenancy). Phase 00.2.5 will swap the import to this module"*
  - `backend/src/multitenancy/services/workspace_service.py:55` — *"Shape matches src._stubs.multitenancy.WorkspaceProvisionResult exactly"*
  - `backend/src/audit/__init__.py:9` — *"src/_stubs/audit.py::emit_audit_event so phase 00.2.5 swaps the stub via"*
  - `backend/src/audit/services/__init__.py:6` — *"src/_stubs/audit.py::emit_audit_event (Phase 00.2.5 swap is a pure"*
  - `backend/src/audit/services/audit_service.py:6` — *"`src/_stubs/audit.py::emit_audit_event`:"*
  - `backend/src/audit/services/audit_service.py:185` — *"Signature is a strict superset of `src._stubs.audit.emit_audit_event` so Phase 00.2.5 swap is a pure import replacement"*
- **Suggested fix**: drop the stub mention or rephrase to past tense. Total diff <30 lines. Bundle into Phase 00.5 exit ritual.
- **Type**: **non-controversial in-loop** — pure docstring edits, no behaviour change.

#### L-2 — OPEN-QUESTIONS.md OQ-04 deadline phrasing is historical ("До Phase 00.2")

- **Carryover from PR #32 audit (finding L-2/L-3).** Not closed.
- **Files**:
  - `.planning/OPEN-QUESTIONS.md:11` column "Дедлайн" reads `До Phase 00.2` — Phase 00.2 has been Complete since 2026-05-18 (PR #28).
  - `.planning/OPEN-QUESTIONS.md:66` reads `**Required до Phase 00.2:** OQ-04 (РКН-уведомление)` — same issue.
- **Suggested fix**:
  - Line 11: change `До Phase 00.2` → `До prod-launch (Phase 00.6+)`.
  - Line 66: change to `**Required до prod-launch:** OQ-04 (final РКН confirmation; dev unblocked)`.
- **Type**: **non-controversial in-loop** — 2 single-cell edits.

#### L-3 — Phase 00.1 phase-spec status field is stale

- **Files**:
  - `.planning/roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:3` reads: *"**Status:** 🔄 In progress (implementation complete на branch `claude/amazing-hamilton-8b9d2c`, awaiting founder review + merge per [STATUS.md](../../../STATUS.md))"*
- **Reality**: PR #25 merged 2026-05-17. STATUS.md correctly shows ✅ Complete. The phase-spec was never flipped during the post-merge exit ritual for 00.1.
- **Suggested fix**: change line 3 to `**Status:** ✅ Complete (merged 2026-05-17 via PR #25, merge-commit b192c6b).` — match the style used in `00.2-custom-jwt-auth.md:10` / `00.3-db-rls-multitenancy.md:12` / `00.4-llm-gateway.md:11`.
- **Type**: **non-controversial in-loop** — single line edit.

#### L-4 — `live` pytest marker has zero consumers

- **Files**:
  - `backend/pyproject.toml:154` — `live` marker declared.
  - `backend/tests/mcp/__init__.py:5` — referenced in a docstring only.
  - **No file under `backend/tests/**/*.py` actually uses `@pytest.mark.live`** (grep over the tree returns no matches).
- **Reality**: HANDOFF.md:129 honestly documents this: *"Live LLM provider tests (`@pytest.mark.live`): marker registered, no tests yet — Phase 00.6 once `TBD_DEEPSEEK_API_KEY` / ... provisioned."*
- **Why FLAG not PASS**: `--strict-markers` (`pyproject.toml:151`) + declared-but-unused marker means CI is paying a tiny carry-cost (no breakage, just dead config). The deletion-or-use principle says either delete the marker until Phase 00.6, or add at least one skeleton test like `tests/llm_gateway/test_live_deepseek.py::test_deepseek_chat_real @pytest.mark.live` that's automatically skipped when the env key is missing.
- **Suggested fix**: defer until Phase 00.6 (founder action: ack the carry-cost or defer-acceptable). Could ship a 1-test skeleton (e.g. `@pytest.mark.live def test_marker_is_actually_wired(): assert True`) to silence the consistency check.
- **Type**: **non-controversial in-loop** — comment on intent or ship a 5-line skeleton test.

### Severity: BLOCK — none.

---

## Verification of PR #32 audit residue

The PR #32 in-flight audit (`AUDIT-2026-05-19-PR-00-2-5/section-05-compliance.md`) identified L-1 / L-2 / L-3 as "defer-acceptable, bundle into Phase 00.5 exit ritual". The exit-ritual commit `a0e0aed` (chore(ci,docs): per-module gates uniform ≥85% + exit ritual for Phase 00.2.5) did NOT bundle the L-class fixes. So those findings carry forward verbatim into this audit (here as L-1 and L-2). H-DEFER-2 was explicitly deferred per the same audit's "Phase 00.5 prerequisite" tag — surfaces here as H-1.

## Wave-0 → Phase 00.5 readiness assessment

- `src/_stubs/` deleted ✅
- `main.py` cleanly scoped to iam routers, sentinel test at `tests/integration/test_e2e_auth_flow.py:425-442` ✅
- Migration chain unbroken, 8 heads ✅, CI uses `alembic upgrade heads` (plural) ✅
- Per-module coverage gates uniform ≥85% ✅
- Sanctioned cross-context import documented ✅
- Wave-1 placeholders coherent with Wave-0 ✅
- No Telegram pre-emption ✅
- ADR-029 + `contracts/role-prompts/` + `verticals/` form coherent first-draft set for Phase 00.5 ✅

**Phase 00.5 can start.** The only finding that touches a Phase 00.5 prerequisite is H-1 (the register-flow RLS posture) — Phase 00.5 wires the LLM/multitenancy/MCP routers under real auth, which surfaces the bypass-RLS issue at runtime if not addressed first.

## Recommended actions

**Before Phase 00.5 starts (founder review required):**
- H-1 — decide: (a) ship `multitenancy.bootstrap_first_workspace(...)` `SECURITY DEFINER` SQL function as Phase 00.5 day-1 work, OR (b) amend ADR-014:9 to honestly state register-flow uses DB-owner credentials in Wave-0.

**Bundle into Phase 00.5 exit ritual (no founder review needed):**
- M-1 — rewrite `contracts/billing/schema.sql` SKELETON to use `workspace_id` (~15-line edit)
- M-2 — flip `[organization, cell]` → `[workspace, cell]` in `contracts/rbac/{api,events}.yaml` (9 substitutions)
- L-1 — drop 6 stale `_stubs/` docstring refs
- L-2 — flip OPEN-QUESTIONS.md OQ-04 phrasing (2 cells)
- L-3 — flip `00.1-repo-cicd.md:3` to ✅ Complete (1 line)
- L-4 — accept carry-cost OR add 5-line `live` marker skeleton test

**No action needed:**
- Migration chain, marker `integration` + `commit_required` consumers, PLACEHOLDERS registry, JOURNAL append-only, STATUS / HANDOFF three-way consistency, Wave-1+ forward gaps, Wave-2/3+ vertical scaffolding.

---

## Evidence index (absolute file paths)

- **STATUS.md** — `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\STATUS.md:33-39, 70`
- **HANDOFF.md** — `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\HANDOFF.md:14-19, 25, 96-130`
- **JOURNAL.md** — `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\JOURNAL.md:155-189`
- **OPEN-QUESTIONS.md** — `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\OPEN-QUESTIONS.md:11, 66`
- **PLACEHOLDERS.md** — `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\PLACEHOLDERS.md:94, 95, 102, 103, 104`
- **Phase-specs**:
  - `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\roadmap\wave-0-foundation\phases\00.1-repo-cicd.md:3` (L-3)
  - `…\phases\00.2-custom-jwt-auth.md:10` ✅
  - `…\phases\00.3-db-rls-multitenancy.md:12` ✅
  - `…\phases\00.4-llm-gateway.md:11` ✅
  - `…\phases\00.5-pydantic-ai-productivity-team.md:5` (Pending, correct)
- **ADRs**:
  - `…\decisions\ADR-014-security.md:9` (H-1)
  - `…\decisions\ADR-009-multitenancy-3-levels.md:5-16`
  - `…\decisions\ADR-024-bounded-context-contracts.md:5-24`
  - `…\decisions\ADR-018-deepseek-primary-llm.md:5` (RU-currency)
  - `…\decisions\ADR-005-pgvector-then-qdrant.md:5` (vector(1024))
  - `…\decisions\ADR-029-master-agent-vertical-templates.md` (Wave-1+ Master-Agent, Proposed)
  - `…\decisions\ADR-030-telegram-business-api.md` (Wave-1 Telegram Business API, Proposed)
- **Contract drift**:
  - `…\.planning\contracts\billing\schema.sql:8, 22, 31, 39, 56, 74, 87` (M-1)
  - `…\.planning\contracts\rbac\api.yaml:64, 101, 134, 150, 202, 215` (M-2)
  - `…\.planning\contracts\rbac\events.yaml:21, 36, 50` (M-2)
  - `…\.planning\contracts\billing\README.md:21` — narrative-only mitigation
  - `…\.planning\contracts\README.md:7-14` — naming bridge note
- **Stale `_stubs/` refs** (L-1):
  - `…\backend\src\multitenancy\services\workspace_service.py:5, 55`
  - `…\backend\src\audit\__init__.py:9`
  - `…\backend\src\audit\services\__init__.py:6`
  - `…\backend\src\audit\services\audit_service.py:6, 185`
- **Cross-context import** (PASS):
  - `…\backend\src\llm_gateway\services\billing_service.py:26` — sanctioned per `contracts/llm-gateway/README.md:59`
- **Migration chain**:
  - `…\backend\migrations\versions\_shared\0001_init.py` (root)
  - `…\backend\migrations\versions\_shared\0002_current_user_id_helper.py` (root-2)
  - All 21 leaf migrations chain via `down_revision` to one of the two roots — verified by grep
- **CI workflow**:
  - `…\.github\workflows\ci-backend.yml:99-111` (pre-create alembic_version), `:118` (`alembic upgrade heads`), `:156-170` (per-module ≥85%)
- **Test markers**:
  - `…\backend\pyproject.toml:151-156` (declarations + addopts)
  - `…\backend\tests\integration\test_e2e_auth_flow.py:64` (commit_required consumer)
  - `…\backend\tests\conftest.py:258, 278` (db_session_committed fixture)
- **RLS bypass evidence** (H-1):
  - `…\backend\migrations\versions\multitenancy\0001_workspaces.py:74-75` (FORCE RLS)
  - `…\backend\tests\multitenancy\test_rls_isolation.py:90` (superuser bypass comment)
  - `…\.planning\_session-context\AUDIT-2026-05-19-PR-00-2-5\AUDIT-REPORT.md:128` (H-DEFER-2 original finding)
  - `…\.planning\_session-context\AUDIT-2026-05-19-PR-00-2-5\section-04-architecture.md:12, 28-35`

---

**End of report.**
