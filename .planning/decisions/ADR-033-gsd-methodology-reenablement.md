# ADR-033: GSD methodology re-enablement — L1 субагенты сейчас, L2 orchestrator-bridge отложен

- **Status:** Proposed (Phase 01.1 Track A, 2026-06-15)

## Контекст

[ADR-023](./ADR-023-ai-team-runtime.md) §6 утверждает, что команды
`/gsd:plan-phase` / `/gsd:execute-phase` / `/gsd:verify-work` / `/gsd:ship`
работают «из коробки», т.к. структура `.planning/` совпадает с GSD-ожиданиями.
**Это не так** (подтверждено Phase 00.8 + 01.1): GSD-валидатор
(`get-shit-done/bin/gsd-tools.cjs validate health`) требует артефактов, которых в
bespoke `.planning/` нет:

| GSD ожидает | Код health | Состояние проекта |
|---|---|---|
| `ROADMAP.md` (flat phase-index) | E003 | ❌ есть `roadmap/wave-N/` + `PHASES.md` |
| `STATE.md` | E004 (repairable) | ❌ есть `STATUS.md` + `HANDOFF.md` |
| `config.json` | W003 | ❌ нет |
| phase-dirs `NN-name/NN-MM-PLAN.md` | W005/6/7 | ❌ `roadmap/wave-N/phases/NN.M-slug.md` |

## Decision

- **L1 (сейчас, работает):** методология GSD доступна через **gsd-субагенты
  напрямую** (Agent tool): `gsd-planner` → `gsd-plan-checker` → execute →
  `gsd-verifier`. Они принимают phase-context и НЕ требуют orchestrator-state.
  В Phase 01.1 продемонстрировано: `gsd-verifier` прогнан goal-backward на Track A.
- **L2 (отложено в отдельный planning-spike):** восстановление slash-оркестраторов
  = авторинг минимального `ROADMAP.md` + `config.json` + `/gsd:health --repair`
  (генерит STATE.md) + решение layout-mismatch (тонкий адаптер vs принятие
  GSD phase-dir layout `NN-name/`). Оформляется собственным ADR при старте спайка.

## Consequences

- ADR-023 §6 claim «из коробки» помечен неточным (amendment-note в самом ADR-023 §6).
- Bespoke `.planning/` остаётся source-of-truth; GSD — инструмент, не truth-source.
- L2 НЕ в скоупе code-PR Phase 01.1 (ортогонален реализации Координатора).
- Риск L2: автогенерация STATE.md из ROADMAP может разойтись с rolling STATUS.md —
  поэтому bridge, а не миграция (миграция = высокий риск для богатого planning-корпуса).

## Links

- [ADR-023](./ADR-023-ai-team-runtime.md) §6 — GSD reuse claim (correction)
- `../agent-handbook/00-START-HERE.md` Step 2 — routing «Wave 1+ → gsd:plan-phase»
