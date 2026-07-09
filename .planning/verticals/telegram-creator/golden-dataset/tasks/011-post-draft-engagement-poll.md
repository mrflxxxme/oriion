---
id: 011
slug: post-draft-engagement-poll
difficulty: medium
primary_task: post-drafting
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 011 — Draft an engagement post with a poll

## Input

```json
{
  "task_type": "post-drafting",
  "niche": "личные финансы",
  "rubric": "вовлечение пятницы",
  "goal": "поднять просевшую вовлечённость за последние 2 недели",
  "current_err": "3%",
  "channel_size": 12000
}
```

## Expected output shape

- `MasterPlan.objective`: produce an engagement-focused post (poll/question)
  aimed at reversing a recent ERR dip for a 12K personal-finance channel.
- `MasterPlan.domain_constraints`: 3% ERR is below the 5-15% healthy band for
  a 10K-100K channel (per domain-brief §3.4) — this should inform the
  urgency/framing, not be ignored; poll topic must be genuinely relevant to
  the niche, not generic engagement-bait unrelated to content.
- `MasterPlan.success_criteria`: draft post + poll options, explicit
  rationale for why this format should lift engagement.
- Final synthesis: ready-to-publish post + poll, with the benchmark context
  noted for the author (not just silently baked into KPI thinking).

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (ERR benchmark awareness) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: treats 3% ERR as fine/healthy for this channel size (misreads
  the benchmark), or proposes a poll unrelated to the channel's niche.
