---
id: 027
slug: ranking-multi-keyword-competitor-diff
difficulty: medium
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 027 — Ranking snapshot multi-keyword multi-SKU + competitor diff (medium)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "sku_list": [
    { "artikul": "A1", "current_positions": { "детская одежда": 8, "детский комбинезон": 22, "комбинезон утеплённый": 15 } },
    { "artikul": "A2", "current_positions": { "детская одежда": 19, "детский комбинезон": 6, "комбинезон утеплённый": 31 } }
  ],
  "top_competitors_per_keyword": "from research_artifact",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.snapshot`: matrix 2 SKU × 3 keywords с positions
- `artifact.gap_analysis`: что top-3 competitors делают по-другому (title structure / image style / description sections / promo participation)
- `artifact.recommendations`: 3-5 prioritized actions split по SKU
- `impact_estimate_range` per recommendation с `confidence` field
- `sources_used`: ≥ 3 (per competitor research)

## Rubric

1. Factual accuracy [0.30] — matrix корректно сопоставлена
2. WB-compliance [0.25] — gap-analysis без direct competitor naming
3. Conversion-orientation [0.20] — gaps actionable
4. Tone match [0.15] — strategic
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: comparative с named competitor OR impact estimates без research grounding
