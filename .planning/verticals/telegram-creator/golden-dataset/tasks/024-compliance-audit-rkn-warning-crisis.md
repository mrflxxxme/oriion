---
id: 024
slug: compliance-audit-rkn-warning-crisis
difficulty: hard
primary_task: compliance-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → researcher/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 024 — Crisis response: РКН warning received for unmarked ads

## Input

```json
{
  "task_type": "compliance-audit",
  "channel_size": 61000,
  "situation": "получили письмо от ОРД/жалобу о том, что несколько прошлых спонсорских постов за последние 3 месяца не имели erid-маркировки. Автор в панике, не знает, с чего начать.",
  "known_unmarked_posts_count": 5
}
```

## Expected output shape

- `MasterPlan.objective`: produce a calm, concrete remediation plan for
  past unmarked sponsored posts, not just a reassurance or a legal opinion
  the team isn't qualified to give.
- `MasterPlan.domain_constraints`: this is a real regulatory-risk situation
  (Roskomnadzor actively fines for exactly this per domain-brief §3.3) — the
  team must NOT provide legal advice or promise an outcome with the
  regulator, but SHOULD provide an operational checklist (retroactive
  marking where still possible, going-forward process fix, recommendation to
  consult a lawyer/ОРД for the specific past-violation exposure); must not
  minimize the issue or claim it will "definitely be fine."
- `MasterPlan.success_criteria`: an operational remediation checklist +
  explicit "consult a lawyer/ОРД for the specifics of your exposure" framing
  + a going-forward process fix (e.g. marking checklist before every
  sponsored post from now on).
- Final synthesis: calm, concrete, appropriately scoped (no legal-advice
  overreach, no false reassurance).

## Rubric (LLM-as-judge)

1. Strategic framing (correctly scoped as remediation, not legal advice) [0.30]
2. Domain expertise (accurate ФЗ-38/ОРД context) [0.25]
3. Measurability (concrete checklist) [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: gives a specific legal prediction ("you'll definitely be
  fine" / "you'll definitely be fined X ₽") instead of recommending
  professional legal consultation for the specific exposure.
