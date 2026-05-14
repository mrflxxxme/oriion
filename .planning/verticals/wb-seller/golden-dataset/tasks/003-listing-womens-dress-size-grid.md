---
id: 003
slug: listing-womens-dress-size-grid
difficulty: medium
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 003 — Generate listing для женского платья с размерной сеткой XS-XXL

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Женщинам > Одежда > Платья > Повседневные",
    "product_name_user": "Платье миди трикотажное офисное",
    "key_features": ["вискоза 95% + эластан 5%", "длина миди", "силуэт прямой", "цвет тёмно-синий"],
    "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
    "price_rub": 2490
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `primary_variant.title`: ≤ 60 chars, includes «платье миди» + основной keyword
- `primary_variant.description`: 2000-4500 chars, размерная сетка с конкретными измерениями (обхват груди / талии / бёдер / длина) per size
- `primary_variant.keywords`: 20-30 entries
- Размерная сетка structured в description ИЛИ specifications field
- `alternative_variants`: ≥ 1 alternative с tone tweak
- `compliance_check.status`: `passed`
- `sources_used`: ≥ 3 indices (category rules + competitor benchmarks + keyword research)

## Rubric

1. Factual accuracy [0.30] — состав ткани, длина, силуэт точно из input
2. WB-compliance [0.25] — размерная сетка обязательна для категории «Платья»; char limits
3. Conversion-orientation [0.20] — keywords cover style + season + occasion
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: размерная сетка absent ИЛИ inconsistent across 6 sizes
