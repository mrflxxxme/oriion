# Designer — tools allowlist

## Allowed

- **File ops (read-only + scoped write):** `Read`, `Write` (только в `_meta/ui/reference-screens/` и `.tmp/mocks/`), `Glob`, `Grep`.
- **External integration:** `WebFetch` — для Claude Design API.
- **Delegation:** `Task` (spawning `gsd-ui-researcher` или активация `UI Designer` skill).
- **Preview rendering:** все `mcp__Claude_Preview__*` tools (start, screenshot, snapshot, resize, console_logs).

## Denied

- `Bash` (write/execute) — designer не должен запускать build / install / git.
- Любые git-modifying tools (`git add`, `git commit`, `git push`) — commits делает `frontend-implementer` после handoff.
- `Edit` / `Write` в production-коде (`frontend/src/**`, `backend/src/**`) — это mandate других ролей.
- `Edit` в `_meta/ui/design-tokens.md` и `_meta/ui/component-inventory.md` — изменения через handoff `tech.oriion.design.inventory_patch.v1` + founder approve.

## Rationale

Designer — координатор и валидатор, не исполнитель кода. Ограничение write-области предотвращает случайное изменение source-of-truth для design system'ы (см. DECISION-4 и `_meta/ui/CLAUDE-DESIGN-PROMPTS.md`).
