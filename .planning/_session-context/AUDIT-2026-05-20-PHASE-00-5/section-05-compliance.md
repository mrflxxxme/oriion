# Section 05 — Compliance Audit (cross-phase, post-implementation)

- **Auditor:** ComplianceAuditor
- **Date:** 2026-05-21
- **Worktree:** `.planning/.claude/worktrees/phase-00-5b-runtime`
- **Branch:** `claude/phase-00-5b-runtime` (commits `7c00b43..6cd8808`, 6 atomic)
- **Phase under audit:** 00.5b runtime — cross-phase compliance posture vs ADR-014 / -024 / -029 / -010 / -017 / -018 + FZ-152 / РКН invariants + Wave-1 readiness signals
- **Predecessor phase:** 00.5a (RLS-bootstrap honesty-pass, merged 2026-05-20)

---

## Verdict

**PASS WITH DEFERRED FINDINGS — Wave-0 anchor compliance posture HONEST + extensible.**

ADR-014 §1 honesty-pass landed in Phase 00.5a exactly per Option-A wording — register-time bootstrap delegated to SECURITY DEFINER `multitenancy.bootstrap_first_workspace(...)`, `oriion_app`-role test fixture surface in CI, and the «default-deny FORCE-RLS» claim is now factually accurate. Compliance H-1 from the pre-Phase-05 audit is genuinely closed (not just claimed-closed).

ADR-024 §3 amendment for Architecture H3 (`llm_gateway.billing_service → billing.models.CreditTransaction`) **already exists in the worktree** as the «Sanctioned cross-context exceptions» section landed 2026-05-19, and Phase 00.5b Commits 2-7 introduced **zero new cross-context model imports**. The HANDOFF claim that Commit 8 needs a «3-line amendment» is **stale wording**: the amendment is already there with a 2026-05-21 re-confirmation paragraph. Commit 8 needs at most a status-line touch-up — NOT a structural ADR edit. See F-CMP-N2.

Role-prompt status discipline is correct (`status: Proposed`, `version: 0.1.0`, `quality_bar: first-draft (hardening pass at Phase 01.1 retro)` on all 4 files) and AC14 hardening backlog is honestly pinned in `gates/wave-0-to-1.md:37`.

CloudEvents emit pattern is conformant for both new bounded contexts. Pip-audit ignore registry remains 1 entry (PYSEC-2025-183) — Phase 00.5b added no new ignores despite adding 30+ pydantic-ai + opentelemetry transitive deps.

The Wave-0→Wave-1 Master-Agent extensibility check **PASSES** — the schema supports composition without breaking changes, with **one MEDIUM caveat** about the `role_category` CHECK constraint membership that needs a migration before Wave-1 phase 01.1 can land Master archetypes. See F-CMP-M1.

Phase 00.5b is on track for merge before 2026-06-09; confidence delta from pre-Phase-05 ~65% → ~78%. See §«Wave-0 deadline confidence delta».

---

## ADR landing matrix

