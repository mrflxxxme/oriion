---
id: 025
slug: ranking-single-keyword-single-sku
difficulty: easy
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 025 — Ranking snapshot single keyword single SKU (easy)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "sku_context": {
    "artikul": "12345678",
    "category_hint": "Дом и сад > Текстиль > Полотенца",
    "current_listing": { "title": "Полотенце махровое...", "rating": 4.6, "reviews_count": 234, "sales_30d": 87 }
  },
  "target_keyword": "полотенце махровое",
  "current_position_estimate": 47,
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.snapshot`: structured (current_position, position_history, top_3_competitors_brief)
- `artifact.recommendations`: 2-4 prioritized action items
  - 1× title/description tweak (concrete suggestion)
  - 1× keyword optimization (add adjacent terms «банное», «70x140»)
  - Optional: image refresh recommendation
- Each recommendation has `estimated_impact_range` (например, «+5-12 позиций в течение 2 недель») + `confidence: low|medium|high`
- `sources_used`: research-cited
- `uncertainty_flags` для impact estimates

## Rubric

1. Factual accuracy [0.30]
2. WB-compliance [0.25]
3. Conversion-orientation [0.20] — recommendations actionable
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: precise position promise («окажетесь на позиции 12») без uncertainty
