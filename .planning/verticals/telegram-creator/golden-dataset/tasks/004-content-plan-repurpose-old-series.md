---
id: 004
slug: content-plan-repurpose-old-series
difficulty: medium
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer/community-manager
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 004 — Content plan built around repurposing an old post series

## Input

```json
{
  "task_type": "content-plan",
  "niche": "продуктивность для фрилансеров",
  "channel_size": 15000,
  "current_cadence": "3 раза в неделю",
  "team_size": 1,
  "horizon": "2 недели",
  "note": "год назад была серия из 8 постов про тайм-менеджмент, хочу переиспользовать материал вместо написания нового"
}
```

## Expected output shape

- `MasterPlan.objective`: build a 2-week plan that repurposes an existing
  8-post time-management series into fresh formats instead of writing new
  material from scratch.
- `MasterPlan.domain_constraints`: repurposing must transform, not just
  repost verbatim (reader-fatigue risk if identical); mix formats (post
  digest, story teaser, follow-up); channel at 15K — РКН already applicable,
  confirm registration status if sponsored content appears (not relevant
  here but worth noting as standing constraint).
- `MasterPlan.success_criteria`: 2-week plan mapping old-series items to
  new formats, at least one digest post aggregating the series, no
  1:1 verbatim repost.
- Final synthesis: coherent 2-week calendar referencing which old post feeds
  which new piece.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (repurposing ≠ verbatim repost) [0.25]
3. Measurability (old-item → new-format mapping) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: plan is just "repost the 8 old posts unchanged."