| ADR | Required change | Status | File:line | Pass / Defer |
|---|---|---|---|---|
| **ADR-014 §1 (honesty-pass)** | Replace original «3-GUC default-deny RLS posture» bullet with truthful statement of the SECURITY DEFINER bootstrap exception | ✅ **Landed 00.5a** | `decisions/ADR-014-security.md:15-58` (amendment dated 2026-05-20) | **PASS** — Option-A wording present verbatim («Register-time bootstrap exception … delegated to the SECURITY DEFINER SQL function `multitenancy.bootstrap_first_workspace`») + CI assertion of failure mode + ADR-009 §5 cross-ref |
| **ADR-014 pip-audit registry** | Carry `PYSEC-2025-183` entry forward, add new ignores if Phase 00.5b adds any | ✅ **Carried** | `decisions/ADR-014-security.md:5-13` + `.github/workflows/ci-backend.yml:206-220` | **PASS** — registry table + CI `--ignore-vuln PYSEC-2025-183` + Phase 00.5b added zero new ignores |
| **ADR-024 §3 (sanctioned cross-context exceptions)** | Legitimize `llm_gateway → billing.models.CreditTransaction` per Architecture H3 | ✅ **Already landed (2026-05-19) + re-confirmed (2026-05-21)** | `decisions/ADR-024-bounded-context-contracts.md:109-159` | **PASS-WITH-CAVEAT** — the canonical amendment text already exists; HANDOFF wording is stale. Commit 8 only needs a status-line refresh, not a 3-line section add. See F-CMP-N2 |
| **ADR-024 §2 (canonical naming)** | No new cross-context model imports introduced by Phase 00.5b | ✅ **Verified** | `git grep ^from src\.[a-z_]*\.models backend/src/` returns 25 lines, all within-context except the pre-sanctioned `billing.models.CreditTransaction` in `llm_gateway/services/billing_service.py:26` | **PASS** |
| **ADR-029 (Master-Agent vertical-templates)** | Wave 1+ delivery; Phase 00.5b must NOT break Wave-1 composability | ⏳ **Wave 1 deliverable** | `agents/models.py:48-49` (role_category CHECK) | **PASS-WITH-CAVEAT** — `role_category` CHECK constraint is `('coordinator','researcher','writer','analyzer','validator','communicator')`. Master archetype needs a 7th literal (`master` or `vertical_master`). Trivial migration in Phase 01.1, but called out as F-CMP-M1 to avoid a Wave-1 surprise |
| **ADR-010 (role-prompt versioning)** | 4 role-prompts ship with valid frontmatter at first-draft semver | ✅ **Landed Commit 5** | `contracts/role-prompts/{coordinator,researcher,writer,analyst}.md:1-13` | **PASS** — frontmatter consistent across 4 files: `status: Proposed`, `version: 0.1.0`, `quality_bar: first-draft (hardening pass at Phase 01.1 retro)`. `role_prompt_loader.py:74-89` enforces mechanical checks (required keys + 9-section monotonicity) per T5 |
| **ADR-017 revision (2026-05-15 horizontal anchor)** | `productivity-core` ships as Wave 0 horizontal anchor, NOT a vertical | ✅ **Landed Commit 5** | `decisions/ADR-017-vertical-templates.md:3,15` + `agents/seed_data/productivity_core_v1.py:25-26` (`VERTICAL_SLUG = "horizontal"`, `PRESET_SLUG = "productivity-core"`) | **PASS** — DDL natural-key `(vertical_slug, slug, prompt_version)` cleanly distinguishes horizontal preset from future `marketing-agency`, `wb-seller`, etc. slugs |
| **ADR-018 (DeepSeek primary + RU triad)** | DeepSeek-first config in adapters | ✅ **Landed Commit 2/4** | `_shared/config.py:113-150` (`deepseek_api_key` + `yandex_iam_token` + `gigachat_auth_key` SecretStr fields) + `agents/seed_data/productivity_core_v1.py:32-62` (`deepseek-reasoner` + `deepseek-chat`) | **PASS** |
| **FZ-152 audit-trail invariants** | CloudEvents emitted for every new INSERT to `agents.agent_instances`, `tasks.tasks`, `tasks.task_steps` | ✅ **Landed Commit 5/6** | `agents/events.py:13-57` + `tasks/events.py:12-101` | **PASS** — `_SOURCE = "oriion://contexts/agents"` and `"oriion://contexts/tasks"` per ADR-024 §3 CloudEvents 1.0 envelope. Emit pattern wraps `_shared.cloudevents.emit_cloudevent` (structlog backend Wave 0 → Redis Streams XADD Wave 1+, transport-stable API per ADR-014 §4) |

---

## Findings

### F-CMP-H1 (informational HIGH — was a HIGH before verification; verified down to NONE)

**Category:** ADR-014 §1 honesty-pass actual landing
**Status verified:** **CLOSED** — the original concern (HANDOFF.md claims «✅ Shipped 00.5a» — verify wording actually present) is fully discharged.

`decisions/ADR-014-security.md:23-58` carries the Option-A wording **exactly** as required by the founder brief:
- «3-GUC default-deny RLS posture **with documented bootstrap exception**» (amendment header line 23)
- «Register-time bootstrap exception … delegated to the SECURITY DEFINER SQL function `multitenancy.bootstrap_first_workspace(p_user_id, p_workspace_slug, p_display_name)` introduced in migration `multitenancy/0005_bootstrap_first_workspace_function.py`» (lines 31-43)
- «CI assertion of production failure mode. `backend/tests/integration/test_e2e_auth_flow.py::override_get_db` issues `SET LOCAL ROLE oriion_app`» (lines 51-55) — i.e. the `oriion_app`-role fixture is real and pins the production posture
- Migration file `backend/migrations/versions/multitenancy/0005_bootstrap_first_workspace_function.py:1-44` confirms the function carries the SECURITY DEFINER attribute with EXECUTE granted to `oriion_app` (audit closures listed in docstring: H1 + H2 + Compliance H-1)

