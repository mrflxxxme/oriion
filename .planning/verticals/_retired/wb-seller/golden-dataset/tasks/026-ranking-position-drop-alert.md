---
id: 026
slug: ranking-position-drop-alert
difficulty: easy
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 026 — Ranking snapshot: position drop alert (easy)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "sku_context": { "artikul": "23456789", "category_hint": "Мужчинам > Одежда > Футболки" },
  "alert": "Position dropped 12 → 38 for keyword 'футболка мужская' за неделю",
  "current_listing_state": { "rating": 4.5, "reviews_count": 156, "sales_30d_prior": 45, "sales_30d_current": 18 },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.snapshot`: position diff + sales correlation (-60%)
- `artifact.likely_causes`: 2-4 hypotheses ranked by likelihood
  - Promo competitors появились в категории
  - Stock-out event на your side?
  - Negative review recently?
  - Algorithmic recalibration WB
- `artifact.recommendations`: 2-3 diagnostic + remedial steps
- No false certainty о причине (each cause flagged `hypothesis`, not `cause`)
- `sources_used`: research-cited

## Rubric

1. Factual accuracy [0.30] — corrette correlation reasoning
2. WB-compliance [0.25]
3. Conversion-orientation [0.20] — actionable diagnostic flow
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: single-cause certainty ИЛИ no diagnostic step
