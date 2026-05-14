# 00-START-HERE — AI-agent workflow protocol

Этот файл — единственный source-of-truth для того, как AI-агент работает в проекте TEAMLY_RU. Здесь только «как работать», не «что за проект» (это в [`../README.md`](../README.md)).

## Bootstrap (обязательный для любой не-lookup задачи)

Перед первым действием по задаче прочитай ровно эти 4 файла (~15 KB суммарно):

| # | Файл | Цель |
|---|---|---|
| 1 | [`../README.md`](../README.md) | Что за проект + схема `.planning/` |
| 2 | [`../STATUS.md`](../STATUS.md) | Активная phase, активные блокеры |
| 3 | [`../HANDOFF.md`](../HANDOFF.md) | Что оставил предыдущий agent: state, in-progress, next |
| 4 | `00-START-HERE.md` (этот файл) | Workflow protocol, правила, anti-patterns |

После чтения подтверждение для пользователя — **неявное**: действуй автономно. Founder включается только на эскалациях (см. ADR-027 tier-table).

**Исключение:** для простых lookup-запросов (термин, статус, версия) достаточно шага 1–2.

## Step 2 — Task routing

| Тип задачи | Следующий шаг |
|---|---|
| Имплементация Wave 0 phase | `../roadmap/wave-0-foundation/phases/00.M-slug.md` |
| Имплементация phase Wave 1+ | Сгенерировать phase-spec через `gsd:plan-phase` (для будущих волн их нет в репо) |
| Архитектурное решение | `../decisions/README.md` + relevant ADR |
| Risk / mitigation | `../risks/REGISTER.md` (только нужный R-NN) |
| Термин | grep `../_meta/glossary.md` |
| Tech-версия | grep `../_meta/stack.md` |
| Контракт API/data | `../contracts/README.md` + relevant subdomain |
| Vertical prompts | `../verticals/<slug>/README.md` |
| Complex multi-step | [`01-CONTEXT-LOADING.md`](./01-CONTEXT-LOADING.md) → [`02-DELEGATION.md`](./02-DELEGATION.md) |

## Step 3 — JIT context loading

**Не грузи всё превентивно.** Принципы:
- Один phase-spec за раз
- ADR — только те, на которые ссылается phase
- Glossary / stack / conventions — точечный grep, не full-read
- При заходе в `.planning/X/` сначала читай `X/README.md`
- При неоднозначности — [`03-ESCALATION.md`](./03-ESCALATION.md), не строй догадки

## Context priority

| Priority | Файл | Когда |
|---|---|---|
| P0 | README + STATUS + HANDOFF + 00-START-HERE | Bootstrap, 1×/session |
| P1 | Текущий phase-spec | Task-start |
| P2 | Цитируемые ADR / risks / contracts | On reference |
| P3 | glossary / stack / conventions / OPEN-QUESTIONS | On grep |
| P4 | Other ADR / историч. контекст | Rare |

**Typical budget:** ~15–30 KB context loaded, ~80–100 KB available для работы.

## Базовые правила

1. **Уважай существующий стек.** Архитектура зафиксирована в ADR (см. `../decisions/`). Не переизобретай. Хочешь отклониться — новый ADR через template + эскалация per `03-ESCALATION.md`.
2. **TBD-tokens — не выдумывай.** Identifier вида `TBD_OOO_INN` — это литерал. Смотри `../PLACEHOLDERS.md`.
3. **Делегируй subagent'ам** ([`02-DELEGATION.md`](./02-DELEGATION.md)).
4. **Спрашивай user'а при неоднозначности** — лучше уточнить, чем сделать неправильно ([`03-ESCALATION.md`](./03-ESCALATION.md)).
5. **Фиксируй decisions:**
   - Новое архитектурное решение → ADR через `../decisions/ADR-template.md`
   - Новый риск → запись в `../risks/REGISTER.md` с mitigation
   - Новый TBD identifier → в `../PLACEHOLDERS.md`
   - Изменение в phase status → обновить `../STATUS.md`
6. **Exit ritual (обязателен перед merge PR):**
   - Дописать одну запись в `../JOURNAL.md` (append-only, шаблон в файле)
   - Перезаписать `../HANDOFF.md` (снимок состояния для следующей сессии)
   - Упомянуть оба обновления в описании PR
   - Без этих обновлений — review-gate блокирует merge.

## Topic shortcuts

- 🚀 «Начинаю работу над phase X» → [`01-CONTEXT-LOADING.md`](./01-CONTEXT-LOADING.md) + phase-spec
- 🤝 «Нужно делегировать часть задачи» → [`02-DELEGATION.md`](./02-DELEGATION.md)
- ❓ «Не понимаю, какое решение правильное» → [`03-ESCALATION.md`](./03-ESCALATION.md)
- 🎯 «Заканчиваю свою часть работы» → [`04-HANDOFF.md`](./04-HANDOFF.md)
- 📝 «Готовлю PR» → [`05-PR-WORKFLOW.md`](./05-PR-WORKFLOW.md)
- 🐛 «Что-то не работает» → [`06-DEBUGGING.md`](./06-DEBUGGING.md)
- ⚙️ «Как работает AI-team runtime» → [`07-AI-TEAM-PIPELINE.md`](./07-AI-TEAM-PIPELINE.md)

## Anti-patterns

- ❌ **Загрузка всего проекта сразу.** Don't: read all ADR + all phases + all risks. Do: bootstrap-4 + phase-spec. Остальное JIT.
- ❌ **Изобретение значений для TBD.** Don't: пишет `INN = "1234567890"`. Do: `TBD_OOO_INN` как литерал + ссылка на PLACEHOLDERS.md.
- ❌ **Архитектурные решения без ADR.** Don't: меняет DB на MongoDB в phase. Do: новый ADR + эскалация.
- ❌ **Игнорирование existing patterns.** Don't: custom auth-flow. Do: следовать ADR-007.
- ❌ **PR без Exit ritual.** Don't: merge без обновления JOURNAL+HANDOFF. Do: дописать запись + перезаписать снимок.
- ❌ **Поиск `_meta/GRILL-DECISIONS-ORIION.md`.** Файл удалён в pre-Wave-0 audit. Все политики и cross-ref решений теперь в [ADR-028](../decisions/ADR-028-policies-registry.md).

## Capabilities reminder

- **Read** — с offset/limit для больших файлов
- **Write/Edit** — для изменений
- **Bash/PowerShell** — git, build, tests, queries
- **Agent (subagents)** — для делегирования параллельных задач ([`02-DELEGATION.md`](./02-DELEGATION.md))
- **Glob/Grep** — поиск (быстрее чем full-read)
- **WebFetch/WebSearch** — актуальная docs tech-стека (не tribal knowledge)
- **TodoWrite** — tracking progress в multi-step task

## Финальный checklist готовности

После bootstrap ты должен мочь ответить:
- [ ] Что за проект (one-liner)?
- [ ] Какая wave / phase активна?
- [ ] Какие блокеры сейчас active?
- [ ] Что оставил предыдущий agent (HANDOFF)?
- [ ] Куда делегировать если нужно?
- [ ] Как escalate если непонятно?

Если не уверен — перечитай bootstrap-4.
