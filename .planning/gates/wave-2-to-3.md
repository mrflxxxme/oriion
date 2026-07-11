---
gate: wave-2-to-3
status: PENDING
opened_at: 2026-05-13T12:00:00Z
revised_at: 2026-07-11T00:00:00Z
closed_at: null
founder_signature: null

# Revision 2026-07-11 (founder-grill D-17, per ADR-040 D5 gate-philosophy):
# hard-пороги = только вычислимые технические; рыночные показатели переведены в
# measured_metrics (замеры к гейту, решение founder, НЕ блокеры закрытия волны).

hard_thresholds:
  must_phases_merged:
    target: "02.1-retro, 02.0(dev), 02.2, 02.3, 02.4, 02.5, 02.6, 02.7, 02.8, 02.9, 02.10, 02.11 merged в main; main HEALTHY"
    actual: null
    passed: null
    evidence_url: null
    description: "Все must-фазы очереди PHASES.md merged; 01.3b — merged ЛИБО перенесён в W3 по протоколу RUNWAY №3 при неразблокированном RW-04 (перенос не валит порог)."
  ac_pass_rate:
    target: 0.95
    actual: null
    passed: null
    evidence_url: null
    description: "Доля AC merged-фаз со статусом green/evidence-closed (PARTIAL допустим только с DV-записью per ADR-040 D6)."
  dv_no_open_p1:
    target: "0 открытых DV класса P1 (утечка/деньги/auth), адресованных Wave 2"
    actual: null
    passed: null
    evidence_url: null
    description: "DEFERRED-VERIFICATION.md: записи, адресованные W2 (DV-13 и добавленные волной), закрыты evidence-фактами."
  approval_flow_live:
    target: "1+ реальный Telegram-пост И 1+ реальный email отправлены через approve-флоу на staging"
    actual: null
    passed: null
    evidence_url: null
    description: "e2e-доказательство цикла ценности 02.3 (draft → human approve → send) на живых кредах (RW-03/RW-01); негативный тест: без approve send невозможен."
  pixel_skin_live:
    target: "Скин live на staging: 24 откурированных AI-архетипа + live-состояния по SSE + axe AA в скине"
    actual: null
    passed: null
    evidence_url: null
    description: "Per D-10: hand-drawn герои НЕ входят в порог (asset-апдейт по готовности RW-10)."
  vertical_certification:
    target: "pass-rate >= 0.75 на полном 30-task golden обеих вертикалей + adversarial 10/10 SAFE"
    actual: null
    passed: null
    evidence_url: null
    description: "Evaluator-run отчёты 02.4 в .planning/verticals/*/review-artifacts/ (гасит DV-13)."
  payments_tested:
    target: "Полный цикл тест-shop ЮKassa зелёный (подписка + автопродление + credit-пак + отмена), ЕСЛИ RW-04 разблокирован к гейту"
    actual: null
    passed: null
    evidence_url: null
    description: "Условный порог: при неразблокированном RW-04 фаза 01.3b переносится в W3 (RUNWAY №3) и порог помечается N/A — волна закрывается без него."
  redesign_approved:
    target: "DS v0.3 материализована; bake-off проведён; founder-утверждение зафиксировано (ADR-042 Accepted)"
    actual: null
    passed: null
    evidence_url: null
    description: "Продуктовое качество редизайна — founder-решение, но факт утверждения вычислим (подпись в ADR-042 + UI-SPEC)."

measured_metrics:
  # Замеры к гейту — НЕ блокеры. Founder принимает решение о W3-фокусе на их основании.
  weekly_registrations: { reference: 100, actual: null, note: "новые cells/нед из публичного трафика, 4-week rolling; боты/внутренние исключены" }
  ttfv_minutes: { reference: 3, actual: null, note: "медиана registration→first_task_approved по 30-дневной когорте (телеметрия 02.0)" }
  trial_to_paid_conversion: { reference: 0.05, actual: null, note: "когорта 4+ нед; актуально только при live 01.3b" }
  paying_customers: { reference: 50, actual: null, note: "активные подписки на момент гейта" }
  nps_friend_cohort: { reference: null, actual: null, note: "замер per ADR-040 D5, без порога" }
  pixel_optin_share: { reference: null, actual: null, note: "доля включивших скин + упоминания в фидбеке (вход kill-criteria R-11)" }

