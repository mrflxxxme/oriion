---
id: 018
slug: channel-audit-churn-spike-sponsor-complaint
difficulty: hard
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → community-manager/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 018 — Diagnose a churn spike coinciding with reader complaints about a sponsored post

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 54000,
  "unsubscribe_spike": "в 6 раз выше обычного за 2 дня после публикации спонсорского поста",
  "reader_comments_sample": [
    "опять реклама без пометки, надоело",
    "перестал быть похож на личный канал, сплошная реклама"
  ]
}
```

## Expected output shape

- `MasterPlan.objective`: diagnose the churn spike as connected to reader
  perception of the sponsored post (frequency and/or missing ad-marking),
  not treat it as an unrelated coincidence.
- `MasterPlan.domain_constraints`: reader comments explicitly flag a missing
  ad-marking perception ("опять реклама без пометки") — this is a compliance
  signal (ФЗ-38 marking requirement), not just a tone complaint, and should
  trigger a recommendation to audit the actual post for marking compliance,
  not just "post less ads" as a vague fix.
- `MasterPlan.success_criteria`: diagnosis connecting churn to both (a)
  sponsored-content frequency/fit and (b) a compliance-audit action item for
  the flagged post's ad-marking.
- Final synthesis: coherent diagnosis + two concrete action items (marking
  audit + sponsored-content cadence review).

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (connects churn to compliance signal, not just vibes) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: ignores the ad-marking complaint signal entirely and treats
  this purely as a generic "audience is unhappy" issue.
