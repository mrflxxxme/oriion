---
id: 021
slug: review-legitimate-defect-return-offer
difficulty: medium
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 021 — Review response: legitimate defect → return offer (medium)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "55556666", "category_hint": "Электроника > Аудиотехника > Колонки" },
  "review": {
    "rating": 1,
    "text": "Колонка пришла в нерабочем состоянии — не включается даже после полной зарядки. Похоже, заводской брак. Огорчён.",
    "sentiment": "strong_negative",
    "defect_credible": true
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 300-500 chars
- Empathetic acknowledgement — заводской брак неприятен, понимаем расстройство
- Concrete next steps: оформить возврат через WB Personal Cabinet (link к WB return-process), либо обмен если есть наличие
- Acknowledge defect возможность даже у quality-control
- Offer follow-up communication через WB messaging если требуется
- No admission of universal-fault («наш товар часто бракованный»)
- `compliance_check.status`: `passed`

## Rubric

1. Factual accuracy [0.30] — корректный WB return process referenced
2. WB-compliance [0.25] — no PII, no over-promise («заменим в течение часа»)
3. Conversion-orientation [0.20] — turn negative в acceptable resolution
4. Tone match [0.15] — sincere, не corporate-bot
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: deny defect ИЛИ no actionable next-step OR claim о QC процессах
