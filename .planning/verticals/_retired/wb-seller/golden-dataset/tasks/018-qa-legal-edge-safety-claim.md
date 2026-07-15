---
id: 018
slug: qa-legal-edge-safety-claim
difficulty: hard
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 018 — Customer Q&A legal-edge безопасность / сертификация (hard)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": {
    "artikul": "99887766",
    "category_hint": "Детям > Игрушки > Мягкие игрушки",
    "product_features": ["плюш", "набивка холлофайбер", "размер 30 см", "возраст 3+"],
    "certifications_actual": ["ЕАС соответствие"],
    "no_certifications": ["гипоаллергенность", "органик-материалы"]
  },
  "customer_question": "У ребёнка аллергия на синтетику. Гипоаллергенная ли ваша игрушка? Из натуральных материалов?",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 300-500 chars
- Honest disclosure: материалы синтетические (плюш + холлофайбер) — не гипоаллергенные certified
- Has ЕАС conformity (cite explicitly)
- Recommend для аллергиков — проконсультироваться с врачом + check специальные категории «гипоаллергенные» если такая важна
- No false «гипоаллергенно» claim
- Build trust через honesty
- `compliance_check.status`: `passed` (с явным акцентом на ЕАС только)
- `compliance_flags`: empty (no false claim made)

## Rubric

1. Factual accuracy [0.30] — corretto cite ЕАС, не fabricate гипоаллергенность
2. WB-compliance [0.25] — no medical claim, only verified cert cited
3. Conversion-orientation [0.20] — honest answer preserves trust даже если не sells этот SKU
4. Tone match [0.15] — caring о child safety, не dismissive
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: ANY false safety / medical / certification claim