**No further action.** This is the cleanest cross-phase honesty-pass landing observed in the audit — STATUS.md, HANDOFF.md, ADR-014, ADR-009, the migration, and the test fixture all align.

---

### F-CMP-N2 (LOW — documentation freshness)

**Category:** ADR-024 §3 amendment — HANDOFF wording is stale
**Severity:** LOW (cosmetic / process-hygiene)
**Confidence:** HIGH

The HANDOFF.md narrative (lines 50, 83, 124) states «ADR-024 §3 amendment NOT YET LANDED» and characterises Commit 8 as adding a «3-line "Sanctioned cross-context model imports" amendment legitimising `llm_gateway.billing_service → billing.models.CreditTransaction`». This is **factually stale**:

1. `decisions/ADR-024-bounded-context-contracts.md:109-159` already contains the full «Sanctioned cross-context exceptions (amendment 2026-05-19)» section with the canonical Exception #1 entry, justification, audit history, and Wave-1 follow-up candidates.
2. The 2026-05-21 re-confirmation paragraph at lines 129-137 explicitly references the Phase 00.5b 5-agent audit and verifies «Commits 2-7 router wiring re-touched the import surface … without introducing any new cross-context model imports» — i.e. the amendment **already covers Phase 00.5b's import surface**.
3. The «Status» line 3 was bumped to «re-confirmed 2026-05-21 by Phase 00.5b audit».

**What Commit 8 actually needs:** at most a 1-line touch — either a status-line re-stamp from «re-confirmed 2026-05-21» to «re-confirmed at Phase 00.5b merge» OR adding the merged-PR-number to the audit-history paragraph. **NOT a 3-line section addition.** The work is already done.

