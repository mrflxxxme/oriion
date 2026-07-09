---
id: 015
slug: channel-audit-monthly-decline-trend
difficulty: medium
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → community-manager/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 015 — Diagnose a month-long engagement decline

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 42000,
  "err_trend": ["9%", "8%", "6%", "4.5%"],
  "trend_period": "последние 4 недели",
  "cadence_change": "перешли с 3 постов в неделю на 6, чтобы «расти быстрее»"
}
```

## Expected output shape

- `MasterPlan.objective`: diagnose the ERR decline trend for a 42K channel
  and connect it to the stated cadence change, not treat them as unrelated.
- `MasterPlan.domain_constraints`: 42K channel sits in the 10K-100K band —
  healthy ERR is 5-15%; the trend has dropped from 9% (healthy) to 4.5%
  (below-healthy) over 4 weeks, coinciding with doubling posting frequency —
  a plausible over-posting/quality-dilution hypothesis should be raised.
- `MasterPlan.success_criteria`: diagnosis explicitly connecting the cadence
  change to the decline (as hypothesis, with a recommended test — e.g.
  reduce cadence and observe), correct benchmark band cited.
- Final synthesis: clear diagnosis + a concrete recommendation to test.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct benchmark + cadence-quality tradeoff reasoning) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: ignores the cadence-change data point entirely, or
  recommends posting even MORE as the fix without addressing the
  correlation.
