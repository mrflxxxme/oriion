---
id: 024
slug: review-defamatory-fraud-claim-escalation
difficulty: hard
primary_task: review-response
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (review-response mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 024 — Review response: defamatory / fraud-claim → escalation path (hard)

## Input

```json
{
  "task_type": "review-response",
  "sku_context": { "artikul": "12121234", "category_hint": "Дом и сад > Кухня > Посуда" },
  "review": {
    "rating": 1,
    "text": "ЭТОТ ПРОДАВЕЦ МОШЕННИК! Прислал ПОДДЕЛКУ известного бренда! Тарелки бьются от каждого прикосновения. Всех предупреждаю — НЕ ПОКУПАТЬ!",
    "sentiment": "defamatory",
    "claims_unverified": ["мошенник", "подделка известного бренда"],
    "context": "Товар — собственный brand (не реselling известного бренда), нет evidence массового брака"
  },
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 400-600 chars
- Emit `oriion.write.legal-edge.v1` event к coordinator
- Tone: calm, factual, не emotional
- Address factual mismatch — товар не reselling известного бренда, это собственный brand; sample-quality issue not = mass-fraud
- Suggest constructive next step: contact seller для return/exchange если defect (offer this calmly)
- DO NOT engage с «мошенник» / «подделка» accusations directly — фиксируем factual rebuttal без drama
- Suggest customer escalate к WB Support если concerns persist
- Privately (через coordinator): suggest seller подаст formal claim к WB Support под раздел «недостоверные отзывы / клевета» (это WB-procedure, не угроза)
- `compliance_check.status`: `flagged` (legal-edge content)
- `compliance_flags`: `[ { "type": "legal-edge", "details": "defamatory-claim-escalation" } ]`

## Rubric

1. Factual accuracy [0.30] — корректное factual rebuttal, no emotional escalation
2. WB-compliance [0.25] — `compliance_flags` populated; escalation event emitted
3. Conversion-orientation [0.20] — preserve dignity; redirect к constructive channels
4. Tone match [0.15] — composed, не provocative
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: emotional response, OR no legal-edge flag, OR no escalation event emitted, OR admit fraud
