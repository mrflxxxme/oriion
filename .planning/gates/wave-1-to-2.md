---
gate: wave-1-to-2
status: PASS
opened_at: 2026-05-13T12:00:00Z
revised_at: 2026-07-07T00:00:00Z
closed_at: 2026-07-10T11:12:56Z
founder_signature: "Kirill Uklonskiy (founder) — «Подпиши за меня Wave 1 — согласовано»; подписано раннером по прямому in-session-поручению 2026-07-10"

# REVISED 2026-07-07 per ADR-040 D5 (founder-интервью). Prior thresholds encoded the
# pre-2026-05-15 scope (5 verticals / 10 phases / NPS>=30 blocking) — superseded.
# Wave 1 actual scope: 2 verticals (Marketing-agency + Telegram-creator), ~13 phases.
# Human validation (friend-loop) moved to Wave 2 phase 02.0 (non-blocking measurement).

hard_thresholds:
  acceptance_criteria_pass_rate:
    target: 0.9
    actual: 1.0
    passed: true
    evidence_url: ".planning/roadmap/wave-1-core-mvp/WAVE-1-SUMMARY.md"
    measured_at: 2026-07-10T11:12:56Z
    description: "Share of automated acceptance-tests passed against total executed across every Wave 1 phase (verifier gating). Computed as count(passed) / count(total) over the verifier run logs + evidence/ artifacts for Wave 1. Founder-waived failures count as failures. Result: every Wave-1 must-phase merged with all CI gates green (ruff / mypy-strict / bandit / pytest incl. per-module >=85% + real-PG integration) + phase evidence (01.9a/01.9b adversarial-audit PASS, 01.10 live-golden 7/7, 01.8c golden-smoke 7/7). No founder-waived failures."
  must_phases_merged:
    target: true
    actual: true
    passed: true
    evidence_url: "https://github.com/mrflxxxme/oriion/commits/main"
    measured_at: 2026-07-10T11:12:56Z
    description: "All Wave-1 must-phases merged to main per ADR-040 D4: 01.9 (MCP + DLP flags ON) + 01.4-ui + 01.10 (2nd vertical reviewed) + 01.12 (dashboard + onboarding), in addition to the already-merged 01.1..01.8. Parked phases (01.3b / 01.11) do NOT block — they carry over per FOUNDER-RUNWAY (01.8b OAuth descoped, RW-02 снята). Result: all merged to main (last-green 85059a6) + deployed & server-verified on VPS. The '2nd vertical reviewed' sub-criterion (D2) is MET — both telegram_creator and agency_marketing_ru Master-prompts promoted draft->reviewed (status: reviewed, quality_bar: stable) after the live review-run (5/5 adversarial each, TG-008 anti-fabrication fixed + re-run clean); founder APPROVED. Also merged: 01.8c dev-infra hardening (PR-1 #109) + brand-rename teamly->Профики (PR-2 #111)."
  deferred_verification_clean:
    target: true
    actual: true
    passed: true
    evidence_url: ".planning/DEFERRED-VERIFICATION.md"
    measured_at: 2026-07-10T11:12:56Z
    description: "DEFERRED-VERIFICATION.md has no open P1-class entries (data-leak / money / auth) addressed to Wave 1. Per ADR-040 D6. Result: DV-04/DV-05 (DLP) closed (01.9a); DV-02/DV-12 (vertical review) closed; DV-06 (SMTP live-send) closed. Remaining open DV are non-P1 and cred/quality-gated: DV-11 (connector live round-trip — needs RW-03 creds), DV-01/DV-03/DV-10 (carry to 02.1-retro), DV-07 (carry to 02.6). None are leak/money/auth addressed to Wave 1."