deliverables:
  - id: D1
    name: "Must-фазы Wave 2 shipped (см. PHASES.md очередь)"
    status: pending
    owner: "autonomy-runner"
  - id: D2
    name: "Платёжный цикл live с РФ-методами (ЮKassa) — либо задокументированный перенос в W3 (RUNWAY №3)"
    status: pending
    owner: "autonomy-runner + founder (RW-04)"
  - id: D3
    name: "Tier-1 редизайн утверждён и live (ADR-042 Accepted, DS v0.3)"
    status: pending
    owner: "designer + founder"
  - id: D4
    name: "Public marketing site live на профики.online"
    status: pending
    owner: "autonomy-runner + founder (тексты/прайсинг ack)"
  - id: D5
    name: "Gate-замеры собраны (телеметрия 02.0 + billing) и представлены founder"
    status: pending
    owner: "autonomy-runner"
  - id: D6
    name: "Cost-budget review (капы v4 $50/$75) + risks review"
    status: pending
    owner: "founder"
  - id: D7
    name: "Friend-validation отчёт (воронка/TTFV/NPS/качественный фидбек) + рекомендация следующей вертикали"
    status: pending
    owner: "founder + autonomy-runner"

metrics_snapshot:
  snapshot_taken_at: null
  metrics: {}

adr_delta:
  created: ["ADR-042 (tier-1 redesign, Proposed 2026-07-11)"]
  revised: ["ADR-004", "ADR-007", "ADR-013", "ADR-021", "ADR-030", "ADR-041 (amendments 2026-07-11)"]
  superseded: []

risks_delta:
  opened: []
  closed: []
  mitigated: ["R-14 (герои сняты с критического пути, D-10)"]
  escalated: []

capacity_snapshot:
  ai_team_roles_active: 11
  total_tasks_completed_this_wave: null
  total_cost_usd_this_wave: null
  average_revision_cycles_per_phase: null
  founder_overrides_count: null
---

# Gate: Wave 2 → Wave 3

> Переписан 2026-07-11 по решению founder-grill **D-17** (философия ADR-040 D5, как гейт W1→2):
> **hard-пороги — только вычислимые**; рыночные показатели (регистрации, TTFV, конверсия, платящие,
> NPS) — обязательные **замеры к гейту**, на основании которых founder принимает решение о фокусе
> Wave 3, но которые не могут держать волну открытой по причинам вне кода.

## Hard thresholds (must-pass, вычислимые)

1. **must_phases_merged** — очередь [PHASES.md](../roadmap/wave-2-pixel-catalog/PHASES.md) merged, main HEALTHY. 01.3b: merged или перенесён по протоколу [RUNWAY №3](../FOUNDER-RUNWAY.md).
2. **ac_pass_rate ≥ 0.95** — по AC-таблицам merged-фаз; PARTIAL только с DV-записью.
3. **dv_no_open_p1** — реестр [DEFERRED-VERIFICATION](../DEFERRED-VERIFICATION.md) чист от W2-адресованных P1.
4. **approval_flow_live** — живой пост + живое письмо через approve; негативный тест обхода зелёный.
5. **pixel_skin_live** — скин + 24 архетипа + SSE-состояния + axe AA (герои вне порога, D-10).
6. **vertical_certification** — 30-task ≥75% × 2 + adversarial 10/10 SAFE (DV-13 закрыта).
7. **payments_tested** — условный (RW-04): тест-shop цикл зелёный, либо документированный перенос.
8. **redesign_approved** — ADR-042 Accepted + UI-SPEC подписан founder.

## Measured metrics (решение founder, не блокеры)

Снимаются в `measured_metrics` frontmatter к моменту оценки гейта: регистрации/нед (ориентир 100), TTFV (≤3 мин), конверсия (≥5%), платящие (50), NPS friend-когорты, доля Pixel opt-in. Источники: телеметрия 02.0 + billing + staging-аналитика.

## Deliverables progress

memory-curator auto-syncs deliverable status. Секция перезаписывается при оценке гейта.

## Retrospective themes

_(Founder заполняет при оценке.)_

## Strategic implications for Wave 3

_(Founder заполняет: выбор следующей вертикали по D7-отчёту; Mini App + 01.11; MCP-протокол; autonomous send; co-editing триггер.)_

## Cost-budget review

- Капы на открытии волны: v4 — $50 soft / $75 hard в день (D-19).
- Фактический спенд волны: _замер при гейте_.
- Корректировка на W3: _решение founder_.

## Sign-off

- **Status:** PENDING
- **Founder signature:** _pending_
- **Date:** _pending_
- **Override justification** (only if status = WAIVED): _n/a_
