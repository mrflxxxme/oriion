# Checklist — Cross-phase invariant audit

Запускается per Workflow 2 перед wave-gate. Все пункты должны быть прогнаны и записаны в
audit report findings table. P-AUDIT-2 triggers — critical severity.

## Pre-flight

- [ ] Gate-файл `.planning/gates/wave-N-to-N+1.md` доступен и frontmatter заполнен
      `memory-curator` на 80%
- [ ] Список phase-spec'ов Wave N доступен (`STATUS.md` или `roadmap/wave-N-*/PHASES.md`)
- [ ] Список новых/revised ADR в Wave N доступен (через `decisions/README.md` diff vs
      previous wave)
- [ ] Доступ к `_meta/contracts/<context>/` × 10

## Deprecated-term sweep (P-AUDIT-2) — CRITICAL severity

Grep по всем deprecated terms из ADR-024 §2 во всех Wave N artifacts:

- [ ] `roles_rbac` — должно быть 0 matches в Wave N phase-spec'ах и contracts
- [ ] `roles_agent` — должно быть 0 matches
- [ ] `sprite-ID` — 0 matches (kebab- и snake_case варианты: `sprite_id`, `spriteId`)
- [ ] `ui_sprite_archetype` — 0 matches
- [ ] Любые другие deprecated terms из revised ADR в Wave N — 0 matches

Каждый match → finding, severity: **critical**, resolution: rename в той же PR что
закрывает gate (per P-AUDIT-2).

## Naming drift check

Grep canonical terms и verify consistency:

- [ ] `agent_archetype_id` — везде snake_case, не `agent_archetypeId` / `agentArchetypeId`
- [ ] `system_roles` — везде snake_case, не `systemRoles` (table name) и `SystemRole` (Python class)
- [ ] `agent_archetypes` — везде snake_case
- [ ] Bounded-context имена — exact match с ADR-024 §1: `iam`, `multitenancy`, `rbac`,
      `billing`, `llm-gateway`, `mcp`, `agents`, `tasks`, `artifacts`, `memory`
      (не `auth`, не `multi-tenancy`, не `llm_gateway`)

Mixed-case usage в файлах одного типа — finding, severity: **medium**.

## Bounded-context coupling audit

Для каждого `_meta/contracts/<context>/README.md`:

- [ ] Прочитана «External dependencies» секция (если есть)
- [ ] Cross-reference с фактическими импортами в `backend/src/<context>/` (если code
      существует) — `grep -r "from src\.<other-context>" backend/src/<context>/`
- [ ] Любой import от другого context, не указанный в External dependencies — finding,
      severity: **high**
- [ ] Любой direct DB cross-context query (например, `session.query(<OtherContextModel>)` в
      `src/iam/`) — finding, severity: **critical**

## DDL conformance

- [ ] Для каждого context: tables в `_meta/contracts/<context>/schema.sql` имеют
      соответствующий Alembic migration в `backend/alembic/versions/<context>/*.py`
- [ ] Migration columns ↔ schema.sql columns — diff = ∅
- [ ] RLS policies в schema.sql имеют соответствие в Alembic migration или application
      code
- [ ] Indexes в schema.sql представлены в migrations

Drift — finding, severity: **high**.

## API contract conformance

- [ ] Для каждого context: endpoints в `_meta/contracts/<context>/api.yaml` представлены
      в `backend/src/<context>/routers/` или equivalent
- [ ] OpenAPI fields ↔ Pydantic schemas — diff = ∅
- [ ] HTTP status codes из api.yaml имеют handlers

Drift — finding, severity: **high**.

## Events contract conformance

- [ ] Для каждого context: events в `events.yaml` имеют emit calls в code (grep по event type)
- [ ] CloudEvents 1.0 envelope используется (не custom формат)
- [ ] Все events documented в `events.yaml` consumed где-то OR явно отмечены как
      «emitted-for-future-use»

Missing emit/consume — finding, severity: **medium**.

## Economic-numbers sweep (P-AUDIT-1)

Grep regex `\$[0-9]+` | `RUB` | `₽` | `MRR_RUB` | `monthly_budget` во всех новых артефактах
Wave N (ADR, risks, phase-spec, handbook):

- [ ] 0 matches в `.planning/decisions/ADR-*.md` (новые/revised в Wave N)
- [ ] 0 matches в `.planning/risks/REGISTER.md` (новые/revised entries)
- [ ] 0 matches в новых phase-spec'ах Wave N
- [ ] Все $-числа живут в `.claude/agents/_shared/cost-budget.yaml`

Каждый match — finding, severity: **high**, resolution: extract в `cost-budget.yaml`.

## ADR cross-ref integrity

Для каждого ADR added в Wave N:

- [ ] `## Links` секция присутствует
- [ ] Cross-ref на GRILL DECISION ID
- [ ] Cross-ref на related/superseded ADR (если applicable)
- [ ] Cross-ref на affected risks
- [ ] `decisions/README.md` catalog содержит row с этим ADR

Missing — finding, severity: **medium**.

## Gate-frontmatter sanity

- [ ] `hard_thresholds` секция содержит точно условия из ADR-025 §2 для текущего gate
- [ ] `metrics_snapshot` поля заполнены (не null) `memory-curator`'ом
- [ ] `adr_delta.added` + `revised` — точно Wave N ADR
- [ ] `risks_delta` — все changes в `risks/REGISTER.md` за Wave N отражены

Mismatch — finding, severity: **high**.

## Final

- [ ] Findings table compiled в `.planning/_meta/audits/audit-<YYYY-MM-DD>-wave-N-gate.md`
- [ ] Severity counts: critical / high / medium / low подсчитаны
- [ ] Если `has_p_audit_2_blockers: true` — escalation packet к founder подготовлен
      параллельно с CloudEvent
- [ ] CloudEvent `tech.oriion.audit.report.v1` собран и validated против handoff-schema
