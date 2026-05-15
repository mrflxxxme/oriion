# ADR-025: Acceptance-gate format — Wave→Wave transitions с hard go/no-go thresholds

- **Status:** Accepted

## Decision

Покрывает [ADR-028 policies registry](./ADR-028-policies-registry.md) DECISION-9. Фиксирует формат файлов, которыми оформляются переходы Wave N → Wave N+1, и hard thresholds на metric-side. Wave 2-5 остаются direction-only (per DECISION-2) до прохождения соответствующего gate.

### 1. Формат — YAML frontmatter + Markdown body

Файлы лежат в `.planning/gates/wave-N-to-N+1.md`. JSON-schema для валидации — `.planning/gates/_schema/gate.schema.json`. Template — `.planning/gates/_template.md`.

Структура файла:

```markdown
---
gate: wave-1-to-2
status: PENDING | PASSED | BLOCKED
opened_at: 2026-09-01
closed_at: null
hard_thresholds:
  friend_feedback_nps: {required: ">=30", actual: null}
  acceptance_criteria_pass_rate: {required: ">=0.9", actual: null}
deliverables:
  - id: phase-01.5
    name: Dashboard UI
    status: DONE | PARTIAL | BLOCKED
    notes: ...
metrics_snapshot:
  registrations_total: ...
  TTFV_minutes: ...
  ...
adr_delta:
  added: [ADR-NNN]
  revised: [ADR-MMM]
risks_delta:
  closed: [R-NN]
  added: [R-MM]
  severity_changed: [R-XX: medium→high]
capacity_snapshot:
  founder_hours_logged: ...
  ai_token_spend_total: ...
---

# Wave 1 → Wave 2 acceptance gate

## Decision (founder-narrative)
<status PASSED/BLOCKED + rationale>

## Retro themes
<что узнали, что переоценили>

## Strategic implications
<как gate-data влияет на Wave 2+ направления>

## Scope changes for Wave 2
<если есть>
```

JSON-schema валидирует frontmatter перед commit (CI gate).

### 2. Hard go/no-go thresholds

| Gate | Required AND-условия |
|---|---|
| **Wave 0 → 1** | `internal_demo.passed = true` |
| **Wave 1 → 2** | `friend_feedback.nps >= 30` AND `acceptance_criteria_pass_rate >= 0.9` |
| **Wave 2 → 3** | `weekly_registrations >= 100` AND `TTFV_minutes <= 3` AND `conversion >= 0.05` |
| **Wave 3 → 4** | `paying_customers >= 500` AND `MRR_RUB >= 3_000_000` |
| **Wave 4 → 5** | `paying_customers >= 2000` AND `MRR_RUB >= 15_000_000` |

Если AND-условие не выполняется — `status: BLOCKED`. Wave N+1 не стартует, Wave N продолжается до закрытия gap или решения founder о pivot/kill (см. risks/REGISTER.md → стратегические ставки + kill criteria).

### 3. Fill protocol

- **memory-curator** auto-fills ~80% frontmatter из накопленной telemetry: metrics, deliverables, ADR-delta, risks-delta, capacity-snapshot.
- **Founder** fills:
  - Markdown body (retro themes, strategic implications, scope-changes).
  - `status: PASSED | BLOCKED` после проверки hard thresholds.
  - `closed_at`.

Gate-файл идёт через PR с reviewer-backend (валидация JSON-schema) + founder (approval). После merge gate-data становится input'ом для AI-планировщика, генерящего Wave N+1 phase-spec'ы (направление-only → B-level).

## Consequences

- **Hard gating:** Wave N+1 не может стартовать спекулятивно. Это защищает от scope creep и от инвестирования AI-budget'а в направления, чьи предпосылки не сошлись.
- **Direction-only для Wave 2-5:** до прохождения gate Wave N → N+1 spec'ы Wave N+1 не доводятся до B-level (per DECISION-2 в GRILL).
- **Auditable retro:** gate-файл = единственное место, где живёт «как Wave N прошёл» с metrics + decision-context. Через 6 месяцев founder может ответить «почему мы решили pivot тогда».
- **Founder accountability:** только founder ставит `status: PASSED/BLOCKED`. AI не может «разблокировать» Wave автоматически даже при достижении метрик — нужен явный founder-sign-off.
- **Schema enforcement:** JSON-schema в CI ломает PR, если frontmatter не conform'ит — это страховка от drift в формате.

## Links

- [ADR-028 policies registry](./ADR-028-policies-registry.md) — DECISION-9
- [ADR-023](./ADR-023-ai-team-runtime.md) — memory-curator роль (auto-fills frontmatter)
- Roadmap waves: [.planning/roadmap/](../roadmap/)
- Strategic bets + kill criteria: [risks/REGISTER.md](../risks/REGISTER.md#стратегические-ставки-с-kill-criteria)
