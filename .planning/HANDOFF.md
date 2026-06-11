# HANDOFF — current session snapshot

> Перезаписывается каждой завершённой сессией как часть Exit ritual (см. `agent-handbook/05-PR-WORKFLOW.md`). История доступна через `git log HANDOFF.md`. Журнальный лог — в `JOURNAL.md`.

## Last updated

- Date: 2026-06-11 (Founder grill-аудит после 00.1–00.7: правки .planning + 3 быстрых фикса чистоты вывода)
- Session: `reverent-euclid-3bbf83`
- Agent: @claude-fable

## Project status

- **Wave:** Wave 0 (Foundation) — **closing**. Build-фазы 00.1–00.7 ✅; архитектура live-validated. Остались: **Phase 00.8 (design restyling, NEW)** + founder staging 10× anchor run (gate D5 — независимый Track A, 00.8 его не гейтит).
- **Phase 00.1–00.7**: ✅ Complete (см. STATUS.md / git history).
- **Phase 00.8 (design restyling)**: ⏳ Pending — создана этой сессией per [ADR-031](./decisions/ADR-031-design-direction-restyling.md). Spec: `roadmap/wave-0-foundation/phases/00.8-design-restyling.md`.
- **Phase 01.1 retro**: ⏳ Pending — AC-W1-1..23 + **NEW AC-W1-24/25** (Coordinator generalization на произвольные промпты + role-prompt example diversification).

## Active blockers

| ID | Описание | Owner | Block уровень |
|---|---|---|---|
| OQ-04 | РКН-уведомление оператора ПДн | Founder + юрист | Submitted — dev unblocked; final РКН до prod-launch |
| OQ-02 | Юр.форма ООО vs ИП | Founder | НЕ блокирует тех.разработку; до ЮKassa (Wave 1) |

## What just happened — grill-session 2026-06-11

Founder провёл промежуточный аудит по 4 темам (дизайн / универсальность агентов / чистота вывода / консистентность доков). 6 решений зафиксированы через grill (см. JOURNAL.md запись). Итог сессии — доки + 3 дешёвых кода-фикса; имплементация крупного — фазами.

### Код (quick fixes, чистота вывода)

1. **`backend/src/runtime/dispatch.py`** — `strip_wrapping_fence` (срез обёрточного ```-фенса, включая ```markdown-маркер) + `normalize_artifact_markdown` (фенс + frontmatter + хвостовой structured-summary). Применение двухуровневое: leaf-вывод — только фенс (чтобы `prior_context` для analyst/writer сохранял мету); `ArtifactRef.path_or_inline` — полная нормализация. +7 unit-тестов; `tests/runtime` 50/50.
2. **Role-prompts 0.1.0 → 0.1.1** (8 файлов: `backend/role_prompts/` + `.planning/contracts/role-prompts/`, синхронны per AC-W1-20): §3 — тело артефакта = чистый публикуемый документ; мета (допущения/уверенность/gaps/обращения к Координатору) только во frontmatter + structured summary (машинные блоки, платформа срезает перед показом, но передаёт по конвейеру); запрет ```-обёртки всего ответа; writer `[assumption]` → frontmatter-only.
3. **`frontend/src/features/tasks/TaskResultPage.tsx`** — «Результат» показывает финальные документы (матрица + бриф); межшаговая «Аналитика (рабочий документ)» и неизвестные типы — в свёрнутом `<details>` «Промежуточные материалы». Без 19-го ui-компонента (CI barrel-гейт = 18). Frontend 156/156, lint + `tsc`+build green. E2E-ассерты не задеты (проверено).

### Доки

- **Phase 00.8** + строки в wave-0 PHASES/README + roadmap/README; счётчик гейта «7 phases» → «9».
- **ADR-031** (Proposed; flip → Accepted при exit 00.8 с выбранным акцентом) + decisions/README.
- **Pixel reframing**: ADR-004 revision-note + wave-2 README/PHASES — pixel-герои = опциональный скин (opt-in), базовый бренд = professional nordic; «5 героев» в 02.1 синхронизировано с README (3 в W2 + 2 в W3).
- **OQ-09** — направление зафиксировано, открытым остаётся имя/домен/финальный бренд (W2). **design-tokens.md** — forward-note v0.2 (значения не менялись).
- **01.1-retro** — AC-W1-24 (произвольные промпты: удалить `_SUB_PROMPT_FRAMING`/`DEFAULT_PIPELINE`/`_ARTIFACT_KIND`; тип артефакта от Координатора; маркет-бриф остаётся только демо-пресетом) + AC-W1-25 (≥2 не-бриф примера на роль в §6 + clean-artifact conformance на golden-прогонах) + Note о лендинге quick-фиксов.

### Не сделано сознательно (по решениям грилла)

- Рестайлинг НЕ имплементирован — это Phase 00.8 (вход через `gsd:ui-phase`).
- Агенты НЕ генерализованы — ничего до 01.1 (AC-W1-16/24/25).
- Лендинг по teamly.to не делаем; полный ребрендинг — W2 (OQ-09).

## Verification state

- Backend: `uv run pytest tests/runtime` — 50/50 PASS (новые: fence/frontmatter/summary stripping, идемпотентность, выживание `### Пост N`, prior_context-keeps-meta).
- Frontend: `npm test` 156/156 PASS (новый: disclosure collapsed-by-default + opens-on-click), `npm run lint` 0 warnings, `npm run build` OK.
- **Рекомендуемый шаг перед anchor run:** один живой прогон `npm run e2e:live` — увидеть чистые артефакты глазами + проверить, что бриф не просел по длине после среза frontmatter (AC-W1-22 уже отслеживает ≥1500w; live ранее давал 1018w).

## Carryover — read order for the next session

1. `README.md` → 2. **this HANDOFF.md** → 3. `STATUS.md` → 4. `agent-handbook/00-START-HERE.md` → 5. для 00.8: `roadmap/wave-0-foundation/phases/00.8-design-restyling.md` + ADR-031 + `ui/design-tokens.md`; для Wave-1: `roadmap/wave-1-core-mvp/phases/01.1-retro.md`.

## Next actions

1. **Merge PR этой сессии** (код-фиксы + .planning).
2. **Execute Phase 00.8**: `gsd:ui-phase` (UI-SPEC) → plan → execute; accent bake-off с founder.
3. **Founder staging 10× anchor run** (gate D5) — параллельно, независимо от 00.8; артефакты теперь чистые.
4. Wave 1 старт: 01.1-retro первым (AC-W1-1..25).

## Exit ritual (this session)

- [x] HANDOFF.md rewritten — grill-аудит + quick fixes + Phase 00.8
- [x] STATUS.md updated — Phase 00.8 Pending, активная фаза, history-таблица
- [x] JOURNAL.md prepended — запись 2026-06-11 reverent-euclid (6 решений + done-список)
- [x] ADR-031 создан + decisions/README; ADR-004 revision-note
- [x] Wave-0/1/2 roadmap-доки синхронизированы
- [ ] Wave-0 anchor flip — pending founder staging 10× (Track A, независимый)
