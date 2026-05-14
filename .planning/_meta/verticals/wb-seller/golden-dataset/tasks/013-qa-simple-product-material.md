---
id: 013
slug: qa-simple-product-material
difficulty: easy
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 013 — Customer Q&A простой material-вопрос (easy)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": {
    "artikul": "12345678",
    "category_hint": "Дом и сад > Текстиль > Полотенца",
    "product_features": ["100% хлопок", "плотность 480 г/м²", "размер 70x140 см"]
  },
  "customer_question": "Здравствуйте! Подскажите, из какого материала это полотенце? Из синтетики не подойдёт.",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 100-300 chars, factual answer (100% хлопок), reassures customer
- No fabricated certifications
- No defensive tone
- No comparative с конкурентами
- `compliance_check.status`: `passed`
- Russian-only output

## Rubric

1. Factual accuracy [0.30] — only product_features info used; no invented properties
2. WB-compliance [0.25] — no medical / certification claims без proof
3. Conversion-orientation [0.20] — reassurance + invite к покупке (без push)
4. Tone match [0.15] — professional-friendly, polite
5. Format correctness [0.10] — plain text, no markdown

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: invented material claim ИЛИ defensive tone ИЛИ English text
