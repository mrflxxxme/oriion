---
id: 002
slug: listing-mens-tshirt-single-color
difficulty: easy
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 002 — Generate listing для мужской однотонной футболки

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Мужчинам > Одежда > Футболки",
    "product_name_user": "Футболка мужская базовая хлопок",
    "key_features": ["100% хлопок", "круглый ворот", "цвет чёрный", "плотность 180 г/м²"],
    "size": "L (один размер)",
    "price_rub": 590
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `primary_variant.title`: ≤ 60 chars, ключевые слова («футболка мужская», «хлопок», «черный»)
- `primary_variant.description`: 1500-3500 chars, секции (материал → крой → плотность → размерная рекомендация → уход)
- `primary_variant.keywords`: 18-28 entries, gender + material + fit terms
- `compliance_check.status`: `passed`
- Размерная сетка mentioned, хотя single-size (L) — рекомендация по соответствию RU sizes

## Rubric

1. Factual accuracy [0.30]
2. WB-compliance [0.25] — apparel-категория правила
3. Conversion-orientation [0.20] — search terms cover «мужская футболка хлопок»
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: gender-mismatch (если writer пишет «женская»), размерная-сетка absent для apparel category
