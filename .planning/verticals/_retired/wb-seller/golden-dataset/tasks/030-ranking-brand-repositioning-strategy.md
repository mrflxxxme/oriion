---
id: 030
slug: ranking-brand-repositioning-strategy
difficulty: hard
primary_task: ranking-snapshot
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (recommendations mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 030 — Ranking snapshot: brand-wide repositioning strategy (hard)

## Input

```json
{
  "task_type": "ranking-snapshot",
  "scope": "brand-wide",
  "seller_brand": "TBD_BRAND_NAME",
  "sku_portfolio": {
    "total_skus": 47,
    "current_avg_rating": 4.5,
    "current_avg_position_target_keywords": 34,
    "categories_covered": ["Мужская одежда", "Женская одежда", "Аксессуары"],
    "pain_points_research": "low brand-recognition, dispersed across 3 categories, no flagship SKU"
  },
  "founder_goal": "Increase brand-recognition + concentrate sales в 2 категории следующие 6 месяцев",
  "tone": "strategic"
}
```

## Expected output shape

- `artifact.diagnosis`: 3-5 root-causes за dispersed performance (no flagship / inconsistent brand-voice / spread thin / lack of clear-USP)
- `artifact.repositioning_strategy`:
  - Phase 1 (months 1-2): identify top-3 flagship SKU из 47 → focus content + promo investment
  - Phase 2 (months 3-4): refresh brand-voice consistency across all 47 SKU (template-based)
  - Phase 3 (months 5-6): exit подкатегория с lowest ROI; reinvest в 2 strongest
  - Specific quarterly KPIs: target avg_position improvement + brand-recognition signals
- `artifact.recommendations`: top-10 prioritized actions с effort / impact / dependencies
- `artifact.risks`: 3 risks + mitigation (e.g., flagship-SKU stockout, brand-voice drift, premature exit)
- `sources_used`: ≥ 5 (research-heavy task)
- `uncertainty_flags`: explicit для long-horizon estimates
- TBD_BRAND_NAME preserved (per PLACEHOLDERS.md)

## Rubric

1. Factual accuracy [0.30] — root-cause analysis grounded в research
2. WB-compliance [0.25]
3. Conversion-orientation [0.20] — strategy executable
4. Tone match [0.15] — strategic depth
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: shallow analysis (no root-causes), OR specific revenue promise, OR TBD_BRAND_NAME заменён
