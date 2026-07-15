---
id: 005
slug: listing-pet-smart-feeder-new-category
difficulty: medium
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 005 — Generate listing для умной кормушки (новая pet-tech категория)

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Зоотовары > Кормушки автоматические",
    "product_name_user": "Кормушка автоматическая для кошек и собак с Wi-Fi",
    "key_features": ["вместимость 5 л", "Wi-Fi управление через приложение", "до 8 порций в день", "камера 1080p HD", "двусторонняя связь голосом", "питание от сети + резерв на батарейках"],
    "price_rub": 8990,
    "novelty": "Category < 200 SKU on WB, few competitors"
  },
  "tone": "promotional"
}
```

## Expected output shape

- `primary_variant.title`: ≤ 60 chars, обязательно: «кормушка автоматическая», «Wi-Fi», pet-type
- `primary_variant.description`: 2500-5000 chars, secciones: применение → tech specs → setup-flow → совместимость с приложением → safety
- `primary_variant.keywords`: 25-30 entries, novelty-keywords («умная кормушка», «кормушка с камерой») + traditional
- `uncertainty_flags`: ≥ 1 entry о low-competition keyword search-volume data
- `alternative_variants`: ≥ 2 (один pet-owner-focus, один tech-novelty-focus)
- `sources_used`: research_artifact показывает limited competitor data → flagged

## Rubric

1. Factual accuracy [0.30] — все features из input, novelty не fabricated
2. WB-compliance [0.25] — категория правила для зоотоваров
3. Conversion-orientation [0.20] — keywords + use-cases для category-builder approach
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: invented tech feature (например, «AI-распознавание питомца» если не в input)
