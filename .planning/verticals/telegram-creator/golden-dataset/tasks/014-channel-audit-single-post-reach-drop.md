---
id: 014
slug: channel-audit-single-post-reach-drop
difficulty: easy
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → community-manager/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 014 — Diagnose a single post's reach drop

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 6000,
  "average_reach_last_10_posts": 4200,
  "last_post_reach": 1800,
  "last_post_time": "воскресенье, 23:40"
}
```

## Expected output shape

- `MasterPlan.objective`: diagnose why one specific post underperformed
  relative to the channel's own recent average, not the channel overall.
- `MasterPlan.domain_constraints`: reach of 1,800 vs an average of 4,200 is a
  ~57% drop for that single post; posting time (Sunday 23:40) is a plausible
  contributing factor worth flagging as a hypothesis, not stated as certain
  fact without more data.
- `MasterPlan.success_criteria`: a diagnosis that distinguishes "this one
  post" from "the whole channel," at least one plausible hypothesis
  (timing), and a suggestion to test (e.g. vary posting time) rather than a
  guaranteed fix.
- Final synthesis: concise diagnosis + one actionable next step.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (single-post vs channel-level framing) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: presents the timing hypothesis as a certain, proven cause
  rather than a plausible factor to test.
