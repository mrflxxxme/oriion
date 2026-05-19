# `contracts/role-prompts/` — Horizontal-team role prompts

> Authoritative role prompts for the Wave-0 horizontal `productivity-core`
> team (4 single-layer agents: Coordinator + Researcher + Writer + Analyst).
> Status: **first-draft**, materialized during Phase 00.5 scope per
> Session-2026-05-15 decision #11. Hardening pass scheduled for Phase 01.1
> retro per AC14.

## Files

| File | Role | Status |
|---|---|---|
| `coordinator.md` | Workflow orchestrator — decomposes user tasks, delegates to specialists, integrates outputs | first-draft |
| `researcher.md` | Market & competitive intel — sourcing, structured note-taking, fact-checking | first-draft |
| `writer.md` | Long-form prose / briefs / posts — voice control, format adherence | first-draft |
| `analyst.md` | Data + structured synthesis — competitive matrices, KPI rollups | first-draft |

## Structure (per Session-2026-05-15 #11)

Each role-prompt follows a 9-section deep structure (~2500-3200 words per role) with YAML frontmatter. Sections include: persona + objectives, capabilities matrix, tooling allowlist, anti-patterns, output schema, evaluator rubric, version metadata.

## Versioning

Per [ADR-010](../../decisions/ADR-010-role-versioning.md): SemVer on prompt content. Phase 01.1 retro hardening lifts these from first-draft to v1.0.0.

## Horizontal vs vertical

Wave-0 horizontal preset stays **single-layer** (Coordinator → specialists, no Master-Agent above). Vertical templates (Wave-1+) add a Master-Agent layer per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md). These role-prompts intentionally do NOT have a Master-Agent counterpart.
