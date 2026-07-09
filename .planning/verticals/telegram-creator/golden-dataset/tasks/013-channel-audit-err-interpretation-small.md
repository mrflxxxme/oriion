---
id: 013
slug: channel-audit-err-interpretation-small
difficulty: easy
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → community-manager/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 013 — Interpret ERR for a small channel

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 4500,
  "recent_err": "18%",
  "question": "это хороший показатель или нет?"
}
```

## Expected output shape

- `MasterPlan.objective`: interpret the given 18% ERR for a 4,500-subscriber
  channel against the correct size-relative benchmark, not in a vacuum.
- `MasterPlan.domain_constraints`: correct benchmark band for <10K
  subscribers is 10-30% ERR (per domain-brief §3.4) — 18% sits comfortably
  within a healthy range; must not misapply the 10K-100K band (5-15%) to
  this channel.
- `MasterPlan.success_criteria`: clear verdict (healthy / not) with the
  correct benchmark cited, plain-language explanation for the author.
- Final synthesis: a short, clear answer — no unnecessary hedging when the
  data is actually reassuring.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct benchmark band applied) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: applies the 10K-100K benchmark band (5-15%) to a
  4,500-subscriber channel, mis-flagging a healthy 18% ERR as weak.
