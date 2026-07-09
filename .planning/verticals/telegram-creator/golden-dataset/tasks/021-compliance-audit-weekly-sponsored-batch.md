---
id: 021
slug: compliance-audit-weekly-sponsored-batch
difficulty: medium
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 021 — Compliance audit across a week of sponsored posts

## Input

```json
{
  "task_type": "compliance-audit",
  "posts": [
    { "id": "p1", "text": "Реклама. ООО Спорт+, ИНН 7701234567, erid: 2VtzXXX1. Кроссовки со скидкой.", "is_sponsored": true },
    { "id": "p2", "text": "Попробовал новый протеин от бренда Y, вкус огонь!", "is_sponsored": true },
    { "id": "p3", "text": "Сегодня делюсь мыслями про мотивацию (не реклама).", "is_sponsored": false }
  ]
}
```

## Expected output shape

- `MasterPlan.objective`: audit a batch of 3 posts for ad-marking compliance,
  correctly distinguishing compliant, non-compliant, and not-applicable.
- `MasterPlan.domain_constraints`: p1 is fully compliant (label + advertiser
  + erid all present); p2 is sponsored but has NO marking at all despite
  being flagged `is_sponsored: true` — the biggest risk; p3 is not sponsored,
  no marking required.
- `MasterPlan.success_criteria`: per-post verdict (p1 ok, p2 flagged/block,
  p3 not-applicable), with p2 given the most attention since it's the actual
  violation.
- Final synthesis: a clear per-post table/summary, p2 prioritized as the
  actionable risk.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct per-post classification) [0.25]
3. Measurability (per-post verdicts) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: misclassifies p1 (compliant) as non-compliant, or fails to
  flag p2 (sponsored, unmarked) as a violation.
