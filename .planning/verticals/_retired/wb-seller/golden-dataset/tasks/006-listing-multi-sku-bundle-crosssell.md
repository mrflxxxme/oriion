---
id: 006
slug: listing-multi-sku-bundle-crosssell
difficulty: hard
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 006 — Generate listings для bundle (base SKU + 3 вариации цвета + cross-sell аксессуар)

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Дом и сад > Кухня > Чайники электрические",
    "base_product": {
      "product_name_user": "Чайник электрический стеклянный 1.7L с подсветкой",
      "key_features": ["объём 1.7 L", "корпус стекло + нерж. сталь", "мощность 2200 Вт", "подсветка LED при кипении", "защита от перегрева"],
      "variations": [
        { "color": "синяя подсветка", "price_rub": 1990 },
        { "color": "зелёная подсветка", "price_rub": 1990 },
        { "color": "красная подсветка", "price_rub": 1990 }
      ]
    },
    "cross_sell_accessory": {
      "product_name_user": "Подставка для чайника силиконовая",
      "price_rub": 290
    }
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- 4 separate `primary_variant` entries (base × 3 variations + accessory) с согласованным brand-tone
- Base карточки: title, description, keywords с явным указанием color variation в `name`
- Cross-sell accessory linked через `recommended_with` reference (Wave 1+ enrichment)
- Variations: 80% shared content + 20% color-specific
- `compliance_check.status`: `passed` для всех 4
- `sources_used` references: category rules для чайников + accessory rules
- Consistency check: brand-voice unified across 4 carts

## Rubric

1. Factual accuracy [0.30] — все 4 entries factually consistent с input
2. WB-compliance [0.25] — char limits соблюдены × 4
3. Conversion-orientation [0.20] — cross-sell hook прозрачен (упоминание подставки в base описании)
4. Tone match [0.15] — unified brand-voice
5. Format correctness [0.10] — structured 4-entry response

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: brand-voice drift между variations, accessory листинг inconsistent с base, hallucinated cross-sell features
