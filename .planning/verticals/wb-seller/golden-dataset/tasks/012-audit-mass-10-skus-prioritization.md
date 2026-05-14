---
id: 012
slug: audit-mass-10-skus-prioritization
difficulty: hard
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 012 — Mass-audit 10 SKU + prioritization + impact estimate (hard)

## Input

```json
{
  "task_type": "audit",
  "sku_context": {
    "category_hint": "Дом и сад > Текстиль > Постельное белье",
    "sku_list": [
      { "artikul": "SKU01", "title_chars": 45, "description_chars": 1800, "images_count": 5, "rating": 4.6, "sales_30d": 120 },
      { "artikul": "SKU02", "title_chars": 28, "description_chars": 320, "images_count": 2, "rating": 4.3, "sales_30d": 8 },
      "...8 more SKUs..."
    ]
  },
  "audit_scope": ["full_multi_criteria", "rank_by_impact"]
}
```

## Expected output shape

- `findings`: aggregated table 10 rows × ≥ 5 criteria
- `prioritized_action_plan`: top-3 SKUs ranked by `impact_score` (combining current sales gap + fix-effort + uplift-estimate)
- `impact_estimate` per top-3 fix: «±X% conversion uplift» grounded в research_artifact category benchmarks
- `compliance_check.status`: `flagged` (multiple issues)
- `sources_used`: ≥ 4 (category rules + competitor benchmarks + WB content guidelines + WB algorithm guidance)
- `uncertainty_flags`: explicit для impact-estimates (no precise model, range estimate only)

## Rubric

1. Factual accuracy [0.30] — все 10 SKU correctly summarized; impact-estimates grounded
2. WB-compliance [0.25] — fixes actionable per category rules
3. Conversion-orientation [0.20] — prioritization логика обоснована (impact / effort ratio)
4. Tone match [0.15] — strategic, not just technical findings
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: impact-estimates fabricated без category-benchmark grounding
