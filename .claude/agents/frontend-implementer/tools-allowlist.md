# Frontend implementer — tools allowlist

## Allowed

- **File ops:** `Read`, `Write`, `Edit`, `Glob`, `Grep` (полный набор в `frontend/src/**` и `tests/frontend/**`).
- **Bash (scoped):** `npm run lint`, `npm run typecheck`, `npm test`, `git add`, `git commit`, `git push --force-with-lease` (только feature-branch), `git status`, `git log`, `git diff`.
- **Delegation:** `Task` (spawning `gsd-executor`, `Frontend Developer` skill, `Senior Developer` skill).
- **Preview verification:** `mcp__Claude_Preview__preview_*` (для smoke-check рендера).

## Denied

- `Write`/`Edit` в `_meta/ui/design-tokens.md`, `_meta/ui/component-inventory.md` — это designer + founder approve.
- `Write`/`Edit` в `backend/src/**` — это backend-implementer.
- `Write`/`Edit` в `.planning/decisions/**` — это architect.
- `git push --force` без `-with-lease` — запрещено per [ADR-027 §7](../../../.planning/decisions/ADR-027-solo-ai-git-pr-workflow.md).
- `git push` в `main` напрямую — branch-protection не даст, но и попыток не должно быть.
- Прямые HTTP-вызовы к production API (`WebFetch` к prod URLs) — только локальный dev-server.

## Rationale

Implementer должен иметь полный write-доступ к frontend codebase + git, но строго ограничен от модификации design-system и кросс-доменных артефактов. `--force-with-lease` нужен для revision-loop'а (Playbook 2).
