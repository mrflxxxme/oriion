---
id: 017
slug: qa-cross-product-comparison
difficulty: medium
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 017 — Customer Q&A cross-product comparison (medium)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": {
    "artikul": "12121212",
    "category_hint": "Дом и сад > Кухня > Сковороды",
    "product_features": ["диаметр 28 см", "антипригарное покрытие гранит", "индукция совместима", "толщина дна 5 мм"]
  },
  "other_seller_skus_in_account": [
    { "artikul": "13131313", "diameter_cm": 24, "coating": "тефлон", "indices_compatible": false },
    { "artikul": "14141414", "diameter_cm": 28, "coating": "керамика", "induction_compatible": true }
  ],
  "customer_question": "У вас три сковороды 24, 28 и 28 — что лучше для индукции и для семьи 4 человек?",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 400-650 chars
- Сравнительная таблица (text-based, no markdown) — диаметр / покрытие / индукция-совместимость
- Recommendation: 28 см подходят для семьи 4; среди двух 28-см → опция индукции зависит от плиты пользователя
- Honest tradeoff: гранит durability vs керамика price
- No external competitor comparison
- Recommend research-cited (не personal opinion)
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — точное сопоставление 3 SKU features
2. WB-compliance [0.25] — only own SKUs cited, no external comparison
3. Conversion-orientation [0.20] — helps customer decide, не push к dearest
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: comparison с конкурентом, fabricated coating-claim
