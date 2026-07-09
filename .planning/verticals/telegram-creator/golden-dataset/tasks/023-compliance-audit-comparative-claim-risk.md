---
id: 023
slug: compliance-audit-comparative-claim-risk
difficulty: medium
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 023 — Compliance audit: comparative-advertising language risk

## Input

```json
{
  "task_type": "compliance-audit",
  "post_text": "Реклама. ИП Иванов, ИНН 770123456789, erid: 2VtzYYY9. Наш курс английского лучше и дешевле, чем у всех известных онлайн-школ!",
  "is_sponsored": true
}
```

## Expected output shape

- `MasterPlan.objective`: audit this post — marking mechanics (label +
  advertiser + erid) are present, but the copy itself contains a
  superlative/comparative claim risk.
- `MasterPlan.domain_constraints`: unsubstantiated superlatives ("лучше и
  дешевле, чем у всех") without evidence/named comparison basis are a ФЗ-38
  risk (misleading advertising / unfair comparison), independent of whether
  the marking mechanics are correct.
- `MasterPlan.success_criteria`: audit flags the marking mechanics as OK but
  the superlative claim as a separate, real risk, with a compliant rewrite
  suggestion (e.g. remove the unverifiable comparison).
- Final synthesis: two distinct findings — marking ok, content-claim risky —
  not collapsed into a single verdict.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (separates marking-mechanics from content-claim risk) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: approves the post as fully compliant solely because the
  marking mechanics (label/advertiser/erid) are present, ignoring the
  superlative-claim risk entirely.
