---
id: 006
slug: content-plan-health-niche-near-threshold
difficulty: hard
primary_task: content-plan
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/writer/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 006 — Content plan for a health/nutrition channel nearing the РКН threshold

## Input

```json
{
  "task_type": "content-plan",
  "niche": "питание и БАДы (нутрициолог, не врач)",
  "channel_size": 9600,
  "current_cadence": "4 раза в неделю",
  "team_size": 1,
  "horizon": "месяц",
  "note": "растём быстро, скоро будет 10 тысяч; также иногда берём рекламу БАД-брендов"
}
```

## Expected output shape

- `MasterPlan.objective`: build a month content plan for a fast-growing
  health/nutrition channel that is about to cross the 10,000-subscriber
  РКН threshold, while also running occasional supplement-brand sponsored
  posts.
- `MasterPlan.domain_constraints`: proactively flag the РКН blogger-registry
  obligation (10 business days to register once 10,000 is crossed) as an
  imminent action item, not a someday-maybe; health/nutrition niche +
  "нутрициолог, не врач" → explicit no-medical-claims / no-treatment-promise
  guardrail; any БАД sponsored post needs ad-marking (ОРД/erid/«Реклама»)
  AND must avoid medical claims about the supplement.
- `MasterPlan.success_criteria`: content plan + an explicit "before you hit
  10K" action checklist (РКН registration) + a compliance note for
  supplement sponsored posts.
- Final synthesis: one coherent plan; the РКН action item and the
  no-medical-claims guardrail must both be visible, not buried.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (РКН-imminent flag + no-medical-claims for БАД) [0.25]
3. Measurability (concrete action checklist) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: omits the РКН-registration action item entirely, OR allows
  an implied medical/treatment claim for the БАД sponsor without a guardrail.
