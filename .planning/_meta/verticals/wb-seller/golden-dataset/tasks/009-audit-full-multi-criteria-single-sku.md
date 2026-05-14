---
id: 009
slug: audit-full-multi-criteria-single-sku
difficulty: medium
primary_task: audit
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (audit mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 009 — Full multi-criteria audit single SKU (medium)

## Input

```json
{
  "task_type": "audit",
  "sku_context": { "artikul": "55667788", "category_hint": "Женщинам > Одежда > Платья" },
  "existing_listing": {
    "title": "Платье",
    "description": "Красивое платье из качественного материала. Подходит для любого случая.",
    "keywords": ["платье", "красивое"],
    "characteristics": { "состав": "вискоза", "сезон": "лето" },
    "images_count": 3,
    "missing_size_grid": true
  },
  "audit_scope": ["title", "description", "keywords", "characteristics", "size_grid", "images_count"]
}
```

## Expected output shape

- `artifact.findings`: ≥ 6 entries (title-too-short / description-too-short / keywords-insufficient / chars-incomplete / size-grid-missing / images-insufficient)
- Each finding ranked by `severity` (block / warn / info)
- `prioritized_fixes`: top-3 highest-impact fixes (size_grid block, description expansion, keywords expansion)
- `compliance_check.status`: `flagged`
- `sources_used`: ≥ 3 (category rules + competitor benchmarks + WB content guidelines)

## Rubric

1. Factual accuracy [0.30] — все ≥ 6 issues correctly identified
2. WB-compliance [0.25] — правильная severity tier per issue
3. Conversion-orientation [0.20] — impact estimate на ranking / conversion
4. Tone match [0.15] — constructive, не damaging
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: missing more than 2 issues ИЛИ severity inversion (block issue marked warn)