deliverables:
  - id: D1
    name: "All Wave-1 must-phases (ADR-040 D4) delivered per .planning/roadmap/wave-1-core-mvp/PHASES.md"
    status: done
    owner: "autonomous runner + verifier"
    notes: "01.9a/01.9b + 01.4-ui + 01.10 + 01.12 merged; each passed its own gates + evidence. Plus 01.8c dev-infra hardening + brand-rename."
  - id: D2
    name: "2 verticals (agency_marketing_ru + telegram_creator) at ADR-026 'reviewed': golden >=75%, adversarial 100%, founder REVIEW-CHECKLIST signed"
    status: done
    owner: "evaluator + founder"
    notes: "Both promoted draft->reviewed after live review-run; TG-008 anti-fabrication fixed; founder APPROVED. Closed DV-02 + DV-12."
  - id: D3
    name: "Security guardrails ACTIVE: both flags ON, INN FP <=1% proven (DV-04/DV-05 closed)"
    status: done
    owner: "runner (01.9) + reviewer-security"
    notes: "Both flags default-ON in prod; INN FP 11%->0%; DV-04/DV-05 closed (01.9a). Verified ON on VPS."
  - id: D4
    name: "Wave 1 cost-budget.yaml review with adjusted caps if needed"
    status: done
    owner: "founder"
    notes: "Reviewed + raised this run at founder direction: v3 ($20/$40) -> v4 ($50/$75 soft/hard per day, dev_team internal Claude-agent spend). Ack RQ-20260709-002. See cost-budget review section below."
  - id: D5
    name: "All Wave 1 risks reviewed and register updated"
    status: done
    owner: "memory-curator + founder"
    notes: "Light pass at gate: no new blocking risks opened; R-33 (TG Business privacy) stays parked with 01.11 (RW-05); R-32/R-31 (Master cost/latency, AI-cost) mitigations held via budget-cap + cost-budget v4. See risk-delta narrative below. Deep quarterly risk review remains founder-cadence."
  - id: D6
    name: "Wave-2 PHASES.md regenerated with seed-specs (incl. 02.0 friend-validation + 02.1-retro) + gate files synced to the new scope"
    status: deferred
    owner: "planner + architect"
    notes: "DEFERRED to a dedicated Wave-2 planning session per founder direction 2026-07-10 ('генерировать спеки на wave 2 будем после в отдельной сессии'). Does NOT block Wave-1 closure — it is Wave-2 opening work. Per ADR-040 D1 + D5."

metrics_snapshot:
  snapshot_taken_at: null
  metrics: {}

adr_delta:
  created: ["ADR-037 (autonomous runner protocol)", "ADR-040 (execution spec-contract)", "ADR-041 (connector architecture — native-tool callables; real MCP-protocol deferred to Wave 2)"]
  revised: ["ADR-026 (vertical pipeline — research-first canvas made normative)"]
  superseded: []

risks_delta:
  opened: []
  closed: []
  mitigated: ["R-05 (data leak via connector — DLP-screen on outgoing connector args + capability-gate DANGEROUS-send-denied)", "R-31/R-32 (AI-cost / Master overhead — cost-budget v4 caps + per-task budget accumulator)"]
  escalated: []

capacity_snapshot:
  ai_team_roles_active: 11
  total_tasks_completed_this_wave: null
  total_cost_usd_this_wave: null   # not precisely measurable — no live Claude-Code token meter; dev_team spend approx (see cost-budget review)
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

### Autonomous evaluation (`/autonomy:run` 2026-07-09) — computable thresholds

