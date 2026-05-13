# reviewer-backend — tools allowlist

Security boundary. Anything not listed is **denied**. Violation = audit log
entry + automatic `verdict: escalate` with `reason: tool-violation`.

## Allowed (read-only inspection)

| Tool | Scope | Notes |
|---|---|---|
| `Read` | any path under repo root | source, contracts, tests, planning |
| `Grep` | any path under repo root | content search |
| `Glob` | any path under repo root | file discovery |
| `WebFetch` | `https://*` | linking to OWASP / RFC / PEP / FastAPI docs |
| `ToolSearch` | catalog query only | discover deferred read-only tools |

## Allowed (write — narrow)

| Tool | Scope | Notes |
|---|---|---|
| `Write` | `revisions/<phase-id>-reviewer-backend.md` **only** | revision artefact per ADR-027 §6 |
| `Edit` | `revisions/<phase-id>-reviewer-backend.md` **only** | amend own revision file across cycles |

## Allowed (Bash — read-only sub-commands)

Permitted commands (must match exactly the verbs below):

- `git status`
- `git diff` (any flags except `--apply`)
- `git log` (any flags)
- `git show <ref>`
- `git branch --list`
- `git rev-parse <ref>`
- `npm test` / `npm run test:*`
- `pytest` / `pytest -q` / `pytest --collect-only`
- `alembic history`
- `alembic check`
- `ruff check`
- `mypy backend/`

Any other Bash invocation = denied. The agent must request explicit
permission via `escalate` rather than try to bypass.

## Denied (hard)

- `Edit` / `Write` on source files (`backend/**`, `frontend/**`).
- `Edit` / `Write` on contracts (`_meta/contracts/**`).
- `Edit` / `Write` on ADR (`.planning/decisions/**`).
- `git commit`, `git push`, `git rebase`, `git reset`, `git checkout --`,
  `git restore`, `git clean`, `git merge`, `git stash drop`.
- `git push --force` / `--force-with-lease` (per ADR-027 §7 reserved to
  implementer agents on their own feature branches).
- Any `sudo`, `rm -rf`, `chmod`, network mutation, package install.
- MCP tools that mutate external state (Linear / Asana / GitHub PR merge
  / Telegram outbound).

## Rationale

Per ADR-023 §6 and ADR-027 §5: reviewers are gates, not writers. The only
artefact a reviewer produces is its verdict envelope and (on
`request_changes`) the revisions file. Founder remains the only entity that
mutates `main`.
