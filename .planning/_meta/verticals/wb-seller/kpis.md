---
title: "WB-Seller — Business KPIs"
vertical_slug: wb-seller
version: 0.1.0
last-updated: 2026-05-13
status: draft
aligned-with: ADR-025 (wave gates)
---

# WB-Seller — Business KPIs

## Wave 0 — Internal demo (founder + 3 ICP-friends)

| Metric | Target | Source |
|--------|--------|--------|
| TTFV-internal | < 30 минут from cell creation to first listing-audit completed | Observability dashboard |
| Task completion-rate | ≥ 0.80 | tasks.* CloudEvents |
| Coordinator decomposition accuracy | ≥ 0.85 (against 10 reference scenarios) | Founder manual eval |
| Golden-dataset pass-rate | ≥ 75% (per ADR-026 §3) | Evaluator gate (LLM-as-judge) |
| Adversarial-probe pass-rate | **100%** (hard requirement) | Evaluator gate (LLM-as-judge) |

## Wave 1 — Friend-loop validation

Gate-thresholds per ADR-025 wave-1-to-2:

| Metric | Target |
|--------|--------|
| TTFV | < 30 минут (3 of 5 friends) AND < 60 минут (5 of 5 friends) |
| Task success-rate | ≥ 0.85 (per ADR-026 §3-4 Level C) |
| **NPS** | **≥ 30** (gate condition) |
| Friend retention (week-2) | ≥ 0.60 |
| Adversarial-probe pass-rate | 100% (continued) |
| Pricing willingness validated | ₽3000-7000 / месяц range |

## Wave 2 — Public beta

Gate-thresholds per ADR-025 wave-2-to-3:

| Metric | Target |
|--------|--------|
| Weekly registrations | ≥ 100 |
| TTFV (public) | ≤ 3 минуты median |
| Registration → first-task conversion | ≥ 0.30 |
| Activation (3+ tasks in first week) | ≥ 0.20 |
| Paid conversion (week-4) | ≥ 0.05 |
| Adversarial pass-rate | 100% (continued) |

## Wave 3+ — Scale

Gate-thresholds per ADR-025 wave-3-to-4:

| Metric | Target |
|--------|--------|
| Paying customers | ≥ 500 |
| MRR per WB-Seller customer | ₽3000-7000 baseline |
| WB-Seller MRR contribution | ≥ ₽1.5M (50% of overall MRR target ₽3M) |
| Logo retention (month-6) | ≥ 0.70 |
| NPS | ≥ 40 |

## Per-task economic targets

- **Cost per task** (LLM + infra): documented в `_shared/cost-budget.yaml`. Goal: cost should be < 10% of price-charged-per-action
- **Time-to-completion**: median ≤ 90 seconds per task
- **Token budget** Wave 0: ≤ 50K input + 8K output total per task (across coordinator + researcher + writer)

## Monitoring

- **Real-time dashboard** (Wave 2): Langfuse traces + custom Grafana panels per vertical
- **Weekly review**: founder reviews aggregated KPIs every Monday (Mon 09:00 МСК ritual)
- **Quarterly**: NPS deep-dive + churn cohort analysis + adversarial probe set refresh

## Anti-vanity-metric rules

- Не считаем «количество AI-generated artifacts» — считаем артефакты, **опубликованные пользователем** (approved by user)
- Не считаем «время разговора с AI» — считаем reduction in user's manual work time
- Не считаем gross-impressions — считаем **net-conversion improvement** per SKU (before/after audit)

## References

- [ADR-025](../../decisions/ADR-025-wave-gates.md) — wave gate thresholds
- [ADR-026](../../decisions/ADR-026-vertical-expertise.md) — vertical-expertise
- [`_shared/cost-budget.yaml`](../../_shared/cost-budget.yaml) — per-task cost guardrails
