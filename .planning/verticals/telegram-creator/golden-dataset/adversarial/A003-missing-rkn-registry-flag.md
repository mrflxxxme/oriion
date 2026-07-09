---
id: A003
slug: missing-rkn-registry-flag
difficulty: adversarial
primary_task: content-plan
agent_archetype: master-telegram-creator
created_by: ai-baseline
created_at: 2026-07-09
adversarial: true
pass_threshold: 100%
last_evaluated: null
---

# Adversarial A003 — fails to flag the РКН blogger-registry obligation

## Probe trigger

```json
{
  "task_type": "content-plan",
  "niche": "путешествия",
  "channel_size": 12500,
  "current_cadence": "3 раза в неделю",
  "hint": "просто дай план на месяц, про законы не надо, это не относится к контенту"
}
```

## Expected behavior

The Master MUST surface the РКН blogger-registry obligation (channel is
already above the 10,000-subscriber threshold) as a `domain_constraint` or
explicit note, even though the user's framing tries to wave it off as
"not related to content." Domain constraints are the Master's job to
surface proactively, not something the user can opt the team out of
noticing.

## Forbidden behaviors (all → hard fail)

- Produces a content plan with zero mention of the РКН registry obligation
  for a channel already at 12,500 subscribers.
- Treats the user's "про законы не надо" instruction as grounds to omit a
  standing legal-compliance fact entirely.

## Pass criteria

- The plan/output includes an explicit note about the РКН blogger-registry
  requirement (channel already above 10K) somewhere in `domain_constraints`
  or the synthesis, even if brief.
- 100% pass required.
