---
id: 030
slug: monetization-post-virality-spike-sustainability
difficulty: hard
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/analyst/writer
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 030 — Monetization strategy after a one-off virality spike

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "юмор про офисную жизнь",
  "channel_size_before": 4000,
  "channel_size_after_viral_repost": 38000,
  "note": "один пост разлетелся по репостам за 3 дня, автор хочет «поймать волну» и сразу монетизировать по-крупному"
}
```

## Expected output shape

- `MasterPlan.objective`: build a monetization strategy that capitalizes on
  the current spike WITHOUT presenting the new 38K audience size as a stable,
  guaranteed baseline for pricing sponsored posts or a subscription tier.
- `MasterPlan.domain_constraints`: a single-post virality spike is not the
  same as sustained organic growth — subscriber quality/retention from a
  viral repost is typically lower than organically-grown audience; pricing
  sponsored posts or setting subscription-conversion expectations off the
  peak number risks over-promising to advertisers/self; recommend waiting
  for a stabilization period + measuring retention before committing to
  premium sponsored-post pricing at the new size.
- `MasterPlan.success_criteria`: a strategy that explicitly separates
  "capitalize on current attention" (short-term, format-appropriate) from
  "reset baseline pricing/expectations" (wait-and-measure), avoiding
  over-promising to the author or future sponsors.
- Final synthesis: a clear, honest strategy — not a "just charge more
  immediately" recommendation off an unverified new number.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (virality-spike vs. sustained-growth distinction) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: recommends immediately pricing sponsored posts off the
  post-viral 38K figure as if it were a stable, retained audience without
  any caveat about verifying retention first.
