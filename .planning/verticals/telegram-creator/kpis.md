---
title: "Telegram-крейтор — Business KPIs"
vertical_slug: telegram_creator
version: 0.1.0
last-updated: 2026-07-09
status: draft
aligned-with: ADR-025 (wave gates)
---

# Telegram-крейтор — Business KPIs

## Wave 1 — Friend-loop validation

Gate-thresholds per ADR-025 wave-1-to-2:

| Metric | Target |
|--------|--------|
| TTFV | < 30 минут (3 из 5 friends) AND < 60 минут (5 из 5 friends) |
| Task success-rate | ≥ 0.85 (per ADR-026 §3-4 Level C) |
| **NPS** | **≥ 30** (gate condition) |
| Friend retention (week-2) | ≥ 0.60 |
| Adversarial-probe pass-rate | 100% (continued) |
| Golden-dataset pass-rate | ≥ 75% (per ADR-026 §3, evaluator gate) |
| Pricing willingness validated | ₽2000-6000 / месяц range (creator tier — ниже agency-marketing-ru, шире retail-охват) |

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
| Paying customers (this vertical) | часть общего ≥ 500 target |
| Logo retention (month-6) | ≥ 0.70 |
| NPS | ≥ 40 |

## Per-task economic targets

- **Cost per task** (LLM + infra): per `.claude/agents/_shared/cost-budget.yaml` guardrails — goal: cost < 10% of price-charged-per-action.
- **Time-to-completion:** median ≤ 90 seconds per task (media-plan-scale tasks may run longer, matching the Master-Agent plan+synthesis two-call shape).
- **Token budget:** Wave 1 baseline mirrors `agency-marketing-ru` — the Master overhead is +15-20% tokens per vertical task (R-32) on top of the leaf-delegation cost.

## Domain-specific quality signals (not vanity metrics)

- **Ad-marking compliance rate** — % of sponsored-post drafts that correctly
  include «Реклама» + advertiser data + erid-token placeholder guidance. Target
  100% (hard gate, mirrors the marketing-agency Master's ad-marking guardrail).
- **РКН blogger-registry flag accuracy** — when a channel's stated subscriber
  count crosses 10,000, the Master must surface the registry obligation. This
  is checked directly by adversarial probe A004 (see `golden-dataset/adversarial/`).
- **No fabricated monetization estimates** — any revenue projection must be
  qualified as a market reference range (domain-brief §4), never presented as
  a guarantee for the specific creator. Checked by adversarial probe A003.

## Monitoring

- **Weekly review:** founder reviews aggregated KPIs (Mon 09:00 МСК ritual, same cadence as other verticals).
- **Quarterly:** NPS deep-dive + adversarial probe set refresh as RU ad-law/РКН rules evolve.

## Anti-vanity-metric rules

- Не считаем «количество AI-generated artifacts» — считаем артефакты,
  **опубликованные пользователем** (approved by user; отправка вручную, пока
  `send_telegram` за approval-gate).
- Не считаем «время разговора с AI» — считаем reduction in time-to-content-plan.
- Не считаем gross-reach — считаем **ERR relative to the channel's own
  size-benchmark** (per domain-glossary «Бенчмарк по размеру канала»).

## References

- [ADR-025](../../decisions/ADR-025-wave-gates.md) — wave gate thresholds
- [ADR-026](../../decisions/ADR-026-vertical-expertise-pipeline.md) — vertical-expertise
- [`domain-brief.md`](./domain-brief.md) §2-3 — monetization + engagement benchmark sourcing
