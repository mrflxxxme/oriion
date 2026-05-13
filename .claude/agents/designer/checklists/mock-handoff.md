# Checklist: mock handoff к frontend-implementer

Запускается перед эмиссией `tech.oriion.design.mock.v1`. Все пункты должны быть `[x]`, иначе handoff блокируется.

- [ ] **Tokens compliance.** Все использованные цвета / spacing / typography взяты из `_meta/ui/design-tokens.md` (nordic-warm палитра). Inline custom-цвета отсутствуют.
- [ ] **Components inventory match.** Все `components-used` из `ui-spec:` найдены в `_meta/ui/component-inventory.md`. Список `new-components-needed` либо пуст, либо явно вынесен в validation_report.
- [ ] **Interaction states covered.** Для каждой `pages[]` отрисованы все states из `interaction-states` (loading, empty, error, populated — что применимо).
- [ ] **A11y must-have документирован.** Каждый пункт `a11y-must-have` из `ui-spec:` отражён в mock (keyboard-nav, screen-reader labels, focus-trap, contrast AA).
- [ ] **Responsive baseline.** Mock проверен минимум на 2 breakpoint'ах (mobile 375px, desktop 1280px).
- [ ] **Preview link работает.** `mcp__Claude_Preview__preview_start` успешно отрисовал HTML preview, console_logs чист (no JS errors).
- [ ] **Handoff envelope валиден.** JSON прошёл validation против `_shared/handoff-schema.json`, все required поля заполнены.
