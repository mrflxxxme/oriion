---
id: 016
slug: qa-dispute-undelivered
difficulty: medium
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 016 — Customer Q&A dispute undelivered товар (medium)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": { "artikul": "44556677", "category_hint": "Электроника > Аудиотехника > Колонки" },
  "customer_question": "Я заказал товар 5 дней назад, статус «в пути» но в личном кабинете уже неделя нет движения. Где мой товар? Хочу возврат денег!",
  "context": "order_status_actual: in_transit, tracking_event_last: 4 days ago at sort hub",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 300-500 chars
- Acknowledge frustration empathetically (no defensiveness)
- Explain что seller-side контроль ограничен — WB логистика отвечает за tracking
- Suggest concrete steps: (1) check personal cabinet для актуального статуса, (2) contact WB Support для investigation, (3) seller готов помочь после WB Support response
- No false promise («обязательно доставим завтра»)
- No admission of seller-fault если не доказан (delivery — WB-side)
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — корректное разграничение seller-vs-WB responsibility
2. WB-compliance [0.25] — no false delivery promise, no PII exposed
3. Conversion-orientation [0.20] — preserves relationship, не abandon claim
4. Tone match [0.15] — empathetic + factual, not patronizing
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: admit fault когда не fault seller, OR dismissive tone, OR no actionable next-step
