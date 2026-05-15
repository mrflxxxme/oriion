# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-05-14
- Session: `epic-almeida-152bad` (final pre-Wave-0 audit & cleanup)
- Agent: @claude-opus

## Project status

- **Wave:** Pre-Wave-0 (preparation)
- **Active phase:** none (Wave 0 / Phase 00.1 не стартовал — ждём блокеры)
- **Next phase:** [`roadmap/wave-0-foundation/phases/00.1-repo-cicd.md`](./roadmap/wave-0-foundation/phases/00.1-repo-cicd.md) (DevOps + Tech Lead, 3 дня)

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-17 | Funding-стратегия | Founder | Required до Phase 00.1 |
| OQ-18 | Burn-бюджет | Founder | Required до Phase 00.1 |
| OQ-04 | РКН-уведомление | Founder + юрист | Required до Phase 00.2 |

Полный реестр — [`OPEN-QUESTIONS.md`](./OPEN-QUESTIONS.md).

## What just happened (this session)

Финальный аудит репозитория перед стартом Wave 0. Согласован и выполнен план `fluffy-napping-sunrise.md`:

- **Git cleanup:** 11 merged feature/milestone-c/d веток удалены (local + origin); 3 worktree сняты с реестра; 3 стале claude/* веток удалены. Остался `main` + текущий worktree.
- **Структура `.planning/`:** production-папки (`contracts/`, `verticals/`, `ui/`, `tools/`) подняты на верхний уровень из `_meta/`. `_meta/` теперь = 4 файла (README, stack, glossary, conventions; + GRILL-DECISIONS-ORIION.md под дистилляцию).
- **OPEN-QUESTIONS.md** поднят в корень `.planning/`.
- **Удалены** 36 phase-stub'ов wave-1..4, `research/teamly_to_analysis/`, `_meta/agent-protocol.md`.
- **Стандартизация:** INDEX→README во всех папках; созданы тонкие README для risks/, contracts/, verticals/, ui/, tools/.
- **Path C:** `.planning/README.md` сокращён до «what is this project» (~2 KB); `agent-handbook/00-START-HERE.md` — полный workflow protocol с обязательным bootstrap-чек-листом.
- **JOURNAL.md + HANDOFF.md** созданы; Exit ritual закреплён hard rule'ом в `agent-handbook/05-PR-WORKFLOW.md`.

## In progress / deferred to next session

- **Stage 7 (distill GRILL-DECISIONS-ORIION.md → ADR):** ещё НЕ выполнен в этой сессии. Файл `_meta/GRILL-DECISIONS-ORIION.md` пока существует. Ссылки на `DECISION-N` / `P-INIT-N` в STATUS.md, PROJECT.md, OPEN-QUESTIONS.md, прочих файлах — пока активны. Этот этап выполняется отдельным проходом аналитика-агента (см. план).
- **Slim PROJECT.md** (удаление ADR-list секций + Tariffs) — отложено до Stage 7.

## Next agent — read first

Bootstrap (4 файла):
1. [`README.md`](./README.md) — что за проект
2. [`STATUS.md`](./STATUS.md) — текущее состояние
3. этот HANDOFF.md
4. [`agent-handbook/00-START-HERE.md`](./agent-handbook/00-START-HERE.md) — workflow protocol

## Next steps (priority order)

1. **Stage 7 — Distill `_meta/GRILL-DECISIONS-ORIION.md`:**
   - Прогнать через analyst-subagent: вытащить DECISION-1..11 и P-INIT-N.
   - Не-отражённое → новые ADR (через `decisions/ADR-template.md`); отражённое частично → дополнения к существующим ADR.
   - DELETE `_meta/GRILL-DECISIONS-ORIION.md`.
   - Найти и заменить все ссылки `GRILL-DECISIONS|P-INIT-N|DECISION-N` → ссылки на конкретные ADR (`grep -r` по `.planning/`).
   - Slim `PROJECT.md`: удалить ADR-list секции (Core/UI/Backend/LLM/Security) → одна строка-ссылка на `decisions/README.md`; удалить Tariffs-таблицу → ссылка на ADR-008.
   - Обновить `decisions/README.md` — добавить новые ADR в полный список.
2. ~~Закрыть OQ-17 + OQ-18~~ — **closed `out-of-scope` per Session-2026-05-15** (founder-personal finance не tracked в project docs; AI dev caps живут в `cost-budget.yaml`).
3. **Стартовать Phase 00.1 (Repo & CI/CD)** — no remaining project-scope blockers per STATUS.md.

## Files modified this session

- Удалены: 11 git-веток, 49 .md-файлов (research + wave-phase-stubs + agent-protocol)
- Создан: `OPEN-QUESTIONS.md` (из `_meta/open-questions.md`)
- Перемещены: `_meta/{contracts,verticals,ui,tools}/` → `.planning/`
- Переписаны: `.planning/README.md`, `agent-handbook/00-START-HERE.md`, `_meta/README.md`, `roadmap/README.md`
- Изменены: `agent-handbook/05-PR-WORKFLOW.md` (+Exit ritual), 37 .md с обновлёнными путями
- Созданы: `risks/README.md`, `contracts/README.md`, `verticals/README.md`, `ui/README.md`, `tools/README.md`, `JOURNAL.md`, `HANDOFF.md`

## Known caveats

- 3 worktree-директории (peaceful-hermann, optimistic-raman, zen-murdock) сняты с git worktree list, но папки на диске не удалены (Windows file-lock от watcher-процессов). Не git-state; можно удалить вручную позже.

Все известные pre-existing broken-ссылки в `verticals/wb-seller/*` (ADR-026 filename mismatch, ADR-015 filename mismatch, `roadmap.md`, депth-3 `tools/` ссылки, `_shared/cost-budget.yaml` пути) починены в follow-up commit'е этой PR.

## Build / test state

- Этот repo — документационный. Build/test не запускаются.
- CI gates по коду активируются с Phase 00.1.
