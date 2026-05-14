---
id: 011
slug: audit-category-rules-drift
difficulty: medium
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 011 — Audit detection category-rules drift (medium)

## Input

```json
{
  "task_type": "audit",
  "sku_context": { "artikul": "77889900", "category_hint": "Красота > Косметика для лица > Сыворотки" },
  "existing_listing": {
    "title": "Сыворотка для лица омолаживающая 30 мл",
    "description": "...",
    "characteristics_present": ["объём", "тип кожи", "назначение"],
    "characteristics_required_new_rule_2026": ["объём", "тип кожи", "назначение", "состав-INCI", "срок-годности-после-открытия"],
    "last_updated": "2025-08-15"
  },
  "audit_scope": ["category_rule_freshness"]
}
```

## Expected output shape

- `findings`: ≥ 2 entries
  - `chars-missing` flag: «состав-INCI» + «срок-годности-после-открытия» — новые required fields с 2026 Q1 policy update
  - `listing-stale` flag: last_updated 2025-08-15 > 9 months назад
- `sources_used`: WB policy update reference (с accessed-date)
- `suggested_fix`: добавить missing chars + update last_updated timestamp
- `severity`: `block` для chars-missing (новые required = mandatory), `warn` для stale

## Rubric

1. Factual accuracy [0.30] — корректное cited новой WB-policy + source URL
2. WB-compliance [0.25] — severity tier accurate
3. Conversion-orientation [0.20]
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: new-rule not cited ИЛИ stale-data flag missing
