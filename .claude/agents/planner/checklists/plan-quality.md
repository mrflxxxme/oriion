# Checklist — PLAN.md quality

Прогоняется перед emit `tech.oriion.plan.task.v1`. Все пункты checked или N/A с rationale.

## Structure & metadata

- [ ] `# PLAN — Phase NN.M — <slug>` title корректный
- [ ] Phase ID matches каталог
- [ ] Wave number указан
- [ ] Pipeline-template указан (один из: `backend-feature`, `frontend-feature`, `full-stack-feature`)
- [ ] Status = `READY` (initial) или `IN-PROGRESS` (re-plan)
- [ ] `Cycle: N of 3` указан (initial = `1 of 3`)

## Dependencies section

- [ ] Contracts cross-links на `_meta/contracts/<context>/` (не inline DDL)
- [ ] ADRs cross-links existing ADR (verified существуют через grep `decisions/`)
- [ ] Blocking/blocked-by phases — actual phase IDs из roadmap

## Task graph table

- [ ] Каждая task имеет unique ID (T1, T2, ...)
- [ ] Каждая task имеет description (≥1 sentence, actionable)
- [ ] Каждая task assigned to ровно одному role
- [ ] Roles — из ADR-023 §1 (11 persistent) ИЛИ valid non-persistent (с founder approve)
- [ ] `depends_on` поле — list existing task IDs (no forward refs, no cycles)
- [ ] `parallel_group` — task в одной группе не имеют mutual dependencies
- [ ] `estimated_tier` per ADR-027 §5 (1-5)

## Acceptance check mapping

- [ ] Каждая acceptance criterion из phase-spec имеет соответствующий row
- [ ] Test ref присутствует (file path + test name)
- [ ] Verifier check описан (как verifier проверит executable)
- [ ] Нет orphan acceptance criteria (без test/check)

## Parallel waves section

- [ ] Waves корректно named (`Wave A`, `Wave B`, ...)
- [ ] Tasks в waves соответствуют parallel_group в table
- [ ] Sequential edges (T1 → T2 → T3) корректно отражены

## Handoff plan table

- [ ] Каждый step имеет From + To + Event
- [ ] Events из `_shared/handoff-schema.json` (валидные types)
- [ ] Pipeline соответствует выбранному template
- [ ] Parallel reviewers (`reviewer-frontend`, `reviewer-backend`, `reviewer-security`)
      явно отмечены параллельно
- [ ] `verifier` идёт ПОСЛЕ reviewers approve (не параллельно)
- [ ] `memory-curator` — последний до founder approve

## Risks section

- [ ] Linked risks существуют в `risks/REGISTER.md`
- [ ] Mitigation описан per risk
- [ ] Если phase создаёт new risk — emit `tech.oriion.risk.new.v1` к `memory-curator`
      для добавления в REGISTER (этого pre-flight, не post-plan)

## Invariants

- [ ] No code в PLAN.md (только описания)
- [ ] No inline DDL/OpenAPI (только cross-refs)
- [ ] No $-numbers (per P-AUDIT-1)
- [ ] Canonical naming (`agent_archetype_id`, `system_roles`, `agent_archetypes`)
- [ ] Если `ui-spec:` в phase-spec — first task в pipeline = designer
- [ ] Если task требует contract change — escalation к architect (НЕ inline change)

## Contracts conformance

- [ ] Каждая task с `contract_refs` указывает existing path в `_meta/contracts/`
- [ ] Если phase упоминает endpoint/table, не присутствующий в contracts —
      escalation НЕ создание plan

## Final

- [ ] Plan reads coherently (mental playback)
- [ ] Total estimated cost (через memory_search past similar) — within cost-budget.yaml monthly cap
- [ ] CloudEvent payloads ready, validated против `_shared/handoff-schema.json`
- [ ] Founder summary notification подготовлена (для interactive UX per ADR-023 §8b)
