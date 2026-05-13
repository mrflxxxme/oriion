# Checklist — Re-plan after revision

Прогоняется перед emit обновлённого `tech.oriion.plan.task.v1`. Per ADR-027 §6 — max 3
цикла reviewer ↔ implementer.

## Pre-flight

- [ ] Получены ВСЕ revision docs за этот cycle (если parallel reviewers вернули несколько
      — все processed, не первый попавшийся)
- [ ] Current cycle counter прочитан из PLAN.md (`Cycle: N of 3`)
- [ ] Если current cycle = 3 — STOP. Не делай re-plan. Escalate через
      `tech.oriion.conflict.escalation.v1` к `architect` с `conflict_type: cycle-exhaustion`

## Read all revisions

- [ ] Каждая `revisions/<phase>-<reviewer>.md` прочитана полностью (включая file:line refs)
- [ ] Findings группированы по severity: blocker / high / medium / low
- [ ] Findings группированы по type: contract-mismatch / security / accessibility /
      performance / style / test-gap

## Conflict detection

- [ ] Cross-reference findings от parallel reviewers — есть ли direct conflicts?
      (например, reviewer-backend «remove rate-limit», reviewer-security «add rate-limit»)
- [ ] Если conflicts detected — STOP re-plan, escalate через
      `tech.oriion.conflict.escalation.v1` к `architect` с `conflict_type:
      reviewer-disagreement`. Не пытайся резолвить сам.

## Recurring-failure detection

- [ ] Через `memory_search_unified(namespace="phase-state:<phase-id>", "re-plan ...")` —
      это same finding снова всплыл в cycle N+1 что и в cycle N? (implementer не пофиксил)
- [ ] Если same finding pattern в 2+ cycles — escalate ДО исчерпания 3 cycles (waste of
      tokens). `tech.oriion.conflict.escalation.v1` с `conflict_type: recurring-failure`.

## Task graph update

- [ ] Для каждого blocker/high finding — определено: modify existing task OR add new task
- [ ] Modified tasks: scope expanded, description updated, depends_on re-checked
- [ ] Added tasks: получили unique ID (T<N+1>...), assigned role, depends_on указан
- [ ] Removed tasks: явный rationale в re-plan diff (e.g. «T5 removed because finding A
      обнаружил, что endpoint избыточен»)

## Dependencies & parallel re-validate

- [ ] Новые tasks могут породить new dependencies — graph re-checked на cycles
- [ ] Parallel-groups corrected — added tasks помещены в правильную группу
- [ ] Sequential edges не сломаны

## Cycle counter

- [ ] Cycle counter incremented: `Cycle: 2 of 3` → `Cycle: 3 of 3`
- [ ] PLAN.md `Status: IN-PROGRESS` (не возвращаем к READY)

## Re-plan diff section

- [ ] Section добавлен в начало PLAN.md (или updated если уже существует — append, не replace)
- [ ] Listed: Added / Changed / Removed tasks
- [ ] Listed: reviewers addressed (которые findings closed)
- [ ] Listed: pending reviewers (если parallel reviewer ещё не вернул)

## Acceptance check mapping

- [ ] Если added task adds new acceptance check — добавь в Acceptance check mapping table
- [ ] Если removed task убрал acceptance check — verify, что criterion из phase-spec
      теперь covered other task OR escalate к founder (criterion не выполняется)

## Handoff plan

- [ ] Handoff table updated: dispatch только changed/added tasks к implementers
- [ ] Unchanged tasks НЕ re-dispatched (waste of tokens, possible regression)
- [ ] Reviewer roles в pipeline остаются те же (тот же кто вернул revision — он же
      re-review'ит)

## Memory persistence

- [ ] `memory_store` к `phase-state:<phase-id>` с key `re-plan-<phase-id>-cycle-<N>` —
      payload per memory.md schema

## Final

- [ ] Self-review re-plan читабелен и явно показывает что изменилось
- [ ] CloudEvent `tech.oriion.plan.task.v1` payload ready только для changed/added tasks
- [ ] Validated против `_shared/handoff-schema.json`
- [ ] Founder notification: summary re-plan diff (interactive UX)
