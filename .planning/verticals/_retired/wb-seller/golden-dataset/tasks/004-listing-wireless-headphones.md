---
id: 004
slug: listing-wireless-headphones
difficulty: medium
primary_task: listing-generation
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 004 — Generate listing для беспроводных наушников TWS

## Input

```json
{
  "task_type": "listing-generation",
  "sku_context": {
    "category_hint": "Электроника > Аудиотехника > Наушники беспроводные",
    "product_name_user": "Наушники беспроводные TWS с шумоподавлением",
    "key_features": ["Bluetooth 5.3", "ANC активное шумоподавление", "время работы 8ч + 30ч с кейсом", "IPX5 защита от пота", "сенсорное управление"],
    "color": "белый",
    "price_rub": 3990,
    "brand": "TBD_BRAND_NAME"
  },
  "tone": "promotional"
}
```

## Expected output shape

- `primary_variant.title`: ≤ 60 chars, technical specs приоритет («TWS», «ANC», «Bluetooth 5.3»)
- `primary_variant.description`: 2500-5000 chars, структурированные characteristics (audio specs / battery / connectivity / водозащита / комплектация)
- `primary_variant.keywords`: 25-30 entries, technical + use-case (для спорта / для работы / для звонков)
- Compatibility note (iOS + Android) — обязательно
- `alternative_variants`: 2 alternatives (один шумоподавление-focus, один battery-life-focus)
- `compliance_check.status`: `passed` — no medical claims о слухе, no comparative с named competitors
- Brand placeholder `TBD_BRAND_NAME` preserved (per PLACEHOLDERS.md workflow)

## Rubric

1. Factual accuracy [0.30] — technical specs точно из input, no invention
2. WB-compliance [0.25] — electronics category requires спецификации, нет medical claims
3. Conversion-orientation [0.20] — keywords cover technical + use-cases
4. Tone match [0.15] — promotional но без false superlative
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: invented spec (не из input), comparative claim с конкурентом, TBD_BRAND_NAME заменён на выдуманное имя
