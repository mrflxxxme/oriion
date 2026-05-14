---
id: 007
slug: audit-title-length-only
difficulty: easy
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 007 — Audit listing title-length compliance (easy)

## Input

```json
{
  "task_type": "audit",
  "sku_context": { "artikul": "98765432", "category_hint": "Дом и сад > Текстиль > Постельное белье" },
  "existing_listing": {
    "title": "Комплект постельного белья евро 200х220 двуспальный сатин турецкий с европейской резинкой нежно-розовый",
    "title_char_count": 108
  },
  "audit_scope": ["title_length"]
}
```

## Expected output shape

- `mode: "audit"`, `artifact.findings`: ≥ 1 entry (`title-overflow` flag)
- `artifact.findings[].rule_violated`: «WB title max 60 chars (category-dependent)»
- `artifact.findings[].severity`: `block`
- `artifact.findings[].suggested_fix`: rewritten title ≤ 60 chars, ключевые слова preserved
- `compliance_check.status`: `flagged`

## Rubric

1. Factual accuracy [0.30] — correct rule cited (60 chars), correct count of input title
2. WB-compliance [0.25] — suggested fix actually compliant
3. Conversion-orientation [0.20] — fix preserves top keywords («комплект», «евро», «сатин»)
4. Tone match [0.15] — factual audit, no preachy
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: violation missed ИЛИ suggested fix > 60 chars
