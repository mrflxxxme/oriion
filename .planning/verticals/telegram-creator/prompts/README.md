# `verticals/telegram-creator/prompts/` — vertical-specific role prompts

> Per ADR-029, the **Master-Agent prompt** for this vertical lives at
> [`contracts/role-prompts/masters/telegram_creator.md`](../../../contracts/role-prompts/masters/telegram_creator.md)
> — the same canonical location `agency-marketing-ru`'s Master prompt uses
> (required by `src.agents.services.role_prompt_loader.load_master_prompt`,
> which resolves `contracts/role-prompts/masters/<vertical>.md`). It is
> **not** duplicated here to avoid drift between two copies of the same
> contract.

## Files in this directory

| File | Role | Status |
|---|---|---|
| `community_manager.md` | Community-manager — reads channel activity (`telegram_read_updates`) and prepares platform-native drafts (`telegram_draft_message`); vertical-specific, not reused from the horizontal preset | draft (AI-baseline, v0.1.0) |

## Reused horizontal role-prompts (not duplicated here)

Coordinator, Researcher, Writer, Analyst are reused **verbatim** from
[`contracts/role-prompts/`](../../../contracts/role-prompts/) (per
`agency_marketing_ru_v1`'s precedent — the horizontal specialists carry the
Master's `StrategicContext` preamble at runtime, they do not need a
vertical-specific prompt fork). See
[`backend/src/agents/seed_data/telegram_creator_v1.py`](../../../backend/src/agents/seed_data/telegram_creator_v1.py)
for the exact archetype wiring.

## Versioning

Per [ADR-010](../../decisions/ADR-010-role-versioning.md): SemVer on prompt
content. Both the Master prompt and `community_manager.md` ship this phase at
`0.1.0` / `status: draft` — founder review promotes to `reviewed` (per
[`../REVIEW-CHECKLIST.md`](../REVIEW-CHECKLIST.md)), which is out of scope
for this phase.
