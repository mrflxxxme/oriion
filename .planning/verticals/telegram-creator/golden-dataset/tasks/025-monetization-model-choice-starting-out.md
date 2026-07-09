---
id: 025
slug: monetization-model-choice-starting-out
difficulty: easy
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 025 — Choose a monetization model for a channel just starting out

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "виниловые пластинки и музыкальные находки",
  "channel_size": 3200,
  "engagement": "хорошая, читатели активно комментируют",
  "question": "с чего начать монетизацию?"
}
```

## Expected output shape

- `MasterPlan.objective`: recommend a realistic starting monetization path
  for a 3,200-subscriber engaged niche channel.
- `MasterPlan.domain_constraints`: at this size, sponsored posts are
  possible (entry threshold cited as low as 1,000-1,500 subscribers per
  domain-brief §3.2) but revenue will be modest; Telegram Stars paid-post/
  subscription is a low-friction option to introduce alongside; the
  official Telegram ad-revenue-share program and large-brand sponsorships
  are more realistic once the channel is larger — sequence the
  recommendation accordingly instead of jumping straight to "get big brand
  deals."
- `MasterPlan.success_criteria`: a sequenced monetization roadmap (start
  with X, add Y once size/engagement grows), no guaranteed revenue figure
  presented as certain for this specific channel.
- Final synthesis: clear, sequenced, realistic monetization starting point.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct model sequencing for channel size) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: promises a specific guaranteed monthly revenue figure for
  this channel.
