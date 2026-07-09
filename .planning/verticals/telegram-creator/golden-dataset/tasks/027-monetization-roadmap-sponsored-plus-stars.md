---
id: 027
slug: monetization-roadmap-sponsored-plus-stars
difficulty: medium
primary_task: monetization-and-repurposing
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 027 — Build a mixed monetization roadmap (sponsored posts + Stars subscription)

## Input

```json
{
  "task_type": "monetization-and-repurposing",
  "niche": "инди-разработка игр",
  "channel_size": 15000,
  "current_monetization": "изредка берём разовые спонсорские посты",
  "goal": "добавить более предсказуемый доход помимо разовых интеграций"
}
```

## Expected output shape

- `MasterPlan.objective`: design a roadmap combining continued sponsored
  posts with a new Telegram Stars paid-subscription tier for recurring
  revenue, for a 15K niche channel.
- `MasterPlan.domain_constraints`: Stars subscription payout mechanics
  (creator keeps 100% of Stars value, ~3-week withdrawal hold, 1,000-Star
  minimum payout per domain-brief §3.2) should inform the pitch to the
  author (manage expectations on cash-flow timing); ad-marking still applies
  to sponsored posts independent of the new subscription tier; no specific
  subscriber-conversion-rate guarantee for the paid tier.
- `MasterPlan.success_criteria`: a roadmap with both revenue streams, a
  note on Stars payout timing/mechanics, and NO fabricated conversion-rate
  promise for the new paid tier.
- Final synthesis: coherent roadmap combining both streams realistically.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (accurate Stars mechanics + continued ad-marking) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: states or implies a specific guaranteed subscriber-to-paid
  conversion percentage, or gets the Stars payout mechanics wrong (e.g.
  claims Telegram takes a cut of Stars revenue).
