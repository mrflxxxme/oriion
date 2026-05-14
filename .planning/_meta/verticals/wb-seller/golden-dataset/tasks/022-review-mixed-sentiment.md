---
id: 022
slug: review-mixed-sentiment
difficulty: medium
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 022 — Review response: mixed sentiment (medium)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "77778888", "category_hint": "Дом и сад > Текстиль > Постельное бельё" },
  "review": {
    "rating": 4,
    "text": "Качество ткани отличное, цвет как на фото, доставка быстрая. Единственное — упаковка пришла мятая, но содержимое целое. Учитывая цену — отлично.",
    "sentiment": "mostly_positive_with_specific_negative"
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 200-350 chars
- Lead с positive acknowledgement (благодарность за detailed review)
- Address packaging issue: упаковка приходит через WB logistics — иногда страдает в транзите; if содержимое целое — это и есть основной test
- Note: упоминание что seller тестирует разные packaging options для лучшей resilience
- Invite повторно если будут вопросы
- No defensive, no dismissal частичного negative
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — packaging-vs-content distinction логичен
2. WB-compliance [0.25] — no PII, balanced tone
3. Conversion-orientation [0.20] — reinforce positive + acknowledge gap
4. Tone match [0.15] — appreciative
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: ignore negative часть ИЛИ over-apologize для packaging issue (it's a minor)
