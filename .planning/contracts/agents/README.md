# Bounded context: `agents`

**Status:** DRAFT-READY (Milestone B.2, Wave 0)
**Owner:** backend-implementer + architect (naming gatekeeper)
**ADR refs:** [ADR-024](../../decisions/ADR-024-bounded-context-contracts.md), [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md), [ADR-010](../../decisions/ADR-010-role-versioning.md), [ADR-023](../../decisions/ADR-023-ai-team-runtime.md)
**GRILL refs:** DECISION-7, DECISION-11, **P-AUDIT-2** (naming enforcement)

## Purpose

Bridge between the **authoring layer** (`verticals/<slug>/prompts/<role>.md` — version-controlled Markdown with frontmatter) and the **runtime layer** (per-cell instantiated AI personas serving tasks).

- `agent_archetypes` snapshots a prompt at a specific version.
- `team_presets` bundles archetypes into opinionated compositions for fast cell bootstrap (e.g. "WB Starter Team").
- `agent_instances` are cell-scoped instantiations that can be renamed and tuned without forking the archetype.

## Ubiquitous language — CRITICAL naming clarification

| Canonical term | Lives in | Meaning |
|---|---|---|
| **`agent_archetypes`** | this context | Vertical-level AI personas (WB-Coordinator, WB-Researcher, WB-ListingWriter). |
| **`agent_archetype_id`** | this context, `tasks` | **The** FK column name. Used everywhere. |
| **`agent_instances`** | this context | Cell-level instantiations of archetypes (with `custom_name`, `custom_settings_jsonb`). |
| **`system_roles`** | `rbac` context | System-level RBAC roles (Owner, Admin, Editor). **Different concept — do not confuse.** |

### Deprecated terms (forbidden in new code)

| Deprecated | Use instead | Source of deprecation |
|---|---|---|
| `roles_agent` (table name) | `agent_archetypes` | ADR-024 §2 |
| `ui_sprite_archetype` (column name) | `agent_archetype_id` | ADR-024 §2, P-AUDIT-2 |
| `sprite_id` (column name) | `agent_archetype_id` | ADR-024 §2, P-AUDIT-2 |
| `roles_rbac` (table name) | `system_roles` (in `rbac` context) | ADR-024 §2 |

CI lint and reviewer-backend enforce zero hits for the deprecated terms in PR diffs touching `contracts/` or `backend/src/`.

## Invariants

1. **Version pin.** `agent_archetypes.prompt_version` must equal the `version:` field in the frontmatter of `verticals/<vertical_slug>/prompts/<slug>.md`. Mismatch ⇒ CI fails. The unique constraint `(vertical_slug, slug, prompt_version)` makes archetype rows immutable per version.
2. **Soft deprecation.** An archetype may be `deprecated_at`-stamped, but existing `agent_instances` referencing it continue to work until explicit cell-level migration. This avoids breaking running tasks. Emit `archetype.deprecated.v1` with `superseded_by` so downstream UIs can prompt migration.
3. **Status promotion ladder.** `draft → reviewed → promoted → locked` (DECISION-11). Transitions are forward-only; `locked` is the only status usable in production cell instances (enforced in service layer).
4. **Canonical FK column.** The column is **always** named `agent_archetype_id`. Deprecated aliases are CI-forbidden (P-AUDIT-2).
5. **Cell isolation.** `agent_instances` are scoped to a single cell via RLS using `app.current_cell_id`. Cross-cell sharing of instances is not supported in Wave 0.
6. **Preset integrity.** A `team_preset.archetype_ids` array must reference archetypes from the **same** `vertical_slug` and all in `status = 'locked'` at apply time (service-layer check, since arrays can't have FK constraints).

## External dependencies (cross-context)

| Context | Reason |
|---|---|
| `multitenancy` | `cell_id` FK; RLS via `app.current_cell_id`. |
| `llm-gateway` | `model_provider_slug` references `llm_provider_config.provider_slug` (cross-context, not DB-enforced). |
| `tasks` | Tasks reference both `agent_instance_id` and snapshot `agent_archetype_id` for historical accuracy. |
| `verticals/` | **Source of truth for prompt content.** This context stores only the version pin, not the prompt body. |

## Out of scope

- Prompt text storage (lives in `verticals/<slug>/prompts/`).
- Prompt evaluation (lives in `evaluator` agent + golden dataset pipeline, ADR-026).
- RBAC roles (lives in `rbac` context — `system_roles` is a **different** concept).

## Files

- [`schema.sql`](./schema.sql) — PostgreSQL 16 DDL with RLS.
- [`api.yaml`](./api.yaml) — OpenAPI 3.1.
- [`events.yaml`](./events.yaml) — CloudEvents 1.0.
