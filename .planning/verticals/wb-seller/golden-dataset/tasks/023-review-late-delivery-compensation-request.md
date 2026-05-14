---
id: 023
slug: review-late-delivery-compensation-request
difficulty: medium
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 023 — Review response: late delivery + компенсация request (medium)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "99990000", "category_hint": "Красота > Косметика > Уход" },
  "review": {
    "rating": 2,
    "text": "Заказ шёл 8 дней. Это уже подарок ко дню рождения подруги — не дождалась. Требую компенсации, иначе оставлю плохой отзыв везде.",
    "sentiment": "negative_with_demand"
  },
  "context": { "delivery_was_FBO": true, "promised_3_5_days": true, "actual_8_days": true },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 350-550 chars
- Empathetic acknowledge — пропустили важную дату для подруги
- Honest framing: компенсация за delivery — WB-side prerogative (можно подать в WB Support по факту просрочки), seller не controls delivery directly
- Не bow к threats (без compromise dignity)
- Offer goodwill gesture в рамках seller-control (например, дополнительный сэмпл при next purchase — если такое возможно), but no monetary promise
- Suggest WB Support claim для delivery compensation
- No admission seller-fault для FBO
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — корректно отделить seller responsibility vs WB delivery
2. WB-compliance [0.25] — no false promise, no PII
3. Conversion-orientation [0.20] — preserve dignity без caving к threat
4. Tone match [0.15] — empathetic but firm
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: monetary compensation promise OR bow к threat OR admit seller-fault
