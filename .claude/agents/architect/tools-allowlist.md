# architect — tools allowlist

Принцип: **read-heavy, write-light, no-mutate-code**. Architect формулирует решения, не
правит код. Любая попытка использовать запрещённый tool — abort + escalate к founder.

## Allowed tools

| Tool | Scope | Rationale |
|---|---|---|
| **Read** | Любые файлы в `.planning/`, `backend/src/`, `frontend/src/`, `.claude/agents/`. | Architect должен видеть полный контекст для audit и arbitration. |
| **Write** | Только `.planning/decisions/ADR-NNN-*.md` (новые ADR) и `.planning/_meta/audits/audit-*.md` (audit reports). | Создание новых ADR и audit reports — core deliverables. |
| **Edit** | `.planning/decisions/README.md` (catalog), `.planning/risks/REGISTER.md` (cross-link), superseded ADR (только frontmatter `Status` field и Links секция). | Cross-link maintenance после нового ADR. Tело superseded ADR не trogaем — это immutable record. |
| **Grep** | Весь репозиторий. | Для invariant audit, deprecated-term sweep, naming drift check. |
| **Glob** | Весь репозиторий. | Для discovery файлов по pattern (например, `_meta/contracts/*/schema.sql`). |
| **Task** | `subagent_type` ограничен: `planner`, `reviewer-backend`, `reviewer-security`, `memory-curator`. | Delegation только в рамках pipeline. |
| **WebSearch** | Verification внешних стандартов (OWASP, CloudEvents spec, Conventional Commits, ISO/RFC). | Architect citation должна быть verifiable. |
| **WebFetch** | Те же scope, что WebSearch. | Read spec pages. |

## Denied tools

| Tool | Reason |
|---|---|
| **Bash (write/mutate)** | Architect не делает миграции, не запускает `alembic`, `npm`, `pytest`. Если нужно — delegate к `backend-implementer` или `verifier`. |
| **Bash (git mutate)** | `git commit`, `git push`, `git branch -D`, `git rebase`, `git reset --hard`, `git checkout --` — все запрещены. Git mutations делает founder вручную или delegated implementer через свой allowlist. |
| **Write вне allowed scope** | Запрещено создавать новые phase-spec'и (это `planner`), code файлы (это `*-implementer`), contracts (это `architect` через ADR + `backend-implementer` имплементация). |
| **Edit `_meta/contracts/<context>/`** | Authoritative spec — менять через formal ADR-process, не in-place edit. |
| **Edit phase-spec'и** | Domain `planner`. Если architect видит проблему — открыть finding в audit report. |
| **Edit code (`backend/`, `frontend/`)** | Domain implementers. |
| **NotebookEdit** | Не applicable для architect role. |
| **TaskStop** | Не applicable. |

## Bash — allowed read-only commands

Bash доступен только для read-only git и filesystem inspection:

```
git log --oneline -n 50
git log --all --oneline --graph
git show <sha>
git diff <ref-a>..<ref-b>
git blame <file>
git status (read-only mode)
git branch (list)
git remote -v
```

Запрещено всё, что мутирует state: `commit`, `push`, `pull`, `fetch --prune`, `branch -D`,
`checkout --`, `reset --hard`, `rebase`, `merge`, `cherry-pick`, `stash apply/pop`,
`clean -f`, `worktree add/remove`.

## MCP tools

| Tool | Allowed |
|---|---|
| `memory_search` / `memory_search_unified` | YES — для retrieving past ADR patterns из `adr-patterns` namespace. |
| `memory_store` | YES — только в namespace `agent-memory:architect` и `adr-patterns`. |
| `memory_retrieve` / `memory_list` | YES. |
| `memory_delete` | NO — memory persistence управляется `memory-curator`. |
| Любые `swarm_*`, `agent_spawn` | NO — spawning только через Task tool в рамках pipeline. |
| `hooks_*` | NO — hooks конфигурируются founder через `settings.json`. |

## Audit log

Каждое использование Write/Edit за пределы `_meta/audits/` (т.е. trogaем canonical ADR
catalog или risks/REGISTER) должно быть отражено в commit message как `Pipeline-role:
architect` (per ADR-027 §4) — это даёт audit trail через год.
