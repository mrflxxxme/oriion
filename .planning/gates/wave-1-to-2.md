---
gate: wave-1-to-2
status: PENDING
opened_at: 2026-05-13T12:00:00Z
revised_at: 2026-07-07T00:00:00Z
closed_at: null
founder_signature: null

# REVISED 2026-07-07 per ADR-040 D5 (founder-интервью). Prior thresholds encoded the
# pre-2026-05-15 scope (5 verticals / 10 phases / NPS>=30 blocking) — superseded.
# Wave 1 actual scope: 2 verticals (Marketing-agency + Telegram-creator), ~13 phases.
# Human validation (friend-loop) moved to Wave 2 phase 02.0 (non-blocking measurement).

hard_thresholds:
  acceptance_criteria_pass_rate:
    target: 0.9
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "Share of automated acceptance-tests passed against total executed across every Wave 1 phase (verifier gating). Computed as count(passed) / count(total) over the verifier run logs + evidence/ artifacts for Wave 1. Founder-waived failures count as failures."
  must_phases_merged:
    target: true
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "All Wave-1 must-phases merged to main per ADR-040 D4: 01.9 (MCP + DLP flags ON) + 01.4-ui + 01.10 (2nd vertical reviewed) + 01.12 (dashboard + onboarding), in addition to the already-merged 01.1..01.8. Parked phases (01.3b / 01.8b / 01.11) do NOT block — they carry over per FOUNDER-RUNWAY."
  deferred_verification_clean:
    target: true
    actual: null
    passed: null
    evidence_url: null
    measured_at: null
    description: "DEFERRED-VERIFICATION.md has no open P1-class entries (data-leak / money / auth) addressed to Wave 1. Per ADR-040 D6."

deliverables:
  - id: D1
    name: "All Wave-1 must-phases (ADR-040 D4) delivered per .planning/roadmap/wave-1-core-mvp/PHASES.md"
    status: pending
    owner: "autonomous runner + verifier"
    notes: "Each phase passes its own gates + evidence before counting"
  - id: D2
    name: "2 verticals (agency_marketing_ru + telegram_creator) at ADR-026 'reviewed': golden >=75%, adversarial 100%, founder REVIEW-CHECKLIST signed"
    status: pending
    owner: "evaluator + founder"
    notes: "Closes DV-02; per 01.10 seed-spec"
  - id: D3
    name: "Security guardrails ACTIVE: both flags ON, INN FP <=1% proven (DV-04/DV-05 closed)"
    status: pending
    owner: "runner (01.9) + reviewer-security"
    notes: "Blocking AC of phase 01.9 per ADR-040 D10"
  - id: D4
    name: "Wave 1 cost-budget.yaml v3 review with adjusted caps if needed"
    status: pending
    owner: "founder"
    notes: "Mandatory per cost-budget.yaml review_trigger; v3 caps = $20/$40 per ADR-040 D11"
  - id: D5
    name: "All Wave 1 risks reviewed and register updated"
    status: pending
    owner: "memory-curator + founder"
    notes: "Inputs to risks_delta"
  - id: D6
    name: "Wave-2 PHASES.md regenerated with seed-specs (incl. 02.0 friend-validation + 02.1-retro) + gate files synced to the new scope"
    status: pending
    owner: "planner + architect"
    notes: "Per ADR-040 D1 (seed-specs for the current wave) + D5 (roadmap reorg must update gate files in the same PR)"

metrics_snapshot:
  snapshot_taken_at: null
  metrics: {}

adr_delta:
  created: []
  revised: []
  superseded: []

risks_delta:
  opened: []
  closed: []
  mitigated: []
  escalated: []

capacity_snapshot:
  ai_team_roles_active: 11
  total_tasks_completed_this_wave: null
  total_cost_usd_this_wave: null
  average_revision_cycles_per_phase: null
  founder_overrides_count: null
---

# Gate: Wave 1 → Wave 2

> **Revision 2026-07-07 (ADR-040 D5).** Гейт переведён на **чисто технические пороги**, автономно
> вычислимые раннером. Прежние пороги (NPS ≥30 от 15–25 друзей по 5 вертикалям; «все 10 фаз»)
> кодировали до-2026-05-15 скоуп и были невычислимы против фактической дорожной карты
> (2 вертикали, ~13 фаз). Людская валидация НЕ отменена — перенесена в **Wave 2 фазу 02.0**
> как первая пользовательская фаза (неблокирующая для остального трека Wave 2); NPS там
> **измеряется**, но порогом не является (выборка 10–15 друзей статистически шумна).

## Hard thresholds (must-pass)

### `acceptance_criteria_pass_rate >= 0.9`

Каждая Wave-1 фаза несёт verifier-driven acceptance-набор. Метрика агрегируется по всем
выполненным проверкам волны:

```
pass_rate = count(passed_runs) / count(total_runs)
```

Источники: verifier run logs + `evidence/` артефакты фаз, экспорт в
`.planning/gates/evidence/wave-1-to-2/verifier-runs.json`. Founder-waived провалы считаются
провалами — waiver не улучшает метрику.

### `must_phases_merged = true`

Все must-фазы per [ADR-040 D4](../decisions/ADR-040-execution-spec-contract.md) смержены в main:
**01.9** (MCP-серверы + оба security-флага ON) + **01.4-ui** + **01.10** (вторая вертикаль
`reviewed`) + **01.12** (dashboard + onboarding) — поверх уже смерженных 01.1–01.8.
Parked-фазы (01.3b / 01.8b / 01.11) гейт НЕ блокируют: их runway-зависимости
([FOUNDER-RUNWAY](../FOUNDER-RUNWAY.md) RW-04/02/05) — внешние процессы; при гейте они
переносятся в Wave 2 отдельным решением в Retrospective themes.

### `deferred_verification_clean = true`

[DEFERRED-VERIFICATION.md](../DEFERRED-VERIFICATION.md) не содержит открытых записей класса P1
(утечка данных / деньги / auth), адресованных Wave 1. Прочие открытые записи переезжают в
02.1-retro планово.

## Deliverables progress

memory-curator auto-syncs deliverable status. This section is rewritten at gate-evaluation time.

## Retrospective themes

_(Founder fills at evaluation time; сюда же — решение по переносу parked-фаз.)_

## Strategic implications for Wave 2

_(Founder fills: результаты 02.0 friend-validation планируются здесь как вход Wave-2 приоритизации, не как гейт-порог.)_

## Risk delta narrative

_(Founder fills around populated risks_delta entries.)_

## Cost-budget review

- Budget cap at gate opening: per `.claude/agents/_shared/cost-budget.yaml` **v3** (per-day $20 soft / $40 hard per ADR-040 D11).
- Actual spend this wave: _to be measured via Langfuse aggregation + RUN-QUEUE complete-entries_.
- Adjustment proposed for Wave 2: _to be decided based on per-task and per-day cap utilization_.
- Founder decision: _pending_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
