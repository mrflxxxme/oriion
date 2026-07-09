---
id: 020
slug: compliance-audit-missing-advertiser-inn
difficulty: easy
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 020 — Compliance audit: erid present but advertiser data incomplete

## Input

```json
{
  "task_type": "compliance-audit",
  "post_text": "Реклама. erid: 2VtzqXXXXX. Заказывайте одежду в новом онлайн-магазине — скидка 20% по коду TG20.",
  "is_sponsored": true,
  "advertiser": "не указано в посте"
}
```

## Expected output shape

- `MasterPlan.objective`: audit this post — it has the «Реклама» label and an
  erid token, but is missing the advertiser's name/INN.
- `MasterPlan.domain_constraints`: full ФЗ-38 marking requires label +
  advertiser identification (name/INN) + erid — having erid alone is
  necessary but not sufficient.
- `MasterPlan.success_criteria`: audit correctly identifies this as
  PARTIALLY compliant (not fully ok, not fully missing) and specifies
  exactly what's missing (advertiser identification).
- Final synthesis: precise partial-compliance verdict + fix.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (distinguishes partial vs full compliance) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: marks this post as fully compliant just because «Реклама»
  and an erid token are present.
