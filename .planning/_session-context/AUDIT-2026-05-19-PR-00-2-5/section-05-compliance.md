# Section 05 — Compliance Audit (Phase 00.2.5 integration PR)

**Auditor:** Compliance Auditor (sub-agent)
**Date:** 2026-05-19
**Branch:** `claude/heuristic-rhodes-f7a3ef`
**Commits ahead of main:** 6 (post-PR-#30 squash)
**Audit pattern:** re-run of the 12-dimension consistency audit applied to PR #30 (`POST-MERGE-AUDIT-2026-05-19.md`).

## Verdict

**PASS (FLAG-class doc drift only).** No blockers, no must-fix-before-merge code findings. All 4 M-class findings from the PR #30 post-merge audit are resolved (M-1/M-2/M-3 via cherry-pick `03d06a4`, M-4 actually shipped — `contracts/mcp/schema.sql` and `contracts/rbac/schema.sql` did change, plus a top-level "Naming bridge" note was added to `contracts/README.md`). The 6-commit history is internally consistent; STATUS / HANDOFF / JOURNAL / phase-specs all converge on the same end-state ("Phase 00.2.5 code-complete; Phase 00.5 next"); the LLM-router wiring gap is honestly documented in HANDOFF + the E2E test + `main.py` itself; the new `commit_required` pytest marker is registered, declared in `pyproject.toml`, and actually used by the new E2E suite.

The remaining drift items are 6 stale docstring/source-comment references to the deleted `src/_stubs/` paths (L-1) and the OPEN-QUESTIONS.md "До Phase 00.2" deadline phrasing which is now historical (L-2). Neither blocks merge; both are 1-line follow-ups that can land in Phase 00.5's exit-ritual commit.

## Consistency matrix (12 dimensions)

| # | Dimension | Status | Finding |
|---|---|---|---|
| 1 | STATUS.md vs git log | PASS | `STATUS.md:33-35` enumerates 6 atomic commits + cherry-pick of `03d06a4`; matches `git log main..HEAD --oneline` exactly. Wording "Code-complete pending PR" aligns with branch-still-unmerged state. Phase 00.2 / 00.3 / 00.4 entries (`STATUS.md:35-37`) all flipped to ✅ Complete. |
| 2 | HANDOFF.md vs commits/tooling | PASS | `HANDOFF.md:51-61` lists 6 commits + 1 exit-ritual commit; matches git history. `HANDOFF.md:66-72` build/test claims ("366 unit / 21 integration / ruff/format/mypy/bandit clean / 6-context coverage ≥85%") are consistent with `.github/workflows/ci-backend.yml:156-170` per-module gate config. Last-updated header `HANDOFF.md:7-9` correctly reflects the worktree branch. |
| 3 | JOURNAL.md append-only + latest entry | PASS | `git diff main..HEAD -- .planning/JOURNAL.md` shows pure append: 2 new entries added (`cool-bell-0c74ba` + `heuristic-rhodes-f7a3ef`) starting at line 155, zero modifications to prior entries. The latest entry (`heuristic-rhodes-f7a3ef`) is consistent with HANDOFF — same 6 commits, same scope-correction language ("E2E adjusted to wired surface — full LLM matrix-via-HTTP is Phase 00.5"), same next-step pointer to Phase 00.5. |
| 4 | Phase-spec Status fields | PASS | All three phase-specs flipped to ✅ Complete: `00.2-custom-jwt-auth.md:10` ("Complete (2026-05-18 via PR #28; integration into multitenancy/audit landed via Phase 00.2.5)"), `00.3-db-rls-multitenancy.md:12` ("Complete (2026-05-19 via PR #30, combined with Phase 00.4; integration into iam landed via Phase 00.2.5)"), `00.4-llm-gateway.md:11` ("Complete (2026-05-19 via PR #30, combined with Phase 00.3; router DI wiring + live provider tests remain Phase 00.5 / 00.6 work)"). The 00.4 entry honestly carves out the router-DI gap. |
| 5 | ADR amendments | PASS | No new ADRs touched by Phase 00.2.5 commits (`git log main..HEAD -- .planning/decisions/` returns only the pre-existing `f5d3e56` from PR #30 era). No new amendment is needed — Phase 00.2.5 is pure integration (no new architectural decisions). ADR-024 deferred amendment for the sanctioned `billing_service → billing.models` cross-context import remains tracked as A-12 / debt (HANDOFF.md:123). |
| 6 | PLACEHOLDERS.md TBD coverage | PASS | `git diff main..HEAD -- .planning/PLACEHOLDERS.md` shows no change. Phase 00.2.5 introduced zero new env vars / placeholder tokens — the integration phase consumed existing config (BYOK_MASTER_KEY_B64, TEST_DATABASE_URL) without adding anything new. Test only references `TEST_DATABASE_URL` which is documented in `.env.example` (no TBD needed — it's a dev-only DSN). |
| 7 | Contract drift (anything stale) | FLAG | All 22 contracts that still mention legacy `organization` are now properly bridged via the top-level `contracts/README.md:7-14` "Naming bridge" note added by `03d06a4`. The remaining narrative occurrences (`rbac/schema.sql:90` cross-context FK comment, `multitenancy/README.md:14`, `artifacts/README.md`, `memory/README.md`, `billing/events.yaml` description) are bridged — not code drift. No FLAG-level contract gap surfaces. Note: `contracts/mcp/schema.sql` and `contracts/rbac/schema.sql` skeleton DDL **did** receive concrete edits in `03d06a4` (12-line and 10-line diffs respectively), refuting the post-merge audit's worry that they would be skipped. |
| 8 | `backend/src/_stubs/` inventory | PASS | Directory fully deleted (verified: `Test-Path` returns False for `_stubs/`, `_stubs/__init__.py`, `_stubs/audit.py`, `_stubs/multitenancy.py`). Zero remaining production imports (`Grep "from src\._stubs"` over `backend/` returns 0 results). The 2 obsolete tests (`test_emit_audit_event_stub_compat.py`, `tests/iam/unit/test_stubs.py`) are deleted. **L-1 leftover:** 6 docstring/source-comment references to the deleted paths (see Findings). |
| 9 | Cross-context model imports | PASS | `Grep "from src\.billing"` over `backend/src/` returns only the single known sanctioned import: `src/llm_gateway/services/billing_service.py:26: from src.billing.models import CreditTransaction`. Unchanged from PR #30 baseline. Sanctioned via HANDOFF.md:123 + invariant-7 atomic 3-currency write. No new cross-context model imports introduced by Phase 00.2.5. |
| 10 | Migration chain integrity | PASS | `git log main..HEAD --oneline -- backend/migrations/` confirms zero new migration commits since main. Only diff under `migrations/` is a trivial ruff-format whitespace shuffle in `_shared/0001_init.py:135-138` (line-break inside `op.execute(...)`, no DDL change). All 8 migration heads (`_shared`, `iam`, `multitenancy`, `rbac`, `audit`, `llm_gateway`, `billing`, `mcp`) chain unchanged; CI invokes `alembic upgrade heads` (plural) per `.github/workflows/ci-backend.yml:118`. |
| 11 | Test marker consistency | PASS | New `commit_required` marker declared in `pyproject.toml:155` and actually used by the new E2E suite (`tests/integration/test_e2e_auth_flow.py:64: pytestmark = [pytest.mark.integration, pytest.mark.commit_required]`). Conftest implements the carve-out (`tests/conftest.py:258, 278` — `db_session_committed` fixture with TRUNCATE cleanup for COMMIT-trigger tests). Pre-existing `integration` + `live` markers unchanged. `--strict-markers` still active per `pyproject.toml:151`. |
| 12 | OQ-04 status | PASS | Three-way consistent: `OPEN-QUESTIONS.md:11` ("До Phase 00.2", historical now), `STATUS.md:70` ("**Submitted** — dev unblocked. Final РКН confirmation required до prod-launch; dev/test работает на mock-данных, реальная обработка ПДн запрещена до closure"), `HANDOFF.md:25` (identical phrasing minus the last clause). All three documents agree on submission status. **L-2 advisory:** OPEN-QUESTIONS.md still phrases the deadline as "До Phase 00.2" which is now in the past; consider rewriting to "До prod-launch" for forward-honesty, but not blocking. |

**Summary:** 10 PASS, 2 FLAG. Both FLAGs (dimensions 7 and 12) are documentation-only and already partially mitigated by the cherry-picked `contracts/README.md` naming-bridge note.

## Verification of PR #30 must-fix-before-merge items (M-1..M-4)

All four resolved.

| ID | Original finding | Resolution mechanism | Verified |
|---|---|---|---|
| M-1 | `HANDOFF.md` brief should call out `provision_initial_workspace` signature change | Cherry-picked `03d06a4` updated HANDOFF; further superseded by the full HANDOFF rewrite landed in `a0e0aed` (exit ritual). Current HANDOFF describes the call-site refactor in `HANDOFF.md:33-47` (grill table Q6 "naive `cmd.email.split("@", 1)[0]`") + `JOURNAL.md` entry. | PASS |
| M-2 | Stale "00.3-audit-subagent will swap" comment at `cell_service.py:18` | Cherry-pick of `03d06a4` (1-line diff to `backend/src/multitenancy/services/cell_service.py`); the swap then happened for real in `f264fc6`. Current state: `cell_service.py:18` reads `from src.audit.services.audit_service import emit_audit_event` (no stale comment). | PASS |
| M-3 | Phase-spec 00.4 references non-existent `_stubs/rls.py` | Cherry-pick of `03d06a4` (3-line diff to `00.4-llm-gateway.md:6`); current `00.4-llm-gateway.md:6` reads: *"`backend/src/_stubs/audit.py::emit_audit_event(...)` — writes to structlog only; no DB write. (NOTE 2026-05-19: `_stubs/rls.py` was originally planned but never created — `set_tenant_context` real impl in `backend/src/_shared/db/rls.py` shipped in the same combined PR. 00.4 code already imports from the real module.)"* | PASS |
| M-4 | Contract SQL comments still reference legacy `organization` term in 6+ files | Cherry-pick of `03d06a4` did real work: `contracts/mcp/schema.sql` (12-line diff, all `organization_id` → `workspace_id` in skeleton DDL + comments), `contracts/rbac/schema.sql` (10-line diff, commented-out seed slugs `('workspace.view'...)` instead of `('organization.view'...)`), `contracts/README.md` (9 new lines: top-level "Naming bridge" note covering narrative refs in `artifacts/README.md`, `memory/README.md`, `billing/events.yaml`). | PASS |

**Confirmation of launch-checklist concern (M-4 cleanup completeness):** The post-merge audit explicitly worried whether `contracts/mcp/schema.sql` and `contracts/rbac/schema.sql` actually changed via `03d06a4` or were skipped. `git show 03d06a4 --stat` confirms 8 files changed including both — full file list: `HANDOFF.md` (14 lines), `_session-context/PHASE-00-2-5-LAUNCH-CHECKLIST.md` (212 new), `_session-context/POST-MERGE-AUDIT-2026-05-19.md` (205 new), `contracts/README.md` (9 lines), `contracts/mcp/schema.sql` (12 lines), `contracts/rbac/schema.sql` (10 lines), `phases/00.4-llm-gateway.md` (3 lines), `backend/src/multitenancy/services/cell_service.py` (2 lines). Cleanup is complete — no skipped files.

## Verification of Phase 00.5 LLM router wiring gap documentation

The launch-checklist Section 5 originally specified a full register → DeepSeek + Yandex + GigaChat + embeddings + BYOK matrix E2E through HTTP. Phase 00.2.5 deviated from this because `main.py` only wires the iam routers. The gap is honestly documented in **three** places:

1. **HANDOFF.md:79-81** — entire "Scope correction vs launch checklist Section 5" paragraph explaining `main.py` doesn't include LLM routers, calling out that the matrix-through-HTTP is Phase 00.5 work, and pointing at the existing service-tier coverage (`test_byok_flow_full.py` + `test_cost_ledger_sum_match.py`).
2. **HANDOFF.md:121** — "Known caveats / tracked for Phase 00.5 + 00.6" first bullet: *"LLM/multitenancy/MCP router DI wiring: Phase 00.5 owns assembly of provider instances + main.py inclusion. Routers exist as code; handlers return 501 today."*
3. **`backend/tests/integration/test_e2e_auth_flow.py`** — module docstring at `:15-21` repeats the same scope correction. Sentinel test `test_llm_chat_endpoint_is_not_yet_wired` at `:425-442` asserts `404` on `/api/v1/llm/chat` and contains the failure message *"If this flipped to 501 (or 200), Phase 00.5 has wired the LLM router..."* — making the gap impossible to lose: when Phase 00.5 lands, this test will start failing visibly, triggering the test owner to re-write or delete it.
4. **`backend/src/main.py:4-6`** itself documents the current wiring scope: *"Phase 00.2: wires iam routers (auth + me) under /api/v1 prefix + RFC 7807 problem+json exception handler for IamError."* — no claim of LLM coverage.

The gap is **fully documented** at four levels (planning doc, caveats list, test docstring, sentinel-test, source code). No drift.

## Other findings

### Severity: L (low — non-blocking docstring drift)

#### L-1 — Stale `src/_stubs/...` references in 5 source files

The stubs directory was deleted but 6 docstring/comment references to it remain in production source. Each is a backward-looking reference explaining historical context, not an active code path — but a future reader searching for `_stubs/` will land on these and momentarily wonder if they need to chase the path.

| File | Line | Current text | Suggested fix |
|---|---|---|---|
| `backend/src/multitenancy/services/workspace_service.py` | 4-5 | `(currently wired to the stub in src._stubs.multitenancy). Phase 00.2.5 will swap the import to this module — return type WorkspaceProvisionResult is identical.` | Replace with: `(consumed by iam.auth_service.register; the Wave-0 stub was deleted in Phase 00.2.5).` |
| `backend/src/multitenancy/services/workspace_service.py` | 55 | `Shape matches src._stubs.multitenancy.WorkspaceProvisionResult exactly so the 00.2.5 import-swap is invisible to callers.` | Drop the second clause: `Returned by provision_initial_workspace; consumed by AuthService.register.` |
| `backend/src/audit/__init__.py` | 9 | `src/_stubs/audit.py::emit_audit_event so phase 00.2.5 swaps the stub via` | Drop the `_stubs` mention; explain the current symbol path only. |
| `backend/src/audit/services/__init__.py` | 6 | `src/_stubs/audit.py::emit_audit_event (Phase 00.2.5 swap is a pure` | Same — drop stub mention. |
| `backend/src/audit/services/audit_service.py` | 4-30 | Long docstring header literally titled "Signature contract" comparing stub vs real with full stub signature reproduced. | Either delete the comparison block entirely (it served its purpose) or replace with a 1-line note: *"Signature was designed as a strict superset of the deleted Phase 00.2 stub at src/_stubs/audit.py (removed 2026-05-19); historical reference preserved in PR #30 post-merge audit."* |
| `backend/src/audit/services/audit_service.py` | 185-186 | `Signature is a strict superset of src._stubs.audit.emit_audit_event so Phase 00.2.5 swap is a pure import replacement.` | Drop entirely or rephrase to past tense. |

**Suggested fix:** single follow-up commit `docs: drop stale _stubs references from post-00.2.5 source docstrings`. Total diff <30 lines. Defer to Phase 00.5 exit ritual or land standalone — does not block merge.

#### L-2 — OPEN-QUESTIONS.md OQ-04 deadline phrasing is historical

`OPEN-QUESTIONS.md:11` says deadline is "До Phase 00.2" which is now in the past (Phase 00.2 + 00.2.5 are both Complete). STATUS.md and HANDOFF.md correctly say "Final РКН confirmation required до prod-launch". For internal-consistency, the OPEN-QUESTIONS row should be updated to the same wording (currently the only three-way-consistency edge case where one source still uses the old phasing).

**Suggested fix:** edit `OPEN-QUESTIONS.md:11` column 4 from `До Phase 00.2` to `До prod-launch (Phase 00.6+)`. Single-cell edit. Defer-acceptable.

#### L-3 — `OPEN-QUESTIONS.md:66` references Phase 00.2 as the OQ-04 gate

`OPEN-QUESTIONS.md:66: **Required до Phase 00.2:** OQ-04 (РКН-уведомление)` — same issue as L-2; should also be updated for forward-honesty. Bundled with L-2 fix.

### Severity: M / H — none

No medium- or high-severity findings.

### Severity: BLOCK — none

## Phase 00.5 readiness assessment

The branch is in a **clean handoff state** for Phase 00.5. Specifically:

1. **`src/_stubs/` no longer exists** — Phase 00.5 will not accidentally re-import deleted symbols.
2. **`main.py` is clearly scoped** to iam routers; sentinel test `test_llm_chat_endpoint_is_not_yet_wired` will fire when Phase 00.5 wires LLM/multitenancy/MCP routers, forcing the test owner to update the assertion.
3. **`AuthService.__init__` now takes `session: AsyncSession`** (per `f264fc6` swap commit) — Phase 00.5 router-DI work will not need to refactor the auth service shape again.
4. **testcontainers fixture is in place** (`tests/conftest.py::pg_container`) — Phase 00.5's planned E2E LLM-matrix tests can reuse `pgvector/pgvector:pg16` directly via `@pytest.mark.integration + commit_required`.
5. **Per-module coverage gates are uniform ≥85%** (`.github/workflows/ci-backend.yml:165-170`) — Phase 00.5 cannot accidentally regress any of the 6 bounded contexts without CI flagging.
6. **Sanctioned cross-context import (`billing_service → billing.models`)** is documented at three places (HANDOFF.md:123, post-merge-audit M-4 deferred → A-12, ADR-024 amendment scheduled) — Phase 00.5 will not surprise-encounter it.
7. **No phase-spec drift remaining** — 00.2 / 00.3 / 00.4 all read ✅ Complete with accurate post-Phase-00.2.5 notes.

The only outstanding items are the 3 L-class doc-hygiene findings above and 11 A-class advisories carried over from the PR #30 audit (A-5 through A-12), explicitly tracked in `POST-MERGE-AUDIT-2026-05-19.md:177-188` and HANDOFF.md "Known caveats".

## Recommended actions

**Before merge (optional, none blocking):**

1. Bundle L-1 + L-2 + L-3 into a single follow-up `docs: drop stale _stubs references + OQ-04 historical phrasing` commit on this branch. <30 line diff total. Adds 0 risk.

**As-is merge is safe.** All 12 consistency dimensions pass functionally; the 3 L-class items are pure docstring/historical-phrasing drift with no behavioural impact.

**For Phase 00.5 exit ritual:**

- Bundle the L-1 docstring cleanup with the LLM-router wiring commit (natural opportunity — both touch `audit_service.py` adjacent areas).
- Flip `test_llm_chat_endpoint_is_not_yet_wired` to assert the wired contract.
- Update `OPEN-QUESTIONS.md` OQ-04 row when prod-launch milestone is firm.

## Evidence index (file paths)

- Audit basis: `.planning/_session-context/POST-MERGE-AUDIT-2026-05-19.md` (PR #30 post-merge findings — all 4 M-class resolved)
- Launch checklist: `.planning/_session-context/PHASE-00-2-5-LAUNCH-CHECKLIST.md` (the 12-section scope spec for this PR)
- STATUS: `.planning/STATUS.md:33-37` (Phase 00.2.5 entry + 00.2/00.3/00.4 complete)
- HANDOFF: `.planning/HANDOFF.md` (full file — rewritten in `a0e0aed`)
- JOURNAL: `.planning/JOURNAL.md:155-208` (2 new entries, append-only confirmed via `git diff main..HEAD`)
- Phase specs: `.planning/roadmap/wave-0-foundation/phases/00.{2,3,4}-*.md` (Status line on line 10/12/11 respectively)
- Contract bridge: `.planning/contracts/README.md:7-14` (Naming bridge note added by `03d06a4`)
- Cherry-pick commit: `03d06a4` (8 files; all M-1..M-4 fixes verified present)
- Stub deletion commit: `f264fc6` (deletes `backend/src/_stubs/{__init__,audit,multitenancy}.py` + 2 tests; rewires 4 call-sites; adds `session` to `AuthService.__init__`)
- E2E suite: `backend/tests/integration/test_e2e_auth_flow.py:15-46` (scope-correction docstring) + `:425-442` (Phase 00.5 sentinel test)
- main.py: `backend/src/main.py:4-6` (documents current router scope) + `:52-53` (only iam routers wired)
- pyproject markers: `backend/pyproject.toml:152-156` (`commit_required` declared) + `tests/conftest.py:258, 278` (fixture) + `tests/integration/test_e2e_auth_flow.py:64` (applied)
- CI gate config: `.github/workflows/ci-backend.yml:156-170` (uniform ≥85% per-module)
- Sanctioned cross-context import: `backend/src/llm_gateway/services/billing_service.py:26` (unchanged from PR #30)
- Stale stub docstring refs (L-1): `backend/src/multitenancy/services/workspace_service.py:4-5, 55` + `backend/src/audit/__init__.py:9` + `backend/src/audit/services/__init__.py:6` + `backend/src/audit/services/audit_service.py:4-30, 185-186`
- OQ-04 historical phrasing (L-2/L-3): `.planning/OPEN-QUESTIONS.md:11, 66`
