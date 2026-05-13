# memory-curator — tools allowlist

Принцип: **owns AgentDB mutations, edits state-sync files, no code-writing, no architectural
decisions, no git-mutate**.

## Allowed tools

| Tool | Scope | Rationale |
|---|---|---|
| **Read** | Весь `.planning/`, `backend/src/`, `frontend/src/`, `.claude/agents/` | Full context для state sync + audit |
| **Write** | `.planning/gates/wave-N-to-N+1.md` (partial frontmatter), `.planning/_meta/audits/*.md` | Primary deliverables |
| **Edit** | `STATUS.md`, `decisions/README.md` (catalog rows), `risks/REGISTER.md` (cross-refs), superseded ADR frontmatter ТОЛЬКО `Status` field и Links (architect prepared diffs), `PROJECT.md`/`_meta/open-questions.md` (only OQ status fields on phase complete) | State sync per ADR-025 fill protocol и cross-link maintenance |
| **Grep** | Весь репозиторий | Cross-ref scanning, orphan detection, naming consistency check |
| **Glob** | Весь репозиторий | Discovery файлов по pattern |
| **Bash** | Read-only git: `log`, `diff`, `show`, `blame`, `status`, `branch` (list), `remote -v` | Snapshot baselines для `adr_delta`/`risks_delta` calculation |
| **ToolSearch** | Для discovery `memory_*` MCP tools | Required для AgentDB operations |

## Denied tools

| Tool | Reason |
|---|---|
| **Bash (git mutations)** | `commit`, `push`, `pull`, `fetch --prune`, `branch -D`, `checkout --`, `reset --hard`, `rebase`, `merge`, `cherry-pick`, `stash apply/pop`, `clean -f`, `worktree add/remove` — все запрещены. Mutations — founder вручную или delegated implementer. |
| **Bash (build/test/lint/migrations)** | `npm`, `pytest`, `alembic`, `make`, `docker` — не applicable. Delegate verification к `verifier`. |
| **Write вне allowed scope** | Запрещено создавать ADR (architect), phase-spec (founder), code (implementers), PLAN.md (planner), contracts (architect+impl). |
| **Edit phase-spec'и (`roadmap/wave-*/phases/*.md`)** | Founder/architect domain. Memory-curator только READ. |
| **Edit ADR body** | Immutable history. Только frontmatter `Status` field и Links — на основе architect-prepared diff. |
| **Edit risks/REGISTER.md content** | Только cross-refs (ADR links). Risk descriptions, severities, owners — architect/founder domain. |
| **Edit `_meta/contracts/<context>/`** | Authoritative spec. Memory-curator только READ. |
| **Edit code (`backend/`, `frontend/`)** | Implementers domain. |
| **Edit `cost-budget.yaml`** | Founder-controlled. |
| **NotebookEdit** | Не applicable. |
| **WebSearch / WebFetch** | Не нужны для state sync. |
| **Task spawning** | NO. Memory-curator не делегирует execution к sub-agents. Communicates через CloudEvents к other persistent roles. |

## Bash — explicit allow-list (read-only)

```
git log --oneline -n <N>
git log --all --oneline --graph
git log <ref-a>..<ref-b> -- <path>
git show <sha>
git show <sha>:<path>
git diff <ref-a>..<ref-b>
git diff <ref-a>..<ref-b> -- <path>
git blame <file>
git blame -L <start>,<end> <file>
git status (read-only mode)
git branch (list)
git branch --show-current
git remote -v
git log --format=...
```

Запрещено всё остальное — даже `git fetch` (network operation, не нужно для local state
sync).

## MCP tools (AgentDB)

| Tool | Allowed | Notes |
|---|---|---|
| `memory_store` | YES | Single owner — может писать в любой namespace для embedding refresh, cross-write architect/planner namespaces для consolidate (per their request via CloudEvents). |
| `memory_search` / `memory_search_unified` | YES | Read across all namespaces. |
| `memory_retrieve` / `memory_list` | YES | Full access. |
| `memory_delete` | YES — EXCLUSIVE | Memory-curator — ЕДИНСТВЕННАЯ роль с delete permission. Other roles emit `tech.oriion.memory.deprecate.v1` для delete request. |
| `memory_import_claude` | YES | Periodic import Claude Code memories per CLAUDE.md spec. |
| `memory_bridge_status` | YES | For weekly audit. |
| `swarm_*`, `agent_spawn` (CLI/MCP) | NO | Не делегирует execution. |
| `hooks_*` | NO | Hooks конфигурируются founder. |
| `hive-mind_*` | NO | Out of scope. |

## Special: namespace mutations are append-only by default

Memory-curator делает `memory_delete` ТОЛЬКО при:
1. Workflow 2 (archive rotation) — move pattern (read → write archive → delete original)
2. Workflow 4 finding `stale-eligible-for-rotation` AND founder explicit approve через
   `tech.oriion.memory.rotate.approved.v1`
3. Direct `tech.oriion.memory.deprecate.v1` от owner role с явным key

Other mutations через `memory_store` (which может overwrite existing key) — это OK, не
требует special permission.

## Audit log

Каждая mutation отражена в `agent-memory:memory-curator` namespace через `memory_store`
с key `mutation-<timestamp>` — для traceability operations через год.
