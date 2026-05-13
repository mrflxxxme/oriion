# reviewer-security — tools allowlist

Security boundary. Anything not listed is **denied**. Violation = audit
log + `verdict: escalate` with `reason: tool-violation`.

## Allowed (read-only inspection)

| Tool | Scope | Notes |
|---|---|---|
| `Read` | any path under repo root | source, contracts, prompts, configs |
| `Grep` | any path under repo root | content search (secret-pattern hunts) |
| `Glob` | any path under repo root | file discovery |
| `WebFetch` | `https://nvd.nist.gov/*`, `https://cve.mitre.org/*`, `https://github.com/advisories/*`, `https://owasp.org/*`, `https://www.cisa.gov/known-exploited-vulnerabilities-catalog`, vendor advisory pages | CVE / advisory lookup |
| `ToolSearch` | catalog query only | discover deferred MCP security tools |

## Allowed (write — narrow)

| Tool | Scope | Notes |
|---|---|---|
| `Write` | `revisions/<phase-id>-reviewer-security.md` AND `revisions/<phase-id>-reviewer-security-critical.md` only | revision + critical artefact per ADR-027 §6 |
| `Edit` | same paths as Write | amend own revision files across cycles |

## Allowed (Bash — read-only sub-commands)

Strict allowlist:

- `git status`
- `git diff` (any flags except `--apply`)
- `git log` (any flags, including `git log -p -S<pattern>` for
  secret-history scans)
- `git show <ref>`
- `git rev-parse <ref>`
- `git ls-files`
- `npm audit --json`
- `npm audit signatures`
- `pip-audit --strict` / `pip-audit --format json`
- `safety check --json`
- `semgrep --config auto --json`
- `trivy fs --severity HIGH,CRITICAL --format json .`
- `trivy config --format json .github/workflows/`
- `bandit -r backend/src/ -f json`
- `gitleaks detect --no-banner --report-format json --report-path /tmp/gitleaks.json`
- `ruff check` (read-only)
- `mypy backend/` (read-only)

Any other Bash invocation → denied.

## Allowed (deferred MCP, load via ToolSearch when needed)

- `mcp__plugin_oh-my-claudecode_t__lsp_diagnostics` — read-only LSP
  diagnostics on touched files.
- `mcp__plugin_oh-my-claudecode_t__lsp_diagnostics_directory` —
  directory-wide LSP diagnostics.
- `aidefence_scan` / `aidefence_is_safe` / `aidefence_has_pii` — prompt
  injection + PII detection on diff content.

## Denied (hard)

- `Edit` / `Write` on source files (`backend/**`, `frontend/**`).
- `Edit` / `Write` on contracts (`_meta/contracts/**`).
- `Edit` / `Write` on ADR (`.planning/decisions/**`).
- `Edit` / `Write` on prompts (`_meta/verticals/**`).
- `git commit`, `git push`, `git rebase`, `git reset`, `git checkout --`,
  `git restore`, `git clean`, `git merge`, `git stash drop`.
- Any `--force` / `--force-with-lease`.
- `sudo`, `rm -rf`, `chmod`, `chown`.
- `npm install`, `pip install`, `poetry add` — never install anything;
  audit must run against the committed lock-file as-is.
- Network mutation (POST/PUT/DELETE via curl / WebFetch).
- MCP tools that mutate external state (Linear / Asana / GitHub PR
  merge / Telegram outbound).

## Rationale

A security reviewer that can mutate code becomes an attack vector. The
agent reads, scans, and writes verdicts. Founder remains the only
entity that mutates `main`. Per ADR-023 §6 and ADR-027 §5.
