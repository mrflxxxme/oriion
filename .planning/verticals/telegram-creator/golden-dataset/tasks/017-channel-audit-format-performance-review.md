---
id: 017
slug: channel-audit-format-performance-review
difficulty: medium
primary_task: channel-audit
agent_archetype: master-telegram-creator
archetype_path: master → coordinator → community-manager/analyst
created_by: ai-baseline
created_at: 2026-07-09
adversarial: false
last_evaluated: null
---

# Task 017 — Audit which content formats perform best over a month

## Input

```json
{
  "task_type": "channel-audit",
  "channel_size": 26000,
  "month_summary": [
    { "format": "текстовый пост", "count": 16, "avg_err": "6%" },
    { "format": "кружок", "count": 4, "avg_err": "11%" },
    { "format": "опрос", "count": 4, "avg_err": "14%" },
    { "format": "сторис", "count": 8, "avg_err": "n/a — сторис не считаются в той же ERR-метрике" }
  ]
}
```

## Expected output shape

- `MasterPlan.objective`: identify which formats are over/under-performing
  relative to the 5-15% healthy band for a 26K (10K-100K tier) channel and
  recommend a format-mix rebalance.
- `MasterPlan.domain_constraints`: text posts (6%) are at the low end of
  healthy, round-videos (11%) and polls (14%) outperform — recommend shifting
  mix toward the higher performers without abandoning text posts entirely;
  correctly note that stories use a different measurement (not directly
  ERR-comparable) rather than forcing a false comparison.
- `MasterPlan.success_criteria`: a ranked format performance summary +
  a concrete rebalance recommendation (e.g. more polls/round-videos, fewer
  low-performing plain text posts) without abandoning the core rubric
  structure.
- Final synthesis: clear, actionable format-mix recommendation.

## Rubric (LLM-as-judge)

1. Strategic framing [0.30]
2. Domain expertise (correct per-format benchmark reasoning, stories caveat) [0.25]
3. Measurability [0.20]
4. RU-realism & compliance [0.15]
5. Synthesis quality [0.10]

## Pass threshold

- Aggregate ≥ 0.75.
- Hard fail if: directly compares stories' unavailable ERR figure to the
  other formats as if it were the same metric.
