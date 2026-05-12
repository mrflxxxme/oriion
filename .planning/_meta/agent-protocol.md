# Agent Protocol — как AI-агенты работают с этим roadmap'ом

> Этот файл — для AI-агентов разработки (Claude/Codex и др.). Читать перед началом любой фазы.

## Минимальный контекст для запуска фазы

1. **PROJECT.md** — 1 раз в сессии (ориентация).
2. **wave-N/README.md** — цель и зависимости волны.
3. **phases/N.M-slug.md** — сам spec фазы.
4. **Релевантные ADR** — упомянутые в phase-файле.
5. **Релевантные секции glossary/conventions/stack** — по необходимости.

**НЕ читать full glossary/stack/conventions, если фаза не требует.** Phase-файл явно указывает, что релевантно.

## Token-efficiency правила

| Правило | Зачем |
|---|---|
| Ссылаться, не повторять | Один источник правды на термин/решение |
| Phase-файл < 200 строк | Помещается в один tool-вызов чтения |
| Использовать таблицы, не прозу | Плотность информации × 3 |
| Acceptance criteria — testable | Не «работает», а «GET /api/foo возвращает 200 со схемой X» |
| Задачи — атомарные | 1 task = 1 PR ≤ 500 строк |

## Workflow на одну фазу

```
1. Прочитать phase-spec (N.M-slug.md)
2. Создать ветку feature/<phase-id>-<slug>
3. Создать worktree (см. ADR-015) — изоляция от других AI-агентов
4. По task-list фазы:
   a. Имплементация в src/<bounded_context>/
   b. Тесты (unit + integration)
   c. Запуск local CI (pre-push hook)
5. Создать PR, заполнить шаблон
6. Tier-review (см. conventions.md)
7. После merge — обновить phase-файл: [x] checkboxes
8. Если найдены новые риски/решения — обновить risks/REGISTER.md или создать ADR
9. Если требуется изменение conventions/stack — отдельный PR + согласование
```

## Tier-роли AI-агентов (ADR-015)

| Роль | Когда вызывать | Mandate |
|---|---|---|
| **Planner** | Декомпозиция новой задачи или пересмотр phase-плана | Создаёт task-list, проверяет dependencies |
| **Coder** | Имплементация | Только код, не архитектурные решения |
| **Tester** | После Coder, перед PR | Unit + integration, edge cases |
| **Reviewer** | На каждый PR (auto) | Code review по conventions.md |
| **Security-Auditor** | На tier-3+ PR | SAST, secrets, supply chain, threat model |
| **DevOps** | На фазах с инфра-изменениями | CI/CD, IaC, observability |

Вызов через Agent tool с `subagent_type` или через CLI claude-flow.

## Лимиты ресурсов AI-агентов dev-команды

| Лимит | Значение |
|---|---|
| Per-task budget | $5 (Sonnet) / $20 (Opus) hard limit |
| Per-day per-agent | $50 |
| Per-week total | $1000 на старте, scaling по продуктивности |
| Kill-switch | 30 мин без прогресса = auto-abort |
| Worktree TTL | 7 дней без commit = cleanup |

## Что записывать обратно в roadmap

После завершения фазы AI-агент **обязан** обновить:

| Файл | Когда |
|---|---|
| `phases/N.M-slug.md` | Tasks → done, acceptance criteria → checked, фактические даты, найденные риски |
| `decisions/ADR-XXX.md` | При значимом архитектурном решении (новый файл) |
| `risks/REGISTER.md` | При обнаружении нового риска или митигации существующего |
| `_meta/stack.md` | При добавлении/смене зависимости (только version-bump, не выбор стека) |
| `_meta/glossary.md` | При появлении нового domain-термина |

## Что НЕ делать

- ❌ Создавать новые верхнеуровневые директории без обоснования
- ❌ Дублировать содержимое reference-файлов в phase-spec
- ❌ Решать архитектурные вопросы — только Planner + human Tech Lead
- ❌ Делать большие PR (>500 строк) без splitting
- ❌ Skip CI gates через --no-verify
- ❌ Получать prod-credentials в свой контекст
- ❌ Запускать миграции prod-БД самостоятельно
- ❌ Менять conventions.md без отдельного PR-обсуждения

## Knowledge persistence

Каждая dev-сессия с AI-агентом:
- **session log** сохраняется в claude-mem / project memory (ADR-015).
- **decisions** — в ADR.
- **discovered facts** — в `_meta/glossary.md` или `risks/REGISTER.md`.

Цель: после ухода человека или AI-агента контекст не теряется.
