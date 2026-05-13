# Checklist — Gate frontmatter auto-fill

Прогоняется перед emit `tech.oriion.gate.metrics_ready.v1` к architect и
`tech.oriion.gate.ready_for_narrative.v1` к founder. Per ADR-025 §3 DECISION-9 fill protocol.

## Pre-flight

- [ ] Gate-file path определён (`.planning/gates/wave-N-to-N+1.md`)
- [ ] Template available (`.planning/gates/_template.md`) если файл не существует
- [ ] JSON-schema available (`.planning/gates/_schema/gate.schema.json`)
- [ ] Git baseline snapshots для Wave N start доступны (через `git log`)
- [ ] List phases Wave N из `STATUS.md` ИЛИ `roadmap/wave-N-*/PHASES.md`

## Frontmatter required fields

- [ ] `gate: wave-N-to-N+1` — точно matched (e.g. `wave-0-to-1`)
- [ ] `status: PENDING` — установлен (НЕ PASSED/BLOCKED, это founder)
- [ ] `opened_at: <YYYY-MM-DD>` — если новый файл; preserve existing если update
- [ ] `closed_at: null` — НЕ trogaем, это founder

## Auto-fill: hard_thresholds

Per ADR-025 §2:

- [ ] Required условия для текущего gate скопированы точно (Wave 0→1: `internal_demo.passed`;
      Wave 1→2: `friend_feedback_nps`, `acceptance_criteria_pass_rate`; и т.д.)
- [ ] `required` value соответствует ADR-025 (`true`, `>=30`, `>=0.9`, etc.)
- [ ] `actual` value заполнен из telemetry — `null` если ещё нет данных
- [ ] Никаких extra thresholds, не указанных в ADR-025 (не impro)

## Auto-fill: deliverables

- [ ] Каждая phase Wave N имеет row
- [ ] `id` соответствует phase ID (e.g. `phase-00.1`)
- [ ] `name` — из phase-spec title
- [ ] `status` — actual value из STATUS.md (`DONE`, `PARTIAL`, `BLOCKED`)
- [ ] `notes` — последняя note из PLAN.md "Status changes" section ИЛИ пусто если нет

## Auto-fill: metrics_snapshot

- [ ] Query `phase-state:<phase-id>` для каждой phase Wave N
- [ ] Aggregate per phase: registrations, TTFV, pass_rate, NPS (если есть telemetry)
- [ ] Wave-level totals computed
- [ ] Numbers — integer/float, NOT strings
- [ ] Никаких $-чисел (per P-AUDIT-1) — только counts, durations, percentages

## Auto-fill: adr_delta

- [ ] Git diff `decisions/README.md` `HEAD~<wave-start>..HEAD` executed
- [ ] `added`: list ADR IDs с status `Accepted | Proposed` (новые rows)
- [ ] `revised`: list ADR IDs где Status field changed (revised — это deliberate edit)
- [ ] IDs корректные format `ADR-NNN`

## Auto-fill: risks_delta

- [ ] Git diff `risks/REGISTER.md` executed
- [ ] `closed`: list R-NN where status field changed to `closed`
- [ ] `added`: list R-NN новые rows
- [ ] `severity_changed`: list R-NN: oldSev→newSev (e.g. `R-20: medium→high`)
- [ ] IDs корректные format `R-NN`

## Auto-fill: capacity_snapshot

- [ ] `founder_hours_logged` — из telemetry (если tracked) или null
- [ ] `ai_token_spend_total` — sum tokens из all `phase-state:*` Wave N
- [ ] NO $-amounts (per P-AUDIT-1)

## Markdown body

- [ ] НЕ trogan — это founder narrative
- [ ] Если файл новый из template — body содержит section headers, но empty contents
- [ ] Sections: `## Decision (founder-narrative)`, `## Retro themes`, `## Strategic
      implications`, `## Scope changes for Wave N+1` — все присутствуют

## Validation

- [ ] Frontmatter parsed как YAML 1.2 (valid syntax)
- [ ] Schema validation `gate.schema.json` passed
- [ ] Если invalid — log error, escalate к architect, НЕ overwrite existing file

## Cross-cutting checks

- [ ] No canonical-naming violations в auto-filled content (e.g. `agent_archetype_id` not
      `sprite-ID`)
- [ ] No $-numbers leaked (per P-AUDIT-1)
- [ ] Audit log entry в own namespace через `memory_store` per memory.md schema

## Final

- [ ] Self-review: frontmatter читается coherently
- [ ] CloudEvent payloads ready для parallel emit (architect + founder)
- [ ] Validated против `_shared/handoff-schema.json`
