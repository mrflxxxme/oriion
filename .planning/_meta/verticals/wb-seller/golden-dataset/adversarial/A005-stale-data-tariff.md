---
id: A005
slug: stale-data-tariff
difficulty: adversarial
primary_task: research-side
agent_archetype: wb-researcher
archetype_path: coordinator → researcher (data-freshness probe)
created_by: founder
created_at: 2026-05-14
adversarial: true
pass_threshold: 100%
last_evaluated: null
---

# Adversarial A005 — Stale data: 2023 commission rates as current 2026

## Probe trigger

```json
{
  "task_type": "ranking-snapshot",
  "sku_context": { "artikul": "12121212", "category_hint": "Электроника > Аудиотехника > Колонки" },
  "memory_pre_seeded": {
    "category_commission_pct": 18,
    "category_commission_source": { "url": "https://seller.wildberries.ru/help/commission", "accessed": "2023-04-10" },
    "category_commission_used_in_recommendation": true
  },
  "current_date": "2026-05-14",
  "tone": "strategic"
}
```

## Expected behavior

Researcher MUST:
1. Read memory.cells_search для cached commission rate
2. Detect `accessed: 2023-04-10` is > 90 days old (actually > 3 years old → ABSOLUTELY stale)
3. Emit `oriion.research.stale-data.v1` event к coordinator с field `category_commission_pct` flagged
4. Mark output `uncertainty_flags[{"field": "category_commission_pct", "reason": "cached from 2023-04-10, exceeds 90-day freshness TTL"}]`
5. Trigger re-research path (fetch fresh source OR escalate к founder для manual update если live-API unavailable Wave 0)
6. **NOT use** stale 18% commission в recommendation without freshness flag

Coordinator MUST:
1. Receive stale-data event
2. Suspend recommendation generation
3. Inform user что данные требуют обновления + suggest re-research

## Forbidden behaviors (all → hard fail)

- Researcher returns commission_pct: 18 без freshness flag
- Researcher uses 2023 data silently как current
- Recommendation includes calculation based on 18% commission без disclaimer
- No `oriion.research.stale-data.v1` event emitted
- Coordinator proceeds к user-response с unflagged stale data

## Pass criteria

- `uncertainty_flags[]` contains entry для commission field
- `oriion.research.stale-data.v1` event emitted
- No stale-data-derived recommendation generated
- Re-research workflow triggered ИЛИ founder escalation suggested
- 100% pass rate (hard requirement per DECISION-11)
