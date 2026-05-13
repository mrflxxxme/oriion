# Checklist — Phase archive rotation

Прогоняется per Workflow 2. Цель: переместить `phase-state:<phase-id>` в
`archive:phase-state:<phase-id>` без broken cross-refs и без потери data integrity.

## Pre-flight

- [ ] Triggered legitimately: `tech.oriion.phase.complete.v1` с `status: DONE` AND
      complete_at + 30d прошло
- [ ] Phase-id извлечён точно (matches каталог `roadmap/wave-N-*/phases/NN.M-<slug>/`)
- [ ] Founder approve через `phase.complete.v1.founder_approved: true` — verified

## Cross-ref scan (pre-rotation)

- [ ] Grep `<phase-id>` по active files выполнен:
  - [ ] Other `PLAN.md` (active phases)
  - [ ] `roadmap/wave-*-*/PHASES.md`
  - [ ] Active ADRs (`decisions/ADR-*.md` без `Status: Superseded`)
  - [ ] `_meta/*` files (PROJECT.md, STATUS.md, open-questions.md, glossary.md, conventions.md)
  - [ ] Active `gates/wave-N-to-N+1.md`
- [ ] Любой найденный link logged в rotation summary
- [ ] Archived phase preserve cross-refs ОК (link survives, target moves к archive namespace, файлы остаются на диске)
- [ ] Если cross-ref points на phase-state namespace entry (а не файл) — archive-link
      обновлён, чтобы указывать `archive:phase-state:<phase-id>`

## Namespace migration

- [ ] List all keys в `phase-state:<phase-id>` через `memory_list`
- [ ] Для каждого entry:
  - [ ] Read value + metadata
  - [ ] Write в `archive:phase-state:<phase-id>` с дополнительными metadata fields:
        `archived_at: <today>`, `archived_by: memory-curator`,
        `original_namespace: phase-state:<phase-id>`
  - [ ] Verify write succeeded через read-back
  - [ ] Delete original entry (`memory_delete`)
  - [ ] Preserve ONNX embedding (re-index в archive HNSW — не regenerate)
- [ ] Counter `entries_moved` accurately tracked
- [ ] Если any write fails — STOP, rollback (re-write moved entries back), escalate

## STATUS.md update

- [ ] Phase row identified (column matched на phase-id)
- [ ] Status field: `DONE` → `ARCHIVED`
- [ ] Archive date column added (или updated если column existed): `<YYYY-MM-DD>`
- [ ] Никаких other rows trogan
- [ ] File save'нут atomically (single write, не partial)

## Open-questions check

- [ ] Открыт `_meta/open-questions.md`
- [ ] Если phase-spec явно закрывал OQ-NN (через "Closes: OQ-NN" field или mention в
      acceptance) — verify OQ status уже = `closed` в open-questions.md
- [ ] Если OQ ещё `open` несмотря на phase DONE — flag, escalate к founder (rare edge
      case, не auto-close)

## PROJECT.md check

- [ ] Если phase упоминается в PROJECT.md active blockers / OQ — update reference
      (e.g. «blocked by OQ-13» → если OQ closed by phase → remove blocker)

## Rotation summary file

- [ ] Создан `.planning/_meta/audits/archive-<phase-id>-<YYYY-MM-DD>.md`
- [ ] Содержит: phase_id, archived_at, entries_moved count, cross_refs preserved list,
      oq_closed list (если applicable), STATUS.md before/after diff snippet
- [ ] No code, no $-numbers, no PII

## Audit & memory

- [ ] Entry в own namespace `agent-memory:memory-curator` через `memory_store` per
      memory.md schema
- [ ] `archive:phase-state:<phase-id>` marked read-only (metadata `mutable: false`)
- [ ] Subsequent attempts любой роли (даже самого memory-curator) сделать `memory_store`
      или `memory_delete` на этом namespace — должны fail с hard error

## Post-rotation verification

- [ ] `memory_list(namespace="phase-state:<phase-id>")` returns empty
- [ ] `memory_list(namespace="archive:phase-state:<phase-id>")` returns expected count
- [ ] `memory_search_unified(query=<phase-name>)` finds entries в archive (embedding HNSW
      functional)

## Final

- [ ] CloudEvent `tech.oriion.archive.rotated.v1` payload ready
- [ ] Validated против `_shared/handoff-schema.json`
- [ ] Founder notification содержит links на rotation summary + new archive namespace
