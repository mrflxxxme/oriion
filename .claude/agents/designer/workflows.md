# Designer — workflows

Типовые playbook'и роли. Каждый — последовательность шагов с явным entry/exit условием.

---

## Playbook 1: New page mock from `ui-spec:`

**Entry:** inbound handoff `tech.oriion.plan.ui_phase.v1` с phase-spec, содержащим `ui-spec.pages[]`.

**Шаги:**

1. **Load context (JIT).** Прочесть `_meta/ui/design-tokens.md`, `_meta/ui/component-inventory.md`, `_meta/ui/CLAUDE-DESIGN-PROMPTS.md`. Загрузить только нужные секции через Grep/Read.
2. **Validate `ui-spec`.** Для каждой `pages[]` проверить: все ли `content-slots` опеределены, все ли `interaction-states` (loading/empty/error/populated) перечислены, `a11y-must-have` непуст, `components-used` ⊆ inventory.
3. **(если есть пробелы)** Spawn `gsd-ui-researcher` через Task tool для рекомендаций по паттернам. Дождаться результата, обновить локальный draft.
4. **Generate mocks.** Активировать skill `UI Designer`, передать ui-spec + tokens + selected components. Получить mock набор (PNG или HTML).
5. **Preview & verify.** Через `mcp__Claude_Preview__preview_start` отрендерить HTML preview, сверить с `interaction-states`.
6. **Compose handoff event** `tech.oriion.design.mock.v1` — payload: paths к mock-файлам, validation-report, рекомендации для `frontend-implementer`.
7. **Persist в memory.** Записать vetted pattern + token-usage в `agent-memory:designer`.

**Exit:** outbound event отправлен в `phase-state:<phase-id>`, статус роли в pipeline = `done`.

---

## Playbook 2: Component variation request

**Entry:** founder или `frontend-implementer` запросил вариант существующего компонента (например, `Button[variant=ghost-danger]`).

**Шаги:**

1. **Lookup в inventory.** Проверить `_meta/ui/component-inventory.md` — существует ли вариант.
2. **Generate вариант.** Если нет — активировать `UI Designer` skill для оформления варианта с соблюдением tokens.
3. **Propose patch** к `component-inventory.md` через handoff event `tech.oriion.design.inventory_patch.v1` (требует founder approve перед merge).
4. **Return mock** запросившему через ad-hoc reply event.

**Exit:** mock возвращён, patch-proposal в founder-queue.
