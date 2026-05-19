# Section 04 — Information Architecture & Navigation Audit

> **Auditor:** Technical Writer
> **Date:** 2026-05-19
> **Scope:** Read-only audit of `.planning/` navigation, bootstrap-4 freshness, README hierarchy, cross-links, duplication, agent-handbook accuracy, naming consistency
> **Branch state:** `claude/heuristic-rhodes-f7a3ef` (post-PR-#32 merge into `main`, code-complete pending PR)
> **Worktree:** `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef`

---

## Top-level verdict: **FLAG**

No blockers for a cold-start agent — bootstrap-4 still works, the next-action chain (`README → STATUS → HANDOFF → 00-START-HERE → roadmap/wave-0-foundation/phases/00.5-...md`) resolves correctly and tells a consistent story. **But navigation has measurably degraded.** A new agent will:

1. Hit at least **4 broken markdown links** in the first hour of work (JOURNAL.md×2, agent-handbook/07-AI-TEAM-PIPELINE.md×2)
2. Be misdirected by stale Path C guidance (`agent-handbook/04-HANDOFF.md` still references the deleted `.planning/handoffs/` directory pattern in 6 places — the project now uses a single rolling `HANDOFF.md` file)
3. Find no entry-point to `_session-context/` — 5 audit reports + 1 checklist + 1 stale launch-doc with no README; an agent looking for "what just happened" sees 6 files of similar weight and no ordering
4. See `00.1-repo-cicd.md` Status field reading "🔄 In progress" — directly contradicts STATUS.md ("✅ Complete, merged 2026-05-17 via PR #25")
5. Find no phase-spec at all for Phase 00.2.5 (acknowledged debt A-8 in HANDOFF.md:128 — the work landed without a spec)
6. Walk into the `verticals/wb-seller/golden-dataset/tasks/.gitkeep` file claiming the directory is empty, while it actually contains 30 populated task files

None of this blocks Phase 00.5 from starting. All of it is **structural information-architecture debt** that compounds at each new session.

---

## Cold-start agent walks the bootstrap-4 — smoke test

A new agent with zero memory follows the standard 4-file boot per `00-START-HERE.md:7-14`:

| # | File | Result | Notes |
|---|---|---|---|
| 1 | `.planning/README.md` (3,020 bytes) | **PASS** | Concise, on-message, accurate Path C entry-point (~2KB target, slightly over). Routes correctly to `agent-handbook/00-START-HERE.md`. |
| 2 | `.planning/STATUS.md` (12,833 bytes) | **PASS** | Accurately describes Phase 00.2.5 as "Code-complete on `claude/heuristic-rhodes-f7a3ef` (2026-05-19, second pass same day)". Cross-refs to audit reports + POST-MERGE-AUDIT-2026-05-19.md resolve. |
| 3 | `.planning/HANDOFF.md` (11,095 bytes) | **PASS-with-caveats** | Current, names the next worktree command + Phase 00.5 brief. Section "Exit ritual completed (this session)" still has `[ ] PR opened — final step of this session` unchecked. Internally consistent with STATUS. |
| 4 | `.planning/agent-handbook/00-START-HERE.md` (7,771 bytes) | **PASS** | Concise, accurate workflow. No drift detected. |

**Verdict on the bootstrap:** the agent can successfully orient + start Phase 00.5. The bootstrap-4 itself is fresh.

**However**, the agent's *second* read (the phase-spec or `agent-handbook/04-HANDOFF.md` or `07-AI-TEAM-PIPELINE.md`) hits a broken link or stale directive within minutes. The bootstrap is fine; the surrounding navigation is the problem.

---

## Findings by severity + in-loop-or-structural

> Legend: **HIGH** = misdirects agent into wrong action / contradicts STATUS · **MEDIUM** = wastes time but recoverable · **LOW** = polish · **In-loop** = doc-only fix in this audit cycle · **Structural** = needs reorg/rename/archive across files

### HIGH — Structural

#### H-1. `agent-handbook/04-HANDOFF.md` describes a directory pattern (`.planning/handoffs/YYYY-MM-DD-<slug>.md`) that no longer exists

**Evidence:** Grep shows 6 references in `04-HANDOFF.md` to a non-existent `.planning/handoffs/` directory (lines 22, 115, 135, 160, 174 + plural-form line in 174). One more reference in `05-PR-WORKFLOW.md:171` (PR template `Handoff:` field).

**Actual practice (per JOURNAL.md + HANDOFF.md + 05-PR-WORKFLOW.md:18-37):** single rolling `HANDOFF.md` at `.planning/` root, overwritten each session, history via `git log HANDOFF.md`. The `handoffs/` directory was abolished during the 2026-05-14 Path C cleanup (per JOURNAL.md:25).

**Impact:** A new agent reading `04-HANDOFF.md` end-to-end will believe they should create `.planning/handoffs/2026-05-19-foo.md` — directly contradicts the actual `Exit ritual` in `05-PR-WORKFLOW.md:18-37`.

**Fix (in-loop):** rewrite `04-HANDOFF.md` to align with single-file-rolling pattern. Update `05-PR-WORKFLOW.md:171` to remove `.planning/handoffs/` from the PR template.

---

#### H-2. `00.1-repo-cicd.md` Status field directly contradicts STATUS.md

**Evidence:** `roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:3` reads `Status: 🔄 In progress (implementation complete на branch claude/amazing-hamilton-8b9d2c, awaiting founder review + merge per STATUS.md)`. STATUS.md:39 + JOURNAL.md:73-85 confirm PR #25 merged 2026-05-17 via merge-commit `b192c6b`.

**Impact:** A cold agent reading the phase-spec directly will not know Phase 00.1 is done. Phase 00.2/00.3/00.4/00.7 Status fields are correctly maintained — only 00.1 is stale. The 2026-05-17 memory-curator session (JOURNAL.md:73-85) updated STATUS.md but missed the per-phase-spec Status field.

**Fix (in-loop):** update `00.1-repo-cicd.md:3` to `Status: ✅ Complete (merged 2026-05-17 via PR #25)`.

---

#### H-3. Phase 00.2.5 has no phase-spec file in `roadmap/wave-0-foundation/phases/`

**Evidence:** Glob check on `roadmap/wave-0-foundation/phases/` shows 00.1, 00.2, 00.3, 00.4, 00.5, 00.6, 00.7 — **no 00.2.5**. PHASES.md index (line 4-11) doesn't list it. HANDOFF.md:128 self-acknowledges this as deferred item A-8: *"A-8 (00.2.5 phase-spec file): not authored; this HANDOFF + the launch checklist + post-merge audit serve as the historical record for the phase."*

**Impact:** Three months from now, a new agent retrospectively studying Wave-0 work will find no canonical record of 00.2.5 in `roadmap/`. The substitute documents (PHASE-00-2-5-LAUNCH-CHECKLIST.md, POST-MERGE-AUDIT-2026-05-19.md, AUDIT-2026-05-19-PR-00-2-5/AUDIT-REPORT.md) live in `_session-context/`, which is meant for transient session artifacts, not authoritative phase records.

**Fix (structural):** author `roadmap/wave-0-foundation/phases/00.2.5-integration.md` as a Status-only retrospective spec — short (≤2KB), pointing readers to `_session-context/AUDIT-2026-05-19-PR-00-2-5/AUDIT-REPORT.md` for full record. Add to PHASES.md index. Allows the agent reading PHASES.md to find a complete chronology.

---

#### H-4. `_session-context/` has no README or index

**Evidence:** Directory contains 3 top-level files + 3 subdirectories — 7 distinct artifacts of mixed purpose (1 architect-PR plan, 1 launch checklist, 1 post-merge consistency audit, 2 multi-section audit reports, 1 in-progress audit). No README. The 4 audit-related entries differ subtly by name (`AUDIT-2026-05-19`, `AUDIT-2026-05-19-PR-00-2-5`, `AUDIT-2026-05-19-PRE-PHASE-05`, `POST-MERGE-AUDIT-2026-05-19.md`).

**Impact:** A new agent investigating "what audits ran and where" must Read all 6 entries to determine ordering and scope. The naming pattern is consistent-but-ambiguous: `AUDIT-2026-05-19/` audits PR #30; `AUDIT-2026-05-19-PR-00-2-5/` audits PR #32; `POST-MERGE-AUDIT-2026-05-19.md` audits the result of PR #30. None of this is discoverable without reading.

**Fix (in-loop):** add `_session-context/README.md` (~2KB) — chronological index of session artifacts with one-line description + PR cross-ref each. Establish convention: "files here are session-bound; consult `roadmap/` and `decisions/` for canonical state."

---

### HIGH — In-loop

#### H-5. Broken markdown links to non-existent ADR filename `ADR-025-gate-format.md`

**Evidence:**
- `agent-handbook/07-AI-TEAM-PIPELINE.md:3` — `[ADR-025](../decisions/ADR-025-gate-format.md)`
- `agent-handbook/07-AI-TEAM-PIPELINE.md:254` — `[ADR-025](../decisions/ADR-025-gate-format.md)`

The actual file is `ADR-025-acceptance-gate-format.md` (verified by Glob + `decisions/README.md:50` + `ADR-028-policies-registry.md:28/100/121` which all use the correct filename).

**Impact:** Click-through breaks. A new agent following the link gets a "file not found" and may believe ADR-025 doesn't exist.

**Fix (in-loop):** rename both link targets to `ADR-025-acceptance-gate-format.md`.

---

#### H-6. Broken relative-root links in JOURNAL.md

**Evidence:** JOURNAL.md is at `.planning/JOURNAL.md`. Lines 48 + 50 use `(.planning/decisions/...)` and `(.planning/STATUS.md)` — these resolve relative to JOURNAL.md's own dir, i.e. to `.planning/.planning/...` which doesn't exist. Correct form would be `(./decisions/...)`.

**Impact:** The two ADR-029/ADR-030 links in the 2026-05-15 journal entry are broken. Agents grepping JOURNAL.md for decision lineage hit dead links.

**Fix (in-loop):** rewrite the two broken-form links in JOURNAL.md:48 + JOURNAL.md:50.

---

### MEDIUM — Structural

#### M-1. Naming inconsistency: branch convention `feature/<slug>` documented, but `claude/<slug>` used everywhere

**Evidence:**
- `_meta/conventions.md:42`: *"Branching | `feature/<phase-id>-<slug>` для фаз"*
- `agent-handbook/05-PR-WORKFLOW.md:45,298,299`: *"Phase task | `feature/<phase-id>-<slug>` (e.g. `feature/00.4-llm-gateway`)"* + tier-table examples
- Reality (`git log --oneline -10` + Grep showed 33 occurrences across 20 files): every branch in 2026-05-14 → 2026-05-19 history is `claude/<adjective-noun-hash>` (e.g. `claude/heuristic-rhodes-f7a3ef`, `claude/cool-bell-0c74ba`, `claude/dazzling-satoshi-0a293d`, `claude/amazing-hamilton-8b9d2c`).

**Impact:** Every PR has violated the documented branch naming. Either the convention is wrong or the practice is wrong — convention should be updated to reflect actual `claude/<slug>` (it's a Claude-Code-generated branch name pattern).

**Fix (in-loop):** update `_meta/conventions.md:42` + `05-PR-WORKFLOW.md:45` to document `claude/<adjective-noun-hash>` as the actual pattern + keep `feature/*` / `fix/*` / `chore/*` / etc. as semantic synonyms when a human starts a branch. Or document that `claude/*` branches are equivalent to `feature/*` for AI-led sessions.

---

#### M-2. Legacy `organization_id` references in 3 contract `schema.sql` files outside of explicit rename comments

**Evidence:** Grep finds `organization_id` in 10 files. After cross-referencing the 2026-05-19 rename:
- `contracts/mcp/schema.sql` (6 hits — active column + comments)
- `contracts/billing/schema.sql` (8 hits — skeleton, explicitly deferred to Wave 2 per `billing/README.md:21`)
- `contracts/rbac/schema.sql` (4 hits — commented-out seed SQL)
- `contracts/llm-gateway/schema.sql:8` — rename-banner comment only (OK)
- `contracts/llm-gateway/events.yaml` — rename-banner only (OK)
- `contracts/multitenancy/events.yaml` — rename-banner only (OK)
- `contracts/{artifacts,memory}/README.md` — banner in README.md (OK)

The `contracts/README.md:7-14` "Naming bridge (2026-05-19)" paragraph explicitly acknowledges this debt and tells readers to treat legacy `organization` as synonym for `workspace`. Already documented as M-4 in `HANDOFF.md:126` — *"M-4 (legacy organization_id in contract comments): 6+ files with comment-only references; deferred follow-up docs PR or Phase 00.6."*

**Impact:** Already a known + tracked debt. Not a navigation issue per se, but a new agent reading `contracts/mcp/schema.sql` sees `organization_id` and may write code against it. The rbac/billing cases are commented-out seed data — strictly safe — but mcp/schema.sql appears to have active references.

**Fix (structural, deferred per existing HANDOFF.md tracking):** Phase 00.6 docs PR.

---

#### M-3. Stale `.gitkeep` content in `verticals/wb-seller/golden-dataset/tasks/.gitkeep`

**Evidence:** The .gitkeep file (651 bytes) reads *"Status: empty placeholder. Population scheduled for Milestone C Phase 00.5."* — but the directory now contains 30 populated task files (001-listing-* through 030-ranking-*).

**Impact:** Cosmetic; the directory is not actually empty. The `.gitkeep` should be deleted (it's no longer needed once the directory has real files), or its content updated to reflect that golden-dataset is materialized.

**Fix (in-loop):** delete `verticals/wb-seller/golden-dataset/tasks/.gitkeep`.

---

### MEDIUM — In-loop

#### M-4. Missing README entry-points in 7 sub-directories (Path C convention violations)

**Evidence:** Per `00-START-HERE.md:40` — *"При заходе в `.planning/X/` сначала читай `X/README.md`"*. Verified missing:

| Directory | Has README? |
|---|---|
| `.planning/contracts/role-prompts/` | **MISSING** (4 prompt files inside, no index) |
| `.planning/gates/_schema/` | **MISSING** (1 schema file, no context) |
| `.planning/_session-context/` | **MISSING** (see H-4) |
| `.planning/_session-context/AUDIT-2026-05-19/` | **MISSING** |
| `.planning/_session-context/AUDIT-2026-05-19-PR-00-2-5/` | **MISSING** |
| `.planning/verticals/wb-seller/golden-dataset/adversarial/` | **MISSING** (5 task files) |
| `.planning/verticals/wb-seller/golden-dataset/tasks/` | **MISSING** (30 task files + stale .gitkeep) |
| `.planning/verticals/wb-seller/prompts/` | **MISSING** (3 prompt files) |

**Impact:** Agents entering these dirs land with no compass — must Read N files to orient. For role-prompts/ specifically, an agent doesn't know whether the 4 files are draft / locked / first-pass / hardened.

**Fix (in-loop):** add 8 README.md files, each ≤1KB, describing purpose + file list + status. `AUDIT-2026-05-19-*/README.md` files are subsumed by H-4's `_session-context/README.md` (don't need separate per-audit READMEs; the parent index is sufficient).

---

#### M-5. Duplication: `_meta/conventions.md:50-71` (Tier-based review + CI gates) duplicated in `05-PR-WORKFLOW.md:177-199`

**Evidence:** Both files document the same tier-table and CI gates. `conventions.md:50-53` even says *"Source of truth: ADR-027 §tier-table … Не дублируем tier-table инлайн."* and then `05-PR-WORKFLOW.md:177-179` repeats the disclaimer.

**Impact:** Three sources of truth for tier policy (ADR-027 + conventions.md + 05-PR-WORKFLOW.md), all currently consistent but at risk of drift. The duplication exists despite both files acknowledging it shouldn't.

**Fix (structural):** truncate `05-PR-WORKFLOW.md:177-199` to a one-line cross-ref `See ADR-027 §tier-table.` Same for CI gates — point to `conventions.md` as canonical. Net deletion ~25 lines.

---

#### M-6. Bootstrap-4 file sizes vs Path C target

**Evidence:** Per `JOURNAL.md:25-26`, the Path C reorg targeted "concise" entry-points (~2KB each). Actual sizes today:

| File | Size | Path C target | Verdict |
|---|---|---|---|
| `.planning/README.md` | 3,020 B | ≤2KB | **MARGINAL** — 50% over but still scannable |
| `agent-handbook/00-START-HERE.md` | 7,771 B | "polished" workflow | **OVER** — ~4× original concise target, but the file IS the workflow (acceptable scope creep) |
| `STATUS.md` | 12,833 B | rolling state | **HIGH** — getting heavy. Has historical context (Phase 00.1 detail at line 39, Phase 00.2/00.3/00.4 detail at lines 35-41) that could move to JOURNAL.md once superseded |
| `HANDOFF.md` | 11,095 B | last-session snapshot | **HIGH** — also growing. The "Known caveats / tracked for Phase 00.5 + 00.6" block (lines 120-130) is long-lived debt tracking, not session-snapshot material |

**Impact:** A new agent reading bootstrap-4 today consumes ~35KB — vs ~15KB Path C target. Still within the "typical session budget: 15-30 KB" stated in `00-START-HERE.md:53`, but at the upper bound.

**Fix (structural, not urgent):** introduce `.planning/_debt.md` (or move the cross-phase tracked caveats to OPEN-QUESTIONS.md) so HANDOFF.md can shrink to "what just happened in *this* session". STATUS.md historical phase detail moves to the JOURNAL entries it duplicates.

---

### LOW — Structural

#### L-1. Naming inconsistency: kebab-case vs UPPER_SNAKE_CASE in `_session-context/`

**Evidence:** `_session-context/` mixes naming styles:
- `2026-05-17-architect-pr-3-way-parallel.md` (kebab)
- `PHASE-00-2-5-LAUNCH-CHECKLIST.md` (UPPER-DASH)
- `POST-MERGE-AUDIT-2026-05-19.md` (UPPER-DASH)
- `AUDIT-2026-05-19/` (UPPER-DASH dir)
- `AUDIT-2026-05-19-PR-00-2-5/` (UPPER-DASH dir, with phase-id embedded)
- `AUDIT-2026-05-19-PRE-PHASE-05/` (UPPER-DASH dir, with adjective)

**Impact:** Cosmetic. Sortability is not broken (date-prefixed entries cluster correctly). But the convention has drifted: 2026-05-17 entry chose date-prefix kebab; 2026-05-19 entries chose UPPER-DASH no-date for documents and UPPER-DASH+date for dirs.

**Fix (defer):** when adding `_session-context/README.md` (H-4), set convention going forward (e.g. *"all new session artifacts: `YYYY-MM-DD-<slug>.md` or `YYYY-MM-DD-<slug>/`"*). Don't retroactively rename — git history continuity matters.

---

#### L-2. Naming inconsistency: bounded contexts (`llm-gateway` vs `llm_gateway`)

**Evidence:**
- `contracts/llm-gateway/` (kebab) — docs/contract dir
- `backend/src/llm_gateway/` (snake) — Python package
- `backend/migrations/versions/llm_gateway/` (snake) — Alembic
- `backend/tests/llm_gateway/` (snake) — Python

This is **correct + intentional** — Python identifier rules forbid kebabs; markdown-dir convention uses kebabs. No fix needed; documenting here so the next agent doesn't try to "normalize" them.

---

#### L-3. `wb-seller/REVIEW-CHECKLIST.md` is an outlier vs sibling `verticals/README.md` "structure" table

**Evidence:** `verticals/README.md:21-32` documents per-vertical structure with `REVIEW-CHECKLIST.md` as one of 7 standard files. WB-Seller is the only materialized vertical, so this is the prototype — but the file naming case (UPPER-DASH) clashes with sibling files at the same level (kebab-case `domain-glossary.md`, `workflow-dag.md`, `changelog.md`, `kpis.md`).

**Impact:** Minor. When future verticals are scaffolded (Wave 1+), the inconsistency will compound.

**Fix (defer to Wave 1 vertical scaffolding):** decide whether REVIEW-CHECKLIST stays UPPER-DASH (matches `ui/REVIEW-CHECKLIST.md`) or moves to kebab (`review-checklist.md`). Pick one. The `ui/` directory uses the UPPER form, so consistency tilts that way.

---

## Concrete reorganization plan

> Every item below is a single proposed file action with a one-line justification. Severity in parentheses. **In-loop** = doc-edit only, ≤1hr. **Structural** = needs cross-file coordination.

### EDIT (in-loop, do before PR opens for Phase 00.2.5)

1. `agent-handbook/04-HANDOFF.md` — rewrite all 6 references to `.planning/handoffs/YYYY-MM-DD-<slug>.md` to point to single-file rolling `HANDOFF.md` pattern (H-1).
2. `agent-handbook/05-PR-WORKFLOW.md:171` — remove `Handoff: .planning/handoffs/...` line from PR template; replace with `Handoff: HANDOFF.md refresh + JOURNAL.md +1 (per Exit ritual)` (H-1).
3. `agent-handbook/07-AI-TEAM-PIPELINE.md:3` + `:254` — fix `ADR-025-gate-format.md` → `ADR-025-acceptance-gate-format.md` (H-5).
4. `roadmap/wave-0-foundation/phases/00.1-repo-cicd.md:3` — change Status from `🔄 In progress` to `✅ Complete (merged 2026-05-17 via PR #25)` (H-2).
5. `JOURNAL.md:48` + `:50` — fix `(.planning/...)` links to `(./decisions/...)` and `(./STATUS.md)` (H-6).
6. `_meta/conventions.md:42` + `agent-handbook/05-PR-WORKFLOW.md:45,298,299` — document `claude/<adjective-noun-hash>` branch pattern as canonical for AI-led sessions; keep `feature/*` as semantic synonym (M-1).
7. `JOURNAL.md:16` + `agent-handbook/05-PR-WORKFLOW.md:31` — either create `dev-log/archive/` skeleton or strike the archive sentence (currently references a directory that doesn't exist). Recommend: change wording to "archive when needed; create `dev-log/archive/` on first overflow" — defers creation until justified.

### CREATE (in-loop, ≤2KB each)

8. `.planning/_session-context/README.md` (~1.5 KB) — chronological index of session artifacts; sets convention: this dir is for transient session work, not canonical state (H-4).
9. `.planning/contracts/role-prompts/README.md` (~1 KB) — index of 4 horizontal-team prompts (coordinator/researcher/writer/analyst); status (first-draft per Phase 00.5); cross-ref to ADR-010 (SemVer) + ADR-029 (Master-Agent layer note: horizontal stays single-layer) (M-4).
10. `.planning/gates/_schema/README.md` (~0.5 KB) — what `gate.schema.json` is; how it's used by `gates/wave-N-to-N+1.md` files (M-4).
11. `.planning/verticals/wb-seller/prompts/README.md` (~1 KB) — note these are W0-legacy targeting; full Wave-2 alignment per `wb-seller/README.md` revision banner (M-4).
12. `.planning/verticals/wb-seller/golden-dataset/adversarial/README.md` (~0.5 KB) — what adversarial probes test; pass-rate target (100% per ADR-026 §5) (M-4).
13. `.planning/verticals/wb-seller/golden-dataset/tasks/README.md` (~0.5 KB) — 30 tasks materialized; mapping to 5 primary task-types × 6 variants; frontmatter contract reference (M-4).
14. `roadmap/wave-0-foundation/phases/00.2.5-integration.md` (~1.5 KB) — retrospective phase-spec for the integration phase that happened without a spec. Points to `_session-context/AUDIT-2026-05-19-PR-00-2-5/AUDIT-REPORT.md` as full record. Add to `wave-0-foundation/PHASES.md:5-11` index (H-3).

### DELETE (in-loop)

15. `.planning/verticals/wb-seller/golden-dataset/tasks/.gitkeep` — directory has 30 files, .gitkeep no longer serves its purpose, and its content claims the directory is empty when it isn't (M-3).

### ARCHIVE (structural, defer to a separate cleanup PR — not urgent for Phase 00.5)

16. Move `_session-context/2026-05-17-architect-pr-3-way-parallel.md` → `_session-context/archive/2026-05-17-architect-pr-3-way-parallel.md` — superseded by STATUS.md "Architect-PR (2026-05-17)" section + JOURNAL.md:87+ entries. Keep history accessible.
17. Move `_session-context/PHASE-00-2-5-LAUNCH-CHECKLIST.md` → `_session-context/archive/2026-05-19-phase-00-2-5-launch-checklist.md` — Phase 00.2.5 is now code-complete; checklist is historical (and the rename normalizes to date-prefix kebab per L-1 convention).
18. Move `_session-context/POST-MERGE-AUDIT-2026-05-19.md` → `_session-context/archive/2026-05-19-post-merge-audit-pr-30.md` — audited PR is merged; report is historical record. Rename clarifies what PR it audited.
19. Move `_session-context/AUDIT-2026-05-19/` → `_session-context/archive/2026-05-19-audit-pr-30/` — audited PR merged; rename clarifies subject.

Active items remain in `_session-context/`: `AUDIT-2026-05-19-PR-00-2-5/` (this PR's audit, not yet merged), `AUDIT-2026-05-19-PRE-PHASE-05/` (this audit, in progress). After PR #32 merges, those move to archive too.

### MERGE (structural, ≤30 line net delete)

20. `agent-handbook/05-PR-WORKFLOW.md:177-199` (Tier-based review + CI gates blocks) — replace with one-line cross-ref to `_meta/conventions.md` and ADR-027 (M-5).

### RENAME (defer, low value)

21. Optional — `verticals/wb-seller/REVIEW-CHECKLIST.md` → align case with sibling kebab files. Defer; revisit when Wave-1 vertical scaffolding starts (L-3).

---

## Path C compliance scorecard

| Entry-point | Target | Actual | Verdict |
|---|---|---|---|
| `.planning/README.md` | "what is this project", ≤2 KB | 3.0 KB | Slightly over; structure is right (no recap of details, just index + Stack + entry-point pointer); acceptable |
| `agent-handbook/00-START-HERE.md` | concise workflow | 7.8 KB | Larger than original target but the file *is* the workflow; well-organized; no fluff |
| `_meta/README.md` | ≤2 KB index | 1.8 KB | PASS |
| `contracts/README.md` | ≤2 KB | 1.9 KB | PASS |
| `roadmap/README.md` | ≤2 KB | 5.2 KB | OVER — but justified (cross-Wave dep graph is content-heavy); acceptable |
| `risks/README.md` | ≤2 KB | 0.9 KB | PASS |
| `tools/README.md` | ≤2 KB | 0.9 KB | PASS |
| `ui/README.md` | ≤2 KB | 1.4 KB | PASS |
| `verticals/README.md` | ≤2 KB | 3.0 KB | OVER — wave-distribution table is content-heavy; acceptable |
| `decisions/README.md` | ≤2 KB | 5.0 KB | OVER — but it's an ADR catalog, content scales with ADR count; acceptable |

Overall Path C compliance: **PASS** — no entry-point file is dangerously bloated. Where they exceed target, the overage is structural content (tables, dep graphs, ADR catalog), not prose drift.

---

## Discoverability of audit reports — `_session-context/` taxonomy proposed

Current layout (alphabetical, no grouping):

```
_session-context/
├── 2026-05-17-architect-pr-3-way-parallel.md         (kebab, dated)
├── AUDIT-2026-05-19/                                  (UPPER-DASH dir)
├── AUDIT-2026-05-19-PR-00-2-5/                        (UPPER-DASH dir)
├── AUDIT-2026-05-19-PRE-PHASE-05/                     (UPPER-DASH dir)
├── PHASE-00-2-5-LAUNCH-CHECKLIST.md                   (UPPER-DASH)
└── POST-MERGE-AUDIT-2026-05-19.md                     (UPPER-DASH)
```

Proposed layout post-cleanup:

```
_session-context/
├── README.md                                          (new — see action #8)
├── AUDIT-2026-05-19-PR-00-2-5/                        (active — PR #32 not merged yet)
├── AUDIT-2026-05-19-PRE-PHASE-05/                     (active — this audit)
└── archive/
    ├── 2026-05-17-architect-pr-3-way-parallel.md
    ├── 2026-05-19-audit-pr-30/                        (was AUDIT-2026-05-19/)
    ├── 2026-05-19-phase-00-2-5-launch-checklist.md
    └── 2026-05-19-post-merge-audit-pr-30.md
```

Convention going forward (documented in `_session-context/README.md`):
- New session artifacts: `YYYY-MM-DD-<slug>.md` (single file) or `YYYY-MM-DD-<slug>/` (multi-section)
- Move to `archive/` once the underlying PR merges or the work moves to canonical state (`roadmap/`, `decisions/`)
- This directory is **never** the source of truth for active state — STATUS / HANDOFF / JOURNAL are

---

## PROJECT.md vs reality — sanity check

PROJECT.md describes:
- ✅ Dual messaging (universal + vertical) — preserved in STATUS, roadmap/README, verticals/README
- ✅ Wave-0 anchor = horizontal `productivity-core` — preserved everywhere
- ✅ Solo founder + 11 AI agents per ADR-023 — preserved
- ✅ 6-wave roadmap with target dates — preserved in roadmap/README + STATUS

PROJECT.md line 55 (Current phase) is **out-of-date**:
> *"Phase 00.3 (multitenancy + audit + RLS) + Phase 00.4 (LLM gateway + MCP) — 🔄 In parallel … Integration via separate Phase 00.2.5 session after 00.3 + 00.4 merge."*

Reality (per STATUS.md, HANDOFF.md): both phases merged via PR #30; Phase 00.2.5 is code-complete and awaiting PR. PROJECT.md missed an update at the 2026-05-19 merge.

**Fix (in-loop, action #22):** update PROJECT.md:55 to reflect 00.2/00.3/00.4 ✅ Complete + 00.2.5 code-complete + 00.5 pending — mirror the STATUS.md wording. Note: PROJECT.md was designed to be relatively static (USP / team / waves), so the "Current phase" pointer should probably be a one-line "See STATUS.md for current state" instead of repeating phase detail.

**Better fix (M-6 follow-up):** delete the "Текущая phase" section from PROJECT.md entirely; leave only the link to STATUS.md. PROJECT.md becomes a true static project-overview document; STATUS.md stays the single source of truth for dynamic state.

---

## Agent-handbook completeness check

All 8 expected files present (`00-START-HERE.md` through `07-AI-TEAM-PIPELINE.md`). Cross-link integrity inside handbook itself: PASS (00 links to 01-07 correctly, no broken refs internally). External refs from handbook:
- to `../README.md`, `../STATUS.md`, `../HANDOFF.md`, `../JOURNAL.md` — all resolve
- to `../decisions/ADR-NNN-*.md` — mostly resolve except H-5 (ADR-025)
- to `../decisions/ADR-028-policies-registry.md#policies-canonical-home` — anchor exists, verified
- to `../../.claude/agents/` (relative depth-2) — outside `.planning/`; verified directory exists in repo root

Rules in `00-START-HERE.md` that have been violated repeatedly (suggesting the rule is wrong/unclear):
- **"PR без Exit ritual"** anti-pattern (line 89): has been honored every session — rule is correct + working.
- **"feature/<phase-id>" branch convention**: violated every session — see M-1; the rule is wrong.
- **"`.planning/handoffs/` directory"**: violated every session since 2026-05-14 (Path C cleanup) — see H-1; the rule is wrong.

---

## Naming consistency drift summary

| Dimension | Convention | Drift detected | Verdict |
|---|---|---|---|
| Phase ID | `00.1`, `00.2`, ..., `00.2.5` (dot-separated) | Single style across PHASES.md, STATUS.md, HANDOFF.md, JOURNAL.md, audit files | PASS |
| Bounded-context dir (docs) | kebab-case (`llm-gateway`, `role-prompts`) | Consistent in `contracts/` | PASS |
| Bounded-context module (Python) | snake_case (`llm_gateway`, `multitenancy`) | Consistent in `backend/src/` | PASS (intentional, see L-2) |
| Branch name | `feature/<slug>` per docs vs `claude/<slug>` in practice | 100% practice violates docs | FAIL — fix docs (M-1) |
| Session-context file name | mixed: kebab-dated, UPPER-DASH-dated, UPPER-DASH-only | Within one directory | FAIL — set convention in README (L-1) |
| ADR file name | `ADR-NNN-kebab-slug.md` | One typo: `ADR-025-gate-format.md` (wrong) in handbook (H-5) | FAIL — fix |

---

## Codebase navigation — quick check

`backend/src/` mirror:
```
backend/src/
├── _shared/        (Base, db, utils)
├── audit/
├── billing/
├── iam/
├── llm_gateway/
├── mcp/
├── multitenancy/
└── rbac/
```

vs `contracts/` (10 bounded contexts: agents/, artifacts/, billing/, iam/, llm-gateway/, mcp/, memory/, multitenancy/, rbac/, tasks/, role-prompts/).

**Gap:** `contracts/` has 11 dirs; `backend/src/` has 8 implementation packages. Missing real code (per HANDOFF.md context): `agents`, `artifacts`, `memory`, `tasks` — all planned for Wave 1+. The audit's question of "what's the natural landing page for a new code-reader" is answered by `contracts/README.md` (lists the 10 contexts with one-line descriptions). However, **there is no `backend/README.md`** — Read confirmed `backend/README.md MISSING`. A new agent walking into `backend/` to read code has only the root README.md (which is project-level Quickstart, encoding-mangled UTF-8 / Cyrillic on Windows but readable). Recommendation: add `backend/README.md` describing the 8 packages + how they map to `contracts/`. **Out of scope for this audit** (audit is `.planning/`-bounded), but flag for next info-arch pass.

---

## Closing — what a cold-start agent's first hour looks like after fixes

After applying all in-loop fixes (~2 hours of doc-only edits + 8 new short READMEs):

1. **Bootstrap-4 read** — 4 files, ~35 KB, success (unchanged from today).
2. **Click first ADR-025 ref in handbook** — resolves (was: broken).
3. **Click any link in JOURNAL.md** — resolves (was: 2 broken).
4. **Read `04-HANDOFF.md` to learn handoff protocol** — sees single-file rolling pattern (was: 6 references to non-existent dir).
5. **Read `00.1-repo-cicd.md`** — sees ✅ Complete (was: 🔄 In progress, contradicting STATUS).
6. **Walk into `_session-context/`** — sees README index pointing to "what's active vs what's archived" (was: 6 ambiguous files).
7. **Walk into `verticals/wb-seller/prompts/`** — sees README explaining these are W0-legacy targeting (was: 3 files with no context).
8. **Plan their PR branch name** — sees docs match practice `claude/<slug>` (was: docs said `feature/<slug>`, every PR used `claude/<slug>`).

Total agent-time saved per future session, conservative estimate: **20-40 minutes**. Over the next ~6 weeks of Wave-0 → Wave-1 work, that's 5-15 hours of avoided confusion — well worth the 2-hour doc-edit investment.

---

## Files referenced in this report

- `C:\Users\KUklonskiy\Obsidian\TGKB\Projects\TEAMLY_RU\.planning\.claude\worktrees\heuristic-rhodes-f7a3ef\.planning\README.md`
- `...\.planning\STATUS.md`
- `...\.planning\HANDOFF.md`
- `...\.planning\JOURNAL.md`
- `...\.planning\PROJECT.md`
- `...\.planning\OPEN-QUESTIONS.md`
- `...\.planning\PLACEHOLDERS.md`
- `...\.planning\agent-handbook\00-START-HERE.md` (PASS)
- `...\.planning\agent-handbook\04-HANDOFF.md` (H-1 fix target)
- `...\.planning\agent-handbook\05-PR-WORKFLOW.md` (H-1, M-1, M-5 fix targets)
- `...\.planning\agent-handbook\07-AI-TEAM-PIPELINE.md` (H-5 fix target)
- `...\.planning\roadmap\wave-0-foundation\PHASES.md` (H-3 add 00.2.5 row)
- `...\.planning\roadmap\wave-0-foundation\phases\00.1-repo-cicd.md` (H-2 fix target)
- `...\.planning\_session-context\` (H-4, action #8 add README; actions #16-19 archive)
- `...\.planning\contracts\role-prompts\` (M-4, action #9 add README)
- `...\.planning\gates\_schema\` (M-4, action #10 add README)
- `...\.planning\verticals\wb-seller\` (M-3 delete .gitkeep, M-4 add 3 READMEs)
- `...\.planning\_meta\conventions.md` (M-1 fix target)
