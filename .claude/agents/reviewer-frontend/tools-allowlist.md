# Reviewer (frontend) — tools allowlist

## Allowed

- **File ops (read-mostly):** `Read`, `Glob`, `Grep` (полный read-access ко всем `frontend/src/**`, `_meta/ui/**`).
- **Write (scoped):** `Write` только в `revisions/<phase>-reviewer-frontend.md` (failure detail per ADR-027 §6).
- **Bash (read-only verification):** `git fetch`, `git checkout`, `git diff`, `git log`, `git status`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` (smoke).
- **Delegation:** `Task` (spawn `gsd-ui-checker`, `gsd-ui-auditor`, `Accessibility Auditor` skill).
- **Preview verification:** `mcp__Claude_Preview__preview_*` (для визуального smoke-check).

## Denied

- `Edit`/`Write` в `frontend/src/**` — reviewer не правит код, только flag'ает.
- `git commit`, `git push`, `git merge`, `git rebase` — review-роль не модифицирует branch.
- `Write` в `_meta/ui/**` — изменения tokens/inventory через designer + founder approve.
- `Bash` deployment / install / `npm install` (зависит от lockfile, может изменить env).

## Rationale

Reviewer должен только наблюдать и валидировать — write-доступ ограничен `revisions/*` для structured feedback. Code modifications делает frontend-implementer в response на report.
