# `verticals/wb-seller/prompts/` — Wave-0 legacy WB-Seller prompts

> ⚠️ **Status (2026-05-15 reorg):** these prompts were authored when WB-Seller
> was the Wave-0 anchor vertical. Per Session-2026-05-15 decision #2,
> WB-Seller moved Wave-0 → **Wave 2** and the Wave-0 anchor became the
> horizontal `productivity-core` team. These prompts STAY here as the
> proof-of-concept for the vertical Master-Agent pattern (per [ADR-029](../../../decisions/ADR-029-master-agent-vertical-templates.md))
> but the **canonical Wave-2 versions** will be re-authored when
> Phase 02.2 (WB-Seller vertical preset) opens.

## Files

| File | Role | Status |
|---|---|---|
| `master.md` | WB-Seller Master-Agent (CEO-level domain expertise + strategic oversight) | first-draft (Wave-0 legacy; needs Wave-2 hardening) |
| `coordinator.md` | WB-Seller Coordinator (COO-level operational orchestration) | first-draft (Wave-0 legacy) |
| `wb_specialist.md` | WB-Seller Specialist (account-level execution: listings, ranking, ads) | first-draft (Wave-0 legacy) |

## Wave-2 alignment

When Phase 02.2 opens, expect:
1. Master-Agent prompt re-aligned with ADR-029 two-layer pattern
2. Specialist prompt split into sub-roles (listings vs ranking vs ads)
3. Golden-dataset (in `../golden-dataset/`) cross-referenced for evaluator rubric

See `../README.md` for the full WB-Seller vertical lifecycle context.
