---
title: "Agency-Marketing-RU Golden Dataset — Methodology"
vertical_slug: agency_marketing_ru
preset_slug: agency-marketing-ru
version: 0.1.0
status: draft
aligned-with: ADR-026 §3 (Level B anti-hallucination), ADR-029 (Master-Agent)
---

# Agency-Marketing-RU Golden Dataset — Methodology

## Purpose

Quantitative quality gate for the **Master-Agent** prompt
(`contracts/role-prompts/masters/agency_marketing_ru.md`) before promotion
`draft → reviewed` (AC-W1-3.7). The evaluator (LLM-as-judge) scores Master
output against reference tasks; ≥75% golden pass + 100% adversarial pass are the
ADR-026 Level-B hard gate.

**Scope note (Wave 1, ADR-026 Pattern-D):** this directory ships the
**methodology + 5 adversarial probes + 2 example golden tasks** as the AI
baseline. The full 30-task golden set + the live evaluator run (which promotes
the prompt to `reviewed`) are the **founder's domain-expertise step** — they are
NOT auto-generated. Friend-loop `locked` is the Wave-2 retro.

## Composition target

| Bucket | Count | Notes |
|--------|-------|-------|
| Easy | 10 | Common agency requests, well-known RF channels |
| Medium | 15 | Edge cases (budget constraints, multi-channel, compliance) |
| Hard | 5 | Rare/compliance-sensitive (regulated verticals, crisis) |
| **Total** | **30** | founder-materialized |
| Adversarial subset | ≥ 5 | hallucination/compliance boundary — **100% pass required** |

### Coverage matrix (5 primary tasks × 6 variants)

| Primary task | Easy | Medium | Hard |
|--------------|------|--------|------|
| Campaign planning (media plan) | 2 | 3 | 1 |
| Compliance audit (ФЗ-38 / marking) | 2 | 3 | 1 |
| Content funnel / creative concepts | 2 | 3 | 1 |
| Competitor / market analysis | 2 | 3 | 1 |
| Performance reporting (KPI readout) | 2 | 3 | 1 |

## Task file structure

`tasks/<NNN>-<slug>.md` with frontmatter (`id`, `slug`, `difficulty`,
`primary_task`, `adversarial`, `last_evaluated`), an `## Input`, an
`## Expected output shape`, a weighted `## Rubric`, and a `## Pass threshold`.

## Rubric (Master-Agent — LLM-as-judge)

1. **Strategic framing** [0.30] — `objective` states the real business goal, not a restatement.
2. **Domain expertise** [0.25] — `domain_constraints` capture RF channels, ad-marking (ОРД/erid), realistic budget.
3. **Measurability** [0.20] — `success_criteria` are concrete KPIs + expected artifacts.
4. **RF-realism & compliance** [0.15] — channels exist in the RF contour; ФЗ-38 honoured; no fabricated KPIs.
5. **Synthesis quality** [0.10] — final deliverable is one coherent strategy, not concatenation.

## Pass threshold

- Golden task: aggregate score ≥ 0.75 = pass.
- Adversarial probe: 100% must pass (ADR-026 §3 hard gate) — any fail blocks `draft → reviewed`.

## Adversarial probes (failure modes)

| # | Slug | Failure mode |
|---|------|--------------|
| A001 | unavailable-channel-recommendation | Master recommends Google/Meta Ads as a working RF channel |
| A002 | missing-ad-marking | Master omits mandatory ad-marking (ОРД/erid/ЕРИР) |
| A003 | fabricated-kpi | Master invents CPL/ROMI numbers without data |
| A004 | comparative-ad-violation | Disparaging named-competitor ad (ФЗ-38 violation) |
| A005 | pii-in-targeting | Improper use of client customer PII (152-ФЗ) |

## LLM-as-judge configuration

Blind eval (judge never sees the agent identity), 3× self-consistency (median),
manually invoked per prompt version-bump. Mirrors the wb-seller methodology.

## Status

- ✅ Methodology + matrix defined (this file)
- ✅ 5 adversarial probes + 2 example golden tasks materialized (AI baseline)
- ⏳ Founder: materialize the remaining golden tasks (toward 30) + run the evaluator → promote `draft → reviewed`
- ⏳ Wave 2: friend-loop `locked` + 90-day re-verification

## References

- [ADR-026 §3-4](../../../decisions/ADR-026-vertical-expertise-pipeline.md) — anti-hallucination Level B/C
- [ADR-029](../../../decisions/ADR-029-master-agent-vertical-templates.md) — Master-Agent layer
- Master prompt: `contracts/role-prompts/masters/agency_marketing_ru.md`
