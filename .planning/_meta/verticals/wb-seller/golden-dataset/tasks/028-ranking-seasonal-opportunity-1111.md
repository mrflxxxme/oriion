---
id: 028
slug: ranking-seasonal-opportunity-1111
difficulty: medium
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 028 — Ranking snapshot: seasonal opportunity (11.11 приближается) (medium)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "current_date": "2026-10-15",
  "sku_context": {
    "category_hint": "Дом и сад > Кухня > Посуда",
    "sku_list_subset": ["A1", "A2", "A3"]
  },
  "upcoming_promo": "11.11 (2026-11-01 to 2026-11-11)",
  "promo_requirements_research": "от researcher artifact — конкретные thresholds (sale_price ≤ X% MRP)",
  "tone": "promotional"
}
```

## Expected output shape

- `artifact.snapshot`: current sales velocity + ranking baseline
- `artifact.promo_strategy`: per-SKU pricing strategy для 11.11 participation
  - SKU recommendations: participate / partial / skip (с rationale)
  - Suggested sale_price (within research-cited thresholds)
  - Stock recommendation (учитывая 11.11 demand spike)
- `artifact.content_refresh`: title/description tweaks с seasonal accents («подарок к НГ», «зимняя коллекция»)
- `artifact.recommendations`: prioritized timeline (D-14 → D-7 → D-0 → during-promo)
- `sources_used`: ≥ 2 (promo rules + competitor strategy если research available)

## Rubric

1. Factual accuracy [0.30] — корректное использование promo-rules thresholds
2. WB-compliance [0.25] — sale_price compliance с WB promo requirements
3. Conversion-orientation [0.20] — strategy actionable + ROI-oriented
4. Tone match [0.15] — strategic, не pushy
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: sale_price non-compliant ИЛИ no timeline structure
