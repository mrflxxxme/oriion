---
id: 016
slug: channel-audit-crossing-tier-benchmark
difficulty: medium
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 016 — Re-benchmark a channel that just crossed from micro to mid-tier

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 11000,
  "err_now": "13%",
  "note": "месяц назад было 9500 подписчиков и ERR 22%, автор переживает, что «вовлечённость упала в 1.7 раза»"
}
```

## Expected output shape

- `MasterPlan.objective`: correctly interpret a 22%→13% ERR drop that
  coincides with the channel crossing the 10K threshold, distinguishing
  "genuinely worse content performance" from "expected benchmark shift when
  moving from the <10K band to the 10K-100K band."
- `MasterPlan.domain_constraints`: 22% was within the <10K healthy band
  (10-30%); 13% is within the 10K-100K healthy band (5-15%) — both numbers
  can be healthy for their respective tiers; the raw percentage drop alone
  is not evidence of a real problem.
- `MasterPlan.success_criteria`: analysis that reassures with the correct
  benchmark reasoning rather than either dismissing the author's concern
  unexplained or validating unwarranted panic.
- Final synthesis: clear, benchmark-grounded reassurance (or a genuine flag,
  if the analysis actually finds one — but the given numbers do not
  warrant alarm).

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (tier-shift benchmark reasoning) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: treats the raw 1.7x percentage-point drop as proof of a
  real engagement problem without accounting for the benchmark-band shift.
