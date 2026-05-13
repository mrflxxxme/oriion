# Evaluator — tools allowlist

## Allowed

- **File ops (read-only):** `Read`, `Glob`, `Grep` (полный read во всём `_meta/verticals/**`).
- **Write (scoped):** `Write` только в `.tmp/evaluator-runs/<run-id>/` (raw run artifacts) и в handoff envelope output.
- **Bash (LLM execution + verification):** запуск LLM provider CLI / SDK (per [ADR-026]) для prompt-under-test execution. `git log` / `git diff` для tracking changes.
- **Delegation:** `Task` (spawn `gsd-nyquist-auditor` для structured-output validation).
- **WebFetch:** для verification источников из `verified-sources[]` frontmatter (опционально, on-demand).

## Denied

- `Edit`/`Write` в `_meta/verticals/<slug>/prompts/**` — это mandate `vertical-prompt-author`.
- `Edit`/`Write` в `_meta/verticals/<slug>/golden-dataset/**` — это `golden-dataset-curator`.
- `git commit`, `git push`, `git merge` — evaluator не модифицирует repo.
- `Bash` для деплоя / install / package management.

## Rationale

Evaluator — pure judge. Read-доступ ко всему vertical-context'у нужен для valid evaluation, но write-доступ строго ограничен ephemeral run-data. Любая модификация prompt / dataset должна идти через профильную роль, иначе теряется audit-trail.
