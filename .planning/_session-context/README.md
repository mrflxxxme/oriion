# `_session-context/` — Session-bound artifacts

> Transient artefacts of completed or in-flight sessions: launch checklists,
> consistency audits, multi-agent audit-swarm reports, ad-hoc planning docs.
> **NOT** the source of truth for current project state — that lives in
> `STATUS.md` / `HANDOFF.md` / `JOURNAL.md` (rolling/snapshot/append-only,
> respectively) at the `.planning/` root, and in `roadmap/` + `decisions/`
> for canonical phase + ADR state.

## Layout convention

```
_session-context/
├── README.md                                 ← this file (index + convention)
├── <ACTIVE-AUDIT-OR-PLAN-NAME>/              ← active artefacts: in-flight audits / pending PRs / live planning
│   ├── AUDIT-REPORT.md                       ← consolidated report (top-of-fold)
│   └── section-NN-*.md                       ← per-section detail reports
└── archive/                                  ← completed work; PRs merged or work moved to canonical state
    ├── YYYY-MM-DD-<slug>.md                  ← single-file artefacts (date-prefixed, kebab-case)
    └── YYYY-MM-DD-<slug>/                    ← multi-section artefacts (same naming)
```

### Naming convention (going forward)

- **New session artefacts:** `YYYY-MM-DD-<slug>.md` (single file) or
  `YYYY-MM-DD-<slug>/` (multi-section directory)
- **Date prefix** sorts chronologically + makes the origin obvious
- **Slug** lowercase kebab-case; describes what the artefact is about
  (`phase-00-2-5-launch-checklist`, `audit-pr-30`, `architect-pr-3-way-parallel`)
- **Move to `archive/`** once the underlying PR merges OR the work moves
  to canonical state (`roadmap/` for phase work, `decisions/` for ADRs)
- **Existing pre-2026-05-19 UPPER-DASH names** are not retroactively
  renamed — git history continuity matters more than naming purity for
  historical artefacts

## Active artefacts (in `_session-context/`)

| Path | Purpose | Context |
|---|---|---|
| `AUDIT-2026-05-19-PRE-PHASE-05/` | Cross-phase pre-Phase-05 audit (5-agent swarm: Compliance + Architecture + Test-Adequacy + Info-Architect + Roadmap-Reviewer) | Pending PR (this PR); audits cumulative Wave-0 state before Phase 00.5 starts |

## Archived artefacts (in `_session-context/archive/`)

| Path | Purpose | Final PR / outcome |
|---|---|---|
| `2026-05-17-architect-pr-3-way-parallel.md` | Architect-PR planning doc: split iam contract extension + `_shared` Alembic bootstrap to unblock 3-way parallel 00.2 / 00.3 / 00.4 | PR #27 merged 2026-05-17 |
| `2026-05-19-phase-00-2-5-launch-checklist.md` | 12-section checklist for Phase 00.2.5 integration session | Phase 00.2.5 ✅ Complete via PR #32 |
| `2026-05-19-post-merge-audit-pr-30.md` | Post-merge consistency audit after PR #30 (Phase 00.3 + 00.4 combined) | Findings rolled into PR #32 audit + this archive |
| `2026-05-19-audit-pr-30/` | 5-agent independent audit of PR #30 (sections: 01 code-review — paused, 02 compliance, 03 security, 04 test-adequacy, 05 architecture) | PR #30 merged 2026-05-19 with 4 HIGH findings fixed in-loop |
| `2026-05-19-audit-pr-32/` | 5-agent independent audit of PR #32 (Phase 00.2.5 integration) — sections: 01 code-review, 02 security, 03 test-adequacy, 04 architecture, 05 compliance, plus `AUDIT-REPORT.md` consolidated | PR #32 merged 2026-05-19 with 4 HIGH addressed in-loop, 2 deferred to Phase 00.5 |

## Lifecycle

1. **Create** an artefact when starting a multi-step planning task / audit
2. **Iterate** as the work proceeds (reports get written, fixes applied)
3. **Archive** when:
   - The PR being planned/audited merges (rename + move to `archive/`)
   - The work moves to canonical state (`roadmap/phase-XX.md` or
     `decisions/ADR-NNN-*.md`)
   - The artefact's scope is superseded by a newer one

The point of moving to `archive/` is **discoverability** for new agents:
the top level shows only what's ACTIVE; history is one directory deeper.

## Authors / consumers

- **Author**: any AI-agent session that runs multi-step planning,
  audit-swarm reports, or doc-heavy cleanup work
- **Consumer**: future AI-agent sessions looking for "what happened when";
  PR reviewers wanting deep context on a recent merge

Canonical project state (current phase, blockers, decisions) lives in
`STATUS.md` / `HANDOFF.md` / `JOURNAL.md` — agents should read those
FIRST and only consult `_session-context/` for deeper background.
