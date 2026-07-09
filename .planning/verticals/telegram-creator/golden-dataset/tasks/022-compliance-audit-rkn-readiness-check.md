---
id: 022
slug: compliance-audit-rkn-readiness-check
difficulty: medium
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 022 — РКН blogger-registry readiness check

## Input

```json
{
  "task_type": "compliance-audit",
  "channel_size_history": [
    { "date": "2026-06-01", "subscribers": 9200 },
    { "date": "2026-06-20", "subscribers": 10150 },
    { "date": "2026-07-08", "subscribers": 10800 }
  ],
  "question": "нужно ли нам что-то делать по закону из-за роста подписчиков?"
}
```

## Expected output shape

- `MasterPlan.objective`: determine whether the channel has crossed the
  10,000-subscriber РКН blogger-registry threshold and what the author must
  do.
- `MasterPlan.domain_constraints`: the channel crossed 10,000 on/around
  2026-06-20 (per the given history); the registration deadline is 10
  business days from crossing the threshold — as of 2026-07-08 (~18 days
  later) the deadline has likely already passed, which should be flagged as
  urgent, not a someday item.
- `MasterPlan.success_criteria`: a clear yes/no answer (yes, action needed),
  the deadline math shown, and an explicit "this is likely already overdue,
  act now" urgency framing — not just generic "you should register
  eventually" advice.
- Final synthesis: urgent, concrete action item.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct threshold-crossing date + deadline math) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: fails to recognize the threshold was already crossed, or
  presents the registration as optional/someday rather than a legal
  obligation with an (likely already passed) deadline.
