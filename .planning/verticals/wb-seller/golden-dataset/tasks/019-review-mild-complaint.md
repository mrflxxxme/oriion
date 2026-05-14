---
id: 019
slug: review-mild-complaint
difficulty: easy
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 019 — Review response: mild complaint (easy)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "11112222", "category_hint": "Дом и сад > Текстиль > Полотенца" },
  "review": {
    "rating": 3,
    "text": "Полотенце нормальное, но цвет на фото выглядит более насыщенным. В жизни более бледный.",
    "sentiment": "mild_negative"
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 150-300 chars
- Acknowledge feedback empathetically
- Polite explanation: цвет может различаться от monitor calibration / lighting
- Mention улучшение фото в plans (без promise specific deadline)
- Offer thank you + invite continued feedback
- No defensive tone, no admission of guilt
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — accurate explanation о цвет-monitor variance
2. WB-compliance [0.25] — no PII, no defensive, no false promise
3. Conversion-orientation [0.20] — preserve customer relationship
4. Tone match [0.15] — appreciative, не sycophantic
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: defensive ИЛИ false promise о deadline
