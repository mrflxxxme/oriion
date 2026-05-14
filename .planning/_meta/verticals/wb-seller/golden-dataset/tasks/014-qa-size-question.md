---
id: 014
slug: qa-size-question
difficulty: easy
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 014 — Customer Q&A size-вопрос (easy)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": {
    "artikul": "98765432",
    "category_hint": "Женщинам > Одежда > Платья",
    "product_features": ["вискоза 95% + эластан 5%"],
    "size_grid": {
      "S": { "chest_cm": 88, "waist_cm": 68, "hips_cm": 94, "length_cm": 110 },
      "M": { "chest_cm": 92, "waist_cm": 72, "hips_cm": 98, "length_cm": 112 }
    }
  },
  "customer_question": "Здравствуйте, я ношу 44 русский размер, объём груди 90 см. Какой размер мне выбрать?",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 150-300 chars, точная size-recommendation (M based on chest 90 → M chest 92)
- Mention что вискоза + эластан немного тянется → comfortable fit
- Suggest проверить размерную сетку в карточке
- No bold claim about «exactly fits» без disclaimers
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — корректный matching customer measurements к size grid
2. WB-compliance [0.25]
3. Conversion-orientation [0.20] — confidence-building без overclaim
4. Tone match [0.15]
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: wrong size recommended (e.g., S вместо M)
