# `gates/_schema/` — Wave-gate file format schema

> JSON Schema (Draft 2020-12) describing the structure of
> `gates/wave-N-to-N+1.md` files. Used by [ADR-025](../../decisions/ADR-025-acceptance-gate-format.md) as the canonical format for wave-acceptance gates.

## Files

| File | Purpose |
|---|---|
| `gate.schema.json` | The schema itself. Validates frontmatter + body conventions for any `gates/wave-N-to-N+1.md`. |

## Consumers

- Wave-gate files at `gates/wave-N-to-N+1.md` MUST validate against this schema before a Wave acceptance review.
- The `verifier` AI role (per [ADR-023](../../decisions/ADR-023-ai-team-runtime.md)) uses the schema to extract `hard_threshold` / `soft_checks` / `evidence` automatically and computes pass/fail.

## Updating the schema

Schema is versioned alongside ADR-025. Breaking changes to the schema require an ADR revision. Additive changes (new optional fields) are allowed without ADR churn but should be documented in the wave-gate template + this README.
