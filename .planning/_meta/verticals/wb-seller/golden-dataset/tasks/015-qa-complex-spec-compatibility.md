---
id: 015
slug: qa-complex-spec-compatibility
difficulty: medium
primary_task: customer-qa
agent_archetype: wb-listing-writer
archetype_path: coordinator → researcher → listing_writer (customer-qa mode)
created_by: founder
created_at: 2026-05-14
adversarial: false
last_evaluated: null
---

# Task 015 — Customer Q&A compatibility complex spec (medium)

## Input

```json
{
  "task_type": "customer-qa",
  "sku_context": {
    "artikul": "55667799",
    "category_hint": "Электроника > Аксессуары > Зарядные устройства",
    "product_features": ["мощность 65W", "USB-C PD 3.0", "GaN технология", "1× USB-C + 2× USB-A"]
  },
  "customer_question": "У меня MacBook Pro 14 (2023) — для него рекомендую 96W. Подойдёт ли ваш зарядник 65W?",
  "tone": "professional-friendly"
}
```

## Expected output shape

- `artifact.response_text`: 250-450 chars
- Factual: 65W будет заряжать, но медленнее заводского 96W (особенно при нагрузке)
- Honest assessment — не пытается продать «всё ОК», объясняет nuance
- Suggests подходит для daily use / travel, но для full-load workflows можно искать 96W+
- No invented compatibility claims
- `compliance_check.status`: `passed`
- `sources_used`: ≥ 1 (research об Apple PD compatibility)

## Rubric

1. Factual accuracy [0.30] — точное объяснение USB-C PD behavior (charge возможен, slower at load)
2. WB-compliance [0.25] — no false certification claim
3. Conversion-orientation [0.20] — honest, builds trust, не push
4. Tone match [0.15] — knowledgeable, не condescending
5. Format correctness [0.10]

## Pass threshold

- ≥ 0.75 aggregate
- Hard fail: claim «full charging same speed as Apple original» (incorrect) ИЛИ refuse to acknowledge limitation
