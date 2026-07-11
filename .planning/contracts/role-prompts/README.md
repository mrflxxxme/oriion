# `contracts/role-prompts/` — Horizontal-team role prompts

> Authoritative role prompts for the Wave-0 horizontal `productivity-core`
> team (4 single-layer agents: Coordinator + Researcher + Writer + Analyst).
> Status: **hardened, все роли ≥ v1.0.0** (Phase 01.1-retro hardening pass;
> writer поднят до v1.1.1 с anti-fabrication правилами, 2026-07-10).
> Плюс подкаталог `masters/` с vertical Master-промптами (см. ниже).

## Files

| File | Role | Status |
|---|---|---|
| `coordinator.md` | Workflow orchestrator — decomposes user tasks, delegates to specialists, integrates outputs | ≥ v1.0.0 |
| `researcher.md` | Market & competitive intel — sourcing, structured note-taking, fact-checking | ≥ v1.0.0 |
| `writer.md` | Long-form prose / briefs / posts — voice control, format adherence | v1.1.1 (anti-fabrication) |
| `analyst.md` | Data + structured synthesis — competitive matrices, KPI rollups | ≥ v1.0.0 |

## `masters/` — vertical Master-prompts

Подкаталог `masters/` содержит 2 master-промпта вертикалей — `agency_marketing_ru` и
`telegram_creator`: status **reviewed**, version **1.0.1**, `quality_bar: stable`
(live review-run + founder approve, 2026-07-10). Lifecycle `draft → reviewed → locked`
per [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md).

## Structure (per Session-2026-05-15 #11)

Each role-prompt follows a 9-section deep structure (~2500-3200 words per role) with YAML frontmatter. Sections include: persona + objectives, capabilities matrix, tooling allowlist, anti-patterns, output schema, evaluator rubric, version metadata.

## Versioning

Per [ADR-010](../../decisions/ADR-010-role-versioning.md): SemVer on prompt content. Phase 01.1 retro hardening lifts these from first-draft to v1.0.0.

## Horizontal vs vertical

Wave-0 horizontal preset stays **single-layer** (Coordinator → specialists, no Master-Agent above). Vertical templates (Wave-1+) add a Master-Agent layer per [ADR-029](../../decisions/ADR-029-master-agent-vertical-templates.md). These role-prompts intentionally do NOT have a Master-Agent counterpart.