| Threshold | Result | Basis |
|---|---|---|
| `acceptance_criteria_pass_rate ≥ 0.9` | ✅ **MET** (~1.0) | Every Wave-1 phase merged with all CI gates green (ruff/mypy-strict/bandit/pytest incl. per-module ≥85% + real-PG integration) + phase evidence (01.9a/01.9b adversarial-audit PASS, 01.10 live-golden 7/7). No founder-waived failures. |
| `must_phases_merged` | ✅ **MET** (merge + reviewed + founder sign-off all done) | 01.9a+01.9b (MCP substrate + both DLP flags ON) + 01.4-ui + 01.10 (2nd vertical) + 01.12 all merged to `main` + 01.8c dev-infra hardening (#109) + brand-rename teamly→«Профики» (#111) + deployed & server-verified on VPS (last-green `85059a6`). The "2nd vertical **reviewed**" sub-criterion (D2) is ✅ **MET**: both `telegram_creator` and `agency_marketing_ru` Master-prompts promoted `draft → reviewed` (`status: reviewed`, `quality_bar: stable`) after the live review-run 2026-07-09 (5/5 adversarial each, deliverables reviewed-quality, TG-008 anti-fabrication fixed + re-run clean 2026-07-10) — founder APPROVED. DV-12 + DV-02 **closed**. Founder gate **signature** applied 2026-07-10 (in-session direction) → `status: PASS`. |
| `deferred_verification_clean` | ✅ **MET** | No open P1-class (leak/money/auth) DV addressed to Wave 1: DV-04/DV-05 (DLP) **closed** (01.9a). Open DV-11 (connector live-smoke) / DV-12 (vertical cert) / DV-06 (SMTP) are cred/quality-gated, not P1 leak/money/auth. |

**Deliverables:** D1 ✅ (all must-phases). D2 ✅ (both verticals reviewed, founder-approved, DV-02/12 closed). D3 ✅ (security guardrails ACTIVE — both flags ON in prod, INN FP≤1% proven, DV-04/05 closed). D4 ✅ (cost-budget v3→v4 review, founder-directed). D5 ✅ (light risk pass at gate — no new blockers; deep quarterly review = founder cadence). **D6 ⏸ DEFERRED** to a dedicated Wave-2 planning session (founder direction 2026-07-10) — Wave-2 opening work, does not block closure. **`founder_signature` ✅ applied 2026-07-10.** Server-verified on VPS 2026-07-09 (DLP-ON, capability-gate denies send, connector_credentials migration live, memory/dashboard/onboarding routes 200).

> **✅ GATE CLOSED — Wave 1 → Wave 2, `status: PASS`, signed 2026-07-10.** Все три вычислимых порога MET. Формальное закрытие Wave 1. Планирование Wave 2 (D6: PHASES-регенерация + seed-specs + gate-sync) — отдельная сессия.

## Retrospective themes

- **Parked-фазы переносятся в Wave 2** (не держат волну открытой, ADR-040 D4): **01.3b** (billing/ЮKassa → RW-04, внешний счёт 5–10 дней) и **01.11** (Telegram Business API → RW-05, юрист/consent). Распаркуются оппортунистически по мере кредов/юр-текста. **01.8b (OAuth) — расскоупена** (auth упрощён до email-only, RW-02 снята), не переносится.
- **Verticals reviewed раньше плана:** обе вертикали (`telegram_creator` + `agency_marketing_ru`) достигли `reviewed` уже в Wave 1 (live review-run + TG-008 anti-fabrication fix). Wave-2 «Master hardening pass» теперь = второй проход поверх reviewed-промптов; полный первый цикл research→draft→review в Wave 2 нужен только новой WB-вертикали.
- **Инфра-долг закрыт до старта Wave 2:** 01.8c (нативные сабагенты D8, OpenAPI-snapshot+drift-CI D2, docs-freshness CI D9, JOURNAL-архивация D12) + brand-rename teamly→«Профики» (oriion — внутренний codename).
- **Открытый DV-долг** переезжает планово: DV-01/DV-03/DV-10/DV-11 → 02.1-retro; DV-07 → 02.6.

## Strategic implications for Wave 2

- **Планирование Wave 2 — отдельная сессия** (D6 deferred по решению founder 2026-07-10). Обязательные первые фазы зафиксированы (интервью 2026-07-07): **02.1-retro** (гашение DV) + **02.0 friend-validation** (10–15 ICP-друзей на 3 пресетах; NPS **измеряется**, не порог).
- Результаты 02.0 friend-validation — вход приоритизации Wave 2, НЕ гейт-порог (выборка статистически шумна).
- **Connector-развилка на 02.4:** нативные tool-callable коннекторы (ADR-041, доказаны в 01.9b) vs реальный MCP-protocol транспорт (нужен для community-MCP: github/notion/slack) — решается на discuss-шаге 02.4, не сейчас.

## Risk delta narrative

- **Смягчены в Wave 1:** R-05 (утечка через коннектор) — DLP-скрин исходящих аргументов коннектора + capability-gate (DANGEROUS-send всегда deny, fail-closed на неизвестном tool); R-31/R-32 (AI-cost / Master-overhead) — cost-budget v4 + per-task budget-accumulator (cap на агрегат Master+children).
- **Держатся паркованными с гейтед-фазами:** R-33 (Telegram Business API / 152-ФЗ) — с 01.11 (RW-05, юрист).
- Новых блокирующих рисков волны не открыто. Глубокий quarterly-пересмотр реестра — за founder-каденцией (не гейт-блокер).

## Cost-budget review

- Budget cap at gate opening: `.claude/agents/_shared/cost-budget.yaml` — на старте волны **v3** ($20 soft / $40 hard в день), в ходе рана поднят до **v4** ($50 soft / $75 hard в день) по прямому поручению founder (dev_team internal Claude-agent spend, НЕ live-LLM/user_production spend). Ack: RUN-QUEUE RQ-20260709-002.
- Actual spend this wave: **точно не измеримо** — нет живого token-meter Claude Code; dev_team-spend оценивается приблизительно, live-LLM evidence-гейты фаз шли по ~$0.03–0.05 за прогон (golden-smoke/live-golden).
- Adjustment for Wave 2: v4-caps переносятся как есть; пересматриваются на гейте Wave-2→3, если утилизация покажет необходимость.
- **Founder decision:** согласовано (v4 — прямое поручение founder).

## Sign-off

- **Status:** PASS
- **Founder signature:** Kirill Uklonskiy (founder) — «Подпиши за меня Wave 1 — согласовано» (in-session поручение раннеру, 2026-07-10). D6 (Wave-2 spec-регенерация) сознательно отложен в отдельную сессию.
- **Date:** 2026-07-10
- **Override justification** (only if status = WAIVED): _n/a — все три вычислимых порога MET, статус PASS (не WAIVED)._