**Remediation:**
1. Rewrite HANDOFF.md lines 50, 83, 124 to read «ADR-024 §3 amendment **already landed 2026-05-19; Phase 00.5b re-confirmation 2026-05-21**. Commit 8 only needs the Exit-ritual STATUS flip + JOURNAL entry — no ADR structural edit needed.»
2. Update STATUS.md line 50 («Commit 8 (ADR-024 §3 amendment for sanctioned … per E2 — still NOT YET LANDED») to reflect reality.
3. Keep Commit 8 in the plan as the Exit ritual + PR-open commit, but drop the «ADR amendment» framing.

**Why this matters for compliance:** an auditor reading HANDOFF.md «not yet landed» while ADR-024 says «already landed + re-confirmed» creates a contradiction that erodes trust in the planning artifacts. This is exactly the kind of stale-claim drift the Phase 00.5a honesty-pass was designed to prevent.

**Effort:** 5 minutes — three line-edits in HANDOFF.md + one in STATUS.md.

---

### F-CMP-M1 (MEDIUM — Wave-1 readiness)

**Category:** ADR-029 Master-Agent extensibility — `role_category` CHECK constraint
**Severity:** MEDIUM (no Wave-0 impact; trivial fix in Phase 01.1)
**Confidence:** HIGH

The current `agents.agent_archetypes.role_category` CHECK constraint enumerates 6 categories:

```sql
-- contracts/agents/schema.sql:30
role_category text NOT NULL CHECK (role_category IN
  ('coordinator','researcher','writer','analyzer','validator','communicator'))
```

```python
# backend/src/agents/models.py:48-49 (mirrors schema.sql)
"role_category IN ('coordinator','researcher','writer','analyzer',"
"'validator','communicator')"
```

ADR-029 §«Implementation outline» introduces a `MasterAgent` archetype (vertical CEO) sitting **above** the Coordinator. It is structurally a new role category — neither a coordinator (no `delegate_task` directly to leaves; it delegates to Coordinator), nor any of the 5 existing leaves. To insert a Master archetype row in Phase 01.1 the CHECK constraint **must be widened** to add a 7th literal — most natural: `'master'` or `'vertical_master'`.

This is **not a Wave-0 blocker** — productivity-core uses only the 6 existing categories. But it is **a Wave-1 land-mine** if Phase 01.1's first commit attempts to seed a Marketing Master archetype before widening the CHECK.

**Remediation:**
1. Add to Phase 01.1 backlog: «First Alembic migration MUST be `agents/0004_role_category_chk_add_master.py` — `ALTER TABLE agents.agent_archetypes DROP CONSTRAINT agent_archetypes_role_category_chk` + re-add with `'master'` added to the IN clause. Mirror in `src/agents/models.py`.» Effort: 30 minutes.
2. Optional: capture this as a forward-looking comment in `contracts/agents/schema.sql:30` («Wave 1+ adds `'master'` per ADR-029») so the next implementer doesn't trip on it.

**Why MEDIUM not LOW:** if Phase 01.1 misses this and ships a Marketing Master archetype without the migration, the seed insert will fail at boot with a CHECK violation that is non-obvious from the error message (it'll look like a generic seed-data bug). A pre-flighted comment costs nothing.

---

### F-CMP-M2 (MEDIUM — vertical-pack composition)

**Category:** ADR-029 Master-Agent composability with `team_presets.archetype_ids[]`
**Severity:** MEDIUM (design observation, not a defect)
**Confidence:** MEDIUM

The `team_presets.archetype_ids uuid[] NOT NULL` column (`contracts/agents/schema.sql:69`) stores a flat ordered list of archetype IDs. The `productivity_core_v1.py` seed populates it with `[coordinator_id, researcher_id, writer_id, analyst_id]` and stores the DAG separately in `default_workflow_dag_json`.

For Wave-1 Master-Agent verticals, the schema **does NOT preclude** inserting a Master archetype above the 4 leaves — `archetype_ids` is just a flat array; the DAG JSON is where the layer hierarchy lives. So composability is preserved.

**However**, two design questions surface that aren't resolved by current contracts:

1. **Ordering convention for `archetype_ids[]`.** Phase 00.5b establishes the order «coordinator, researcher, writer, analyst» (canonical leaves first). When Master joins, is the convention «master, coordinator, leaves…» or «leaves…, coordinator, master»? No ADR fixes this. `agents/seed_data/productivity_core_v1.py:70-71` documents the current order but doesn't anticipate Master.
2. **No FK from `team_presets` to a Master-specific column.** Wave-1 verticals will need either (a) a `master_archetype_id uuid REFERENCES agent_archetypes(id)` column added to `team_presets`, or (b) a convention that Master is `archetype_ids[0]`. Option (a) is cleaner (queryable) but breaks the «archetype_ids is the single source of composition» invariant.

**Remediation:**
1. Phase 01.1 spec should explicitly decide: add `master_archetype_id` column OR enforce position-0 convention. **Recommendation:** add `master_archetype_id uuid NULL REFERENCES agent_archetypes(id)` — NULL for horizontal presets (Wave 0), set for verticals (Wave 1+). One column, queryable, doesn't break Wave-0 seed.
2. Add to ADR-029 a §«Schema impact» section pinning the column-add decision before Phase 01.1 implementation starts.

**Why this lands MEDIUM:** the schema **doesn't preclude** Master-Agent today, but the **representation** is undefined. An auditor reviewing Phase 01.1's first PR would have to re-derive this decision under time pressure. Best to nail it down in ADR-029 before then.

---

### F-CMP-L1 (LOW — CloudEvents transport drift signal)

**Category:** FZ-152 audit-trail durability — CloudEvents transport
**Severity:** LOW (Wave 0 acceptance per ADR-014 §4)
**Confidence:** HIGH

Current Wave-0 transport: `_shared.cloudevents.emit_cloudevent` logs via structlog (per ADR-014 §4 «Log-only Wave 0; Wave 1+ swap to Redis Streams XADD keeps emit API stable»). This is intentional — the audit-log table (`audit.audit_log`, append-only with UPDATE/DELETE trigger blocks, 3-year retention per ADR-014 §3) is the canonical FZ-152 evidence surface; CloudEvents are an additional projection.

**Observation:** every new INSERT in Phase 00.5b's `agents.agent_instances`, `tasks.tasks`, `tasks.task_steps` emits a CloudEvent BUT relies on structlog persistence for durability in Wave 0. If structlog output isn't shipped to immutable storage (e.g. an S3 sink or similar), there's an effective gap between «event emitted» and «event durably stored» for the period until the Redis Streams swap.

**Why LOW:** the `audit.audit_log` append-only table is the actual FZ-152 surface; CloudEvents in Wave 0 are best-effort. Founder-resolved per ADR-014 §4 as acceptable.

**Remediation:** none in Phase 00.5b. Track for Phase 01.x: confirm the structlog sink configuration for Wave 0 production has a 3-year-retention persistence path OR explicitly accept that CloudEvents are dev-debug-only until the Redis Streams swap. Either is acceptable — just make the choice explicit so an auditor doesn't think the gap is accidental.

**ТX-bound emit pattern confirmation:** both `agents/events.py` and `tasks/events.py` accept the implicit transactional context via the async session held by the caller — neither emits «out of band» of the session. This matches the «TX-bound emit» pattern noted in the founder brief and is correct for Wave-0 → Wave-1 transport-swap stability.

---

### F-CMP-L2 (LOW — new dep transitive scan)

**Category:** Pip-audit ignore registry — Phase 00.5b dep additions
**Severity:** LOW (no new ignores added)
**Confidence:** HIGH

Phase 00.5b adds significant dependency surface: `pydantic-ai>=1.30.1` (Commit 4) plus the opentelemetry chain (transitive). The CI workflow diff (`git diff 0360955..HEAD -- .github/workflows/ci-backend.yml`) shows **27 lines changed, zero new `--ignore-vuln` entries**. The existing `PYSEC-2025-183` (pyjwt, disputed) is the only ignored advisory.

`backend/pyproject.toml:175-179` documents a known import-time warning from pydantic-ai 1.30 about `opentelemetry._events.NoOpEventLogger` deprecation, but this is a **deprecation warning, not a CVE** — no pip-audit ignore needed.

**No action required.** Phase 00.5b honored the «register every new ignore with rationale» discipline by adding **zero** new ignores, which is the best possible outcome.

---

### F-CMP-L3 (LOW — Wave-1 retrofit signal)

**Category:** Role-prompt v1.0.0 lift discipline
**Severity:** LOW (correctly deferred)
**Confidence:** HIGH

All 4 role-prompts ship with `version: 0.1.0` + `status: Proposed` + `quality_bar: first-draft (hardening pass at Phase 01.1 retro)`. The `role_prompt_loader.py` enforces frontmatter required-keys + 9-section monotonicity but **does NOT** enforce semver progression or status transitions yet.

This is **correct for Wave 0** — per ADR-010 §«Жизненный цикл версии роли/template», the lifecycle is `draft → staging → canary-5% → canary-25% → stable → deprecated → archived`, and Wave-0 lives at `draft` (first-pass) with the lift to `staging`/`stable` deferred to Phase 01.1 retro per AC14 (pinned at `gates/wave-0-to-1.md:37,102`).

**Remediation:** none in Phase 00.5b. Phase 01.1 retro must:
1. Lift versions to `1.0.0` and statuses to `staging` (or `locked` per the schema enum at `agent_archetypes.status_chk`) after the hardening pass produces failing-case fixtures.
2. Add a status-progression check to `role_prompt_loader.py` rejecting forward-references (e.g. an `analyst.md` that references a non-existent `analytics-team` would be a parse error).

---

## Wave-1 readiness flags

### Master-Agent extensibility ✅ PASS (with F-CMP-M1 caveat)

- Schema-level: `agent_archetypes` table supports any string `slug` + `vertical_slug` + `prompt_version`. The natural-key `UNIQUE(vertical_slug, slug, prompt_version)` cleanly isolates horizontal (`vertical_slug='horizontal'`) from future verticals (`marketing-agency`, `wb-seller`, etc.).
- Code-level: `role_prompt_loader.py:121-142` resolves prompts by slug + filesystem path. Adding `contracts/role-prompts/masters/agency-marketing-ru-master.md` requires zero loader changes — the directory pattern from ADR-029 §«Master-Agent prompt storage» drops in cleanly.
- **Blocker:** `role_category` CHECK constraint must be widened (F-CMP-M1).

### Vertical-pack composition ✅ PASS (with F-CMP-M2 caveat)

- `team_presets` schema supports the 5 vertical packs (Marketing, Telegram, WB-Seller, Бухгалтерия, Sales) via `vertical_slug` + `archetype_ids[]` + `default_workflow_dag_json`. Wave 1+ adds rows with `vertical_slug='marketing-agency'`, `'telegram-creator'`, etc.
- The horizontal `productivity-core` preset (`vertical_slug='horizontal'`) is **distinguishable** from future vertical slugs by the literal value — no collision risk.
- **Open question:** Master-Agent representation in `team_presets` — flat `archetype_ids[0]` convention OR new `master_archetype_id` column (F-CMP-M2).

### Vertical-domain readiness ✅ PASS

- Per ADR-017 revision 2026-05-15, productivity-core ships as the horizontal anchor. The Phase 00.5b seed (`productivity_core_v1.py:114-117`) explicitly documents «Горизонтальный preset для Wave 0 internal demo. … Master-Agent layer и vertical-packs — Wave 1+.» — i.e. the seed-data narrative is honest about scope.
- `ADR-017-vertical-templates.md:15` table row 0 documents `productivity_core → horizontal → W0 (anchor) → — (Coordinator top-level)` — confirming no Master-Agent at the horizontal layer (matches ADR-029 §«Horizontal team-preset (Wave 0) остаётся однослойным»).

### FZ-152 / РКН audit-trail ✅ PASS

- `audit.audit_log` append-only table + UPDATE/DELETE trigger block + 3-year retention per ADR-014 §3 — unchanged in Phase 00.5b.
- `agents/events.py` + `tasks/events.py` both emit CloudEvents 1.0 envelopes via the canonical `_shared.cloudevents.emit_cloudevent` helper with proper `source` URIs (`oriion://contexts/agents`, `oriion://contexts/tasks`).
- TX-bound emit pattern confirmed — no async out-of-band emits introduced.
- OQ-04 (FZ-152 personal-data submission to РКН) status: dev unblocked per HANDOFF — no Phase 00.5b dependency.

---

## Defer-to-Wave-1 with AC pin

| Defer item | AC pin | Where pinned |
|---|---|---|
| Role-prompt v1.0.0 lift + status promotion (`Proposed → staging/locked`) after replicate-failure hardening pass | **AC14** (gates/wave-0-to-1.md:102) — «Role-prompts hardening backlog produced and handed to Phase 01.1 retro» | `gates/wave-0-to-1.md:37,102` + frontmatter `quality_bar` field of all 4 role-prompts |
| `role_category` CHECK constraint widened to include `'master'` literal (F-CMP-M1) | New AC needed in Phase 01.1 spec — recommend «AC1: Master archetype Alembic migration precedes seed inserts» | TODO — add to Phase 01.1 backlog before phase-discuss |
| `master_archetype_id` column or position-0 convention in `team_presets` (F-CMP-M2) | New ADR-029 §«Schema impact» — recommend column-add option | TODO — amend ADR-029 before Phase 01.1 discuss |
| HANDOFF.md / STATUS.md stale-claim cleanup re: ADR-024 §3 (F-CMP-N2) | Should land **in this PR's Commit 8** — bundle with Exit ritual | `.planning/HANDOFF.md:50,83,124` + `.planning/STATUS.md:50` |
| CloudEvents transport: Wave-0 structlog sink durability OR explicit «dev-debug only» acceptance (F-CMP-L1) | Track for Phase 01.x — no Wave-0 AC needed (founder-accepted per ADR-014 §4) | None — informational |

---

## Wave-0 deadline confidence delta (2026-06-09)

**Pre-Phase-05 audit baseline:** ~65% confidence Wave-0 ships before deadline.
**Post Phase 00.5a + 00.5b state:** ~78% confidence.

**Delta drivers (positive):**
- Phase 00.5a 1-commit landing (RLS bootstrap) cleared the highest-uncertainty compliance gap (H-1) cleanly with audit-trail honesty — `git log --oneline` shows `dae62c1 fix(multitenancy): resolve cell.owner role by slug` and `b5f27a0 fix(lint,tests)` on main, indicating both the structural fix + lint discipline shipped together.
- Phase 00.5b 6-commit atomic shippability with checkpoint commit at midpoint (`41baf7f docs(planning): Phase 00.5b mid-session checkpoint`) demonstrates the chunking philosophy from /grill-me session works in practice.
- ADR-024 §3 amendment is **already done** (F-CMP-N2 reveals this) — Commit 8 is now a pure Exit ritual (STATUS/HANDOFF rewrites + JOURNAL append + Phase 00.5 ✅ Complete flip + PR open), not a structural change. Effort drops from ~2hrs to ~30min.
- Zero new pip-audit ignores added despite 30+ transitive dep additions — strong dep-hygiene signal.
- All 4 role-prompts have valid frontmatter + 9-section structure passing `role_prompt_loader.py` mechanical checks — first-pass alignment hardening (T5) genuinely landed.

**Delta drivers (negative / remaining risk):**
- F-CMP-N2: HANDOFF/STATUS stale claims need cleanup before PR opens (5min — trivial).
- F-CMP-M1 + M2 are Phase 01.1 problems but if not pre-flighted in this PR's JOURNAL, they will surface as Wave-1 surprises (medium future-cost).
- The ADR-024 §3 «3-line amendment» wording in the founder brief and HANDOFF is **incorrect** — that needs to be reconciled. Without the reconcile, the audit story for the merger is «we landed a thing that was already landed», which is fine but reads weird in a PR description.

**Cadence comment (not a deep schedule audit):**
- Two weeks until deadline (2026-06-09). Phase 00.5b is one commit away from PR-open. Phase 00.6 (Yandex KMS + production credentials) is the next block.
- The chunking discipline (Phase 00.5 → 00.5a + 00.5b) added zero calendar overhead and produced two honest landing surfaces. This pattern repeats well for Phase 00.6 if it gets large.
- **On-track verdict:** YES, with the F-CMP-N2 cleanup as the only Phase-00.5b blocker remaining.

---

## Recommendation

**Merge Phase 00.5b after applying F-CMP-N2 cleanup (5 minutes, HANDOFF + STATUS line-edits).**

The cross-phase compliance posture is **honest, extensible, and auditable**:
- Phase 00.5a closed Compliance H-1 with verifiable evidence (ADR-014 wording + migration + test fixture).
- Phase 00.5b closes Architecture H3 — but via prior ADR-024 §3 amendment landing (2026-05-19) + re-confirmation paragraph (2026-05-21), not via a Commit-8 ADR edit. The «3-line amendment» framing in HANDOFF is stale.
- Wave-1 Master-Agent extensibility is preserved; F-CMP-M1 + M2 are pre-flighted for Phase 01.1.
- FZ-152 audit-trail invariants are conformant; CloudEvents emit pattern is TX-bound and transport-swap-stable per ADR-014 §4.
- AC14 first-pass + hardening-backlog discipline is honestly pinned.

**Specific actions for Commit 8 (Exit ritual):**
1. **Required (F-CMP-N2):** HANDOFF.md lines 50, 83, 124 + STATUS.md line 50 — rewrite from «not yet landed» to «already landed 2026-05-19; re-confirmed 2026-05-21». Drop the «3-line amendment» framing from the Commit 8 description.
2. **Required:** ADR-024 status line bump from «re-confirmed 2026-05-21 by Phase 00.5b audit» to «re-confirmed at Phase 00.5b merge» (or include the PR number).
3. **Recommended (F-CMP-M1 + M2 pre-flight):** add a JOURNAL.md entry capturing the two Master-Agent extensibility caveats so Phase 01.1 picks them up at phase-discuss.
4. **Recommended:** add a 1-line forward comment at `contracts/agents/schema.sql:30` («-- Wave 1+ adds `'master'` per ADR-029 Master-Agent layer; widen CHECK before seeding Master archetypes») to make F-CMP-M1 self-discovering for the next implementer.

**Confidence in 2026-06-09 Wave-0 ship: ~78% (up from pre-Phase-05 ~65%).** The remaining 22% risk is concentrated in Phase 00.6 (Yandex KMS + prod credentials), not in the agent-runtime stack just audited.

---

**Audit complete.** 7 findings (1 verified-down-to-NONE + 2 MEDIUM + 4 LOW); ADR landing matrix all PASS or PASS-WITH-CAVEAT; Wave-1 readiness flags green with two pre-flighted caveats.
