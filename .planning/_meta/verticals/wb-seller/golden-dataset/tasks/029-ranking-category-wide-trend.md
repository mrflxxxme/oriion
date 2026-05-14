---
id: 029
slug: ranking-category-wide-trend
difficulty: medium
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 029 — Ranking snapshot: category-wide trend analysis (medium)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "category_hint": "Красота > Косметика > Уход за лицом",
  "trend_data_research": "от researcher artifact — last 60d category dynamics",
  "user_sku_list_count": 12,
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.category_trend_summary`: 60-day dynamics — какие подкатегории растут / падают
  - «K-Beauty сыворотки» +35% sales
  - «Anti-age кремы» stable
  - «Уход за губами» -12%
- `artifact.user_portfolio_alignment`: 12 SKU mapped к trends → which align with growing subcategories, which lag
- `artifact.recommendations`:
  - 2 SKU prioritized для investment (content refresh + promo)
  - 2 SKU flagged для potential discontinue / repositioning
- Все trend numbers `source_idx`-referenced
- `uncertainty_flags` для extrapolation

## Rubric

1. Factual accuracy [0.30] — trend data correctly cited
2. WB-compliance [0.25]
3. Conversion-orientation [0.20] — strategic prioritization
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: fabricated trend numbers без source
