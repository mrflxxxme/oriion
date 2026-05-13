# backend-implementer — tools allowlist

Принцип: **code-writing in `backend/`, test/build/lint via Bash, atomic git commits,
NO mutations к `_meta/contracts/` or other spec layers**.

## Allowed tools

| Tool | Scope | Rationale |
|---|---|---|
| **Read** | Весь репозиторий | Need full context: contracts, ADRs, plan, existing code, related contexts |
| **Write** | `backend/src/<context>/**`, `backend/tests/<context>/**`, `backend/alembic/versions/<context>/**` | Primary deliverable — new code files |
| **Edit** | Existing files в same scope as Write + PLAN.md status column only | Iterative implementation + status sync |
| **Grep** | Весь репозиторий | Find existing impl, dependencies, naming consistency |
| **Glob** | Весь репозиторий | Discovery |
| **Bash** | См. explicit allow-list ниже | Test, build, lint, alembic, git read+limited mutations |
| **Task** | `subagent_type` ограничен: `architect` (escalation only) | Limited delegation |

## Denied tools

| Tool | Reason |
|---|---|
| **Write/Edit `_meta/contracts/<context>/**`** | HARD DENY. Authoritative spec — меняется через ADR-process via architect. Even «маленькая правка» нарушает P-INIT-2. |
| **Write/Edit `_meta/**` other** | Out of scope (ADR-architect, planner). |
| **Write/Edit ADR files** | Architect domain. |
| **Write/Edit `risks/REGISTER.md`** | Architect / memory-curator domain. |
| **Write/Edit phase-spec'и (`roadmap/wave-*/phases/**.md`)** | Founder/architect domain. Implementer только READ. |
| **Edit PLAN.md tasks/dependencies/handoff** | Planner domain. Implementer touches ТОЛЬКО status column для own tasks. |
| **Write/Edit `frontend/**`** | frontend-implementer domain. |
| **Write/Edit `.claude/**` (own role config)** | Founder governance. |
| **Bash: `rm -rf _meta/contracts/`** | HARD DENY. |
| **Bash: `git push --force`** (без `-with-lease`) | Per ADR-027 §7. |
| **Bash: `git push --force-with-lease` к `main` branch** | Per ADR-027 §1, main защищена branch-protection. Allowed только на feature/* branches. |
| **Bash: `git commit --amend`** после reviewer revision | Per ADR-027 §6: новый commit. |
| **Bash: `git reset --hard` к main** | Destructive. |
| **NotebookEdit** | Не applicable. |
| **WebSearch / WebFetch** | Не нужны для implementation (spec уже в contracts). Если нужна Python библиотека documentation — founder может paste relevant snippet. |

## Bash — explicit allow-list

### Test / lint / build

```
pytest backend/tests/<context>/ -v
pytest backend/tests/<context>/test_X.py::test_Y -v
pytest backend/tests/<context>/ -v --cov=backend/src/<context>
ruff check backend/src/<context>/
ruff format backend/src/<context>/
mypy --strict backend/src/<context>/
python -m pip install <package>   # only when PLAN.md task explicitly requires new dep
```

### Alembic

```
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini upgrade <revision>
alembic -c backend/alembic.ini downgrade -1
alembic -c backend/alembic.ini downgrade <revision>
alembic -c backend/alembic.ini current
alembic -c backend/alembic.ini history
alembic -c backend/alembic.ini revision -m "<msg>" --autogenerate   # rarely; prefer hand-written для control
```

### Git — read-only

```
git status
git log --oneline -n <N>
git log --all --oneline --graph
git diff
git diff <ref-a>..<ref-b>
git show <sha>
git blame <file>
git branch --show-current
git remote -v
```

### Git — limited mutations (allowed)

```
git add backend/<specific-paths>      # explicit paths, NOT `git add .` or `git add -A`
git commit -m "<message>"             # per ADR-027 §4 format
git push origin feature/<branch>      # push к own feature branch
git push --force-with-lease origin feature/<branch>   # ONLY если pre-push rebase локально
git pull origin <branch>              # if working in shared feature branch
git fetch origin                      # update refs
git checkout feature/<branch>         # switch к own feature branch
git checkout -b feature/wave-N-phase-NN.M-<slug>  # new feature branch
```

### Git — DENIED mutations

```
git push origin main                  # main защищена branch-protection
git push --force origin <any>         # use --force-with-lease
git push --force-with-lease origin main   # main защищена
git reset --hard <ref>                # destructive
git rebase main                       # founder does pre-merge rebase per ADR-027 §2
git rebase -i                         # interactive — founder only
git merge <branch>                    # merge — through PR, not direct
git cherry-pick <sha>                 # founder discretion
git branch -D <branch>                # destructive
git clean -fd                         # destructive
git checkout -- <file>                # destructive (discards changes)
git restore --staged --worktree .     # destructive
```

## MCP tools

| Tool | Allowed |
|---|---|
| `memory_search` / `memory_search_unified` | YES — retrieve FastAPI patterns, Pydantic recipes, Alembic pitfalls |
| `memory_store` | YES — namespace `agent-memory:backend-implementer` only (own writes); `phase-state:<phase-id>` append-only для own task progress |
| `memory_retrieve` / `memory_list` | YES |
| `memory_delete` | NO — owned `memory-curator` |
| `swarm_*`, `agent_spawn` (CLI) | NO |
| `hooks_*` | NO |

## Pre-commit safety

Before every `git commit` — self-check:
1. No secrets / credentials в diff (grep по common patterns: `password=`, `api_key=`,
   `secret=`, `BEGIN PRIVATE KEY`)
2. No `_meta/contracts/` modifications в diff
3. No `print()` statements в production code (use structured logger)
4. No `TODO` без issue/OQ reference
5. Tests added для new code
6. Lint passes
7. Commit message matches ADR-027 §4 format

If any fails — abort commit, fix.

## Audit log

Каждый commit отражает `Pipeline-role: backend-implementer` (per ADR-027 §4). Memory
store entry per task complete в `phase-state:<phase-id>` для traceability.
