# verifier — tools allowlist

Security boundary. Anything not listed is **denied**. Violation = audit
log + `verdict: fail` with `reason: tool-violation`.

## Allowed (read-only inspection)

| Tool | Scope | Notes |
|---|---|---|
| `Read` | any path under repo root | phase-specs, tests, contracts, gate-files |
| `Glob` | any path under repo root | test discovery |
| `Grep` | any path under repo root | criterion-ID lookup in tests |
| `WebFetch` | `https://*` | doc lookup for k6 / playwright / pytest |
| `ToolSearch` | catalog query only | discover deferred runners |

## Allowed (write — narrow)

| Tool | Scope | Notes |
|---|---|---|
| `Write` | `verification-reports/<phase-id>/**` AND `verification-reports/gates/**` | artefacts + run reports only |
| `Edit` | same paths as Write | amend report cross-runs |

## Allowed (Bash — test runners + measurement + read-only git)

Permitted commands (match exactly the verbs below):

- **Git read-only:**
  - `git status`
  - `git diff` (any flags except `--apply`)
  - `git log` (any flags)
  - `git show <ref>`
  - `git rev-parse <ref>`
  - `git ls-files`
- **Python test:**
  - `pytest` / `pytest -q` / `pytest --junitxml=<path>`
  - `pytest --collect-only`
  - `python -m pytest ...` (same flags)
- **Frontend test:**
  - `npm test` / `npm run test:*`
  - `npx playwright test`
  - `npx playwright test --reporter=junit`
- **Perf / load:**
  - `k6 run <script>` (with any `--summary-export` / `--out` flag
    targeting `verification-reports/` only)
- **Acceptance smoke:**
  - `curl -sS -o <file> -w '%{http_code}\n' <url>` (URL must be repo
    `localhost` / `127.0.0.1` / configured staging from PHASE.md, never
    arbitrary)
- **Type / lint sanity (acceptance only when AC includes it):**
  - `ruff check`
  - `mypy backend/`
- **Custom criteria-runner:**
  - `python -m oriion.acceptance.runner <phase-id>` (project-internal
    runner; mounts `verification-reports/` as output dir).

Any Bash invocation not above → denied. If a check needs a missing
runner, emit `acceptance.failed.v1` with
`reason: missing-test-runner` rather than improvising.

## Denied (hard)

- `Edit` / `Write` on source (`backend/**`, `frontend/**`).
- `Edit` / `Write` on tests themselves (verifier runs tests; planner +
  implementer write them).
- `Edit` / `Write` on contracts (`_meta/contracts/**`).
- `Edit` / `Write` on ADR (`.planning/decisions/**`).
- `Edit` / `Write` on phase-specs (`.planning/phases/**/PHASE.md`).
- `Edit` / `Write` on gate-files (`.planning/gates/*.md`) — verifier
  produces verdict envelope; memory-curator + founder mutate the file.
- `git commit`, `git push`, `git rebase`, `git reset`, `git checkout --`,
  `git restore`, `git clean`, `git merge`, `git stash drop`.
- `--force` / `--force-with-lease` (ever).
- `sudo`, `rm -rf`, `chmod`, package install.
- Mutating MCP tools (Linear / Asana / GitHub PR merge / Telegram
  outbound).

## Rationale

A verifier that can mutate source can rewrite tests to pass. A verifier
that can mutate gate-files can declare a wave-transition. Both negate
the verifier's role. Per ADR-023 §3 verifier emits verdict only;
mutation belongs to implementer (source/tests) and founder + curator
(gate-files).
