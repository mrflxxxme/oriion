---
id: 020
slug: review-shipping-delay-no-seller-fault
difficulty: easy
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 020 — Review response: shipping delay без seller-fault (easy)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "33334444", "category_hint": "Электроника > Аксессуары > Кабели" },
  "review": {
    "rating": 2,
    "text": "Заказ шёл 12 дней вместо обычных 3-5. Конечно, потом всё пришло, но осадочек неприятный.",
    "sentiment": "negative"
  },
  "context": { "delivery_actual_days": 12, "delivery_was_FBO": true },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 200-400 chars
- Acknowledge неудобство
- Explain что delivery — WB-side ответственность (FBO logistics), seller не контролирует точные сроки
- No blame customer, no blame WB explicitly
- Thank for ratings/feedback, signal willingness improve experience
- No admission of seller-fault для FBO delivery
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — корректное FBO logistics responsibility framing
2. WB-compliance [0.25] — no PII, no negative WB-mention, no false promise
3. Conversion-orientation [0.20] — preserve relationship
4. Tone match [0.15] — empathetic + factual
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: blame WB explicitly OR admit seller-fault для FBO delivery
