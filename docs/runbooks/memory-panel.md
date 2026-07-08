# Runbook — Memory panel «Что помнит команда/агент» (Phase 01.4-ui)

Frontend-панель для просмотра/контроля памяти команды поверх live API `/api/v1/memory/*` (ADR-011).

## Что это
- Маршрут `/memory` (навигация в `AppLayout`). Два таба:
  - **Ячейка** — cell-memory (общая память ячейки; scope неявный через RLS tenant-context).
  - **Агент** — role-memory по выбранному agent-instance (picker из `GET /api/v1/cells/{cell_id}/agents`).
- На каждой записи: содержимое, `kind`, source-бейдж (`manual` / `filter_agent` / `summary`), даты.
- Действия: семантический поиск (`?q=`), добавление (`source=manual`), удаление с подтверждением (Radix Dialog). «Редактирование» = удалить + добавить заново (бэк append-only, PATCH нет).
- Авторизация: как у API — cell-scoped через RLS, без Owner-gate → любой член ячейки может добавлять/удалять свою ячейковую память.

## Как проверить (server-verify после деплоя)
1. Открыть `https://staging.профики.online`, залогиниться (или зарегистрироваться).
2. Перейти в раздел «Память» (`/memory`).
3. Таб **Ячейка**: добавить запись → появляется в списке с бейджем `manual`; поиск по подстроке содержимого возвращает её; удалить → подтвердить → исчезает.
4. Таб **Агент**: выбрать агента в селекте → отображается role-memory этого агента (пусто, если агент ещё ничего не запоминал).
5. API-проверка (без UI): `GET /api/v1/memory` с Bearer-токеном должен вернуть добавленную запись; после DELETE — отсутствовать.

## Гейты фазы
Frontend-only: `cd frontend && npm run lint && npm run typecheck && npm test` (vitest + jest-axe). Tripwire-free (auto-merge). Live-golden N/A.
