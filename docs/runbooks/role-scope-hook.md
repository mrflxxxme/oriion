# Runbook — role tool-scope enforcement hook

> Closes the 01.8c SECURE-audit **P2** (chip `task_dd666049`). Native subagent frontmatter
> `tools:` gives only COARSE (tool-level) restriction; the fine-grained path / sub-command
> scope in each `.claude/agents/<role>/tools-allowlist.md` was prompt-enforced only. This
> PreToolUse hook makes it **capability-enforced** for the read-only / gate roles.

## What it does

`scripts/autonomy/role_scope_hook.py` fires on every `Write` / `Edit` / `Bash` (+ PowerShell /
NotebookEdit) tool call. It reads the Claude Code PreToolUse payload and keys on `agent_type`
(present only when the call comes from **inside a subagent**; absent for the main agent):

| Caller | Behaviour |
|---|---|
| main agent (no `agent_type`) / implementer / built-in / unknown role | **allow** (fail-open on identity — the runner + `backend-implementer` etc. are never blocked) |
| `reviewer-security` / `reviewer-backend` / `reviewer-frontend` | Write/Edit only under `revisions/`; Bash mutations denied |
| `verifier` | Write/Edit only under `verification-reports/`; Bash mutations denied |
| `architect` | Write/Edit only under `.planning/decisions/`, `.planning/_meta/audits/`, `.planning/risks/`; Bash mutations denied |
| `evaluator` | Write/Edit only under `.tmp/evaluator-runs/`, `evidence/`; Bash mutations denied |

**Denied Bash mutations** (the security core of every handbook's "Denied (hard)"): `git commit/push/
reset/rebase/merge/cherry-pick/revert/restore/clean`, `git checkout --`, `git branch -D`, `git stash
drop|pop|apply`, `git worktree`, `--force`, `rm -r*`, `sudo`, `chmod/chown`, package installs
(`pip/uv/poetry/npm/pnpm/yarn install|add|ci`). Read / test / scan / eval commands pass.

Fail posture: **fail-open** on identity-unknown (never bricks the main agent), **fail-closed** on a
restricted role's Write path-check. Exit 0 = allow, exit 2 = block (stderr → the agent, which then
emits a verdict + delegates the mutation to an implementer). It is purely additive safety over the
existing tripwire+ack merge gate + backend CI.

## FOUNDER ACTION — arm it (Claude cannot self-install hooks)

Merge the `hooks` block from [`.claude/autonomy/settings.hook-snippet.json`](../../.claude/autonomy/settings.hook-snippet.json)
into `.claude/settings.json` (it adds the second PreToolUse matcher alongside `premerge_hook`).
Verify after arming:

```bash
python -c "import json; json.load(open('.claude/settings.json'))"   # valid JSON
```

## cwd caveat (shared with premerge_hook)

The hook command `python scripts/autonomy/role_scope_hook.py` resolves **relative to the shell cwd**.
If a tool leaves the persistent shell cwd in a sub-dir without the script (e.g. `frontend/`), the hook
can't find its script and blocks all shell tools. **Always run shell tools from the repo root** — use
a subshell `(cd backend && …)` for sub-dir commands so the parent cwd stays at root. Recovery if
bricked: drop a temporary `<subdir>/scripts/autonomy/role_scope_hook.py` allow-stub, `cd` back to root,
delete it. (See memory `teamly-premerge-hook-cwd-fragility`.)

## Keeping the policy in sync

The per-role write-prefixes live in `role_scope_hook.py::_WRITE_ALLOW`, a **curated mirror** of each
handbook's "Allowed (write)" section (the prose tables are not reliably machine-parseable — a reworded
table would silently disable enforcement, worse than a reviewed policy). When a role's
`tools-allowlist.md` write-scope changes, update `_WRITE_ALLOW` in the same PR.
`scripts/autonomy/check_subagents.py` (`ci-autonomy`) asserts every scoped role stays spawnable + keeps
its `tools-allowlist.md`, and that every frontmatter `tools:` token is a valid Claude Code tool.

## Tests

`backend/tests/tooling/test_role_scope_hook.py` — main-agent/implementer never blocked, per-role Write
fencing, Bash mutation deny-list, command-position matching, unparseable→fail-open, exit-code contract.
Run: `(cd backend && uv run pytest tests/tooling/test_role_scope_hook.py -q)`.

## Known limitation

Bash is enforced by a **deny-list of mutations** (not a per-role allow-list): reviewer/verifier/eval
commands are open-ended (LLM SDK calls, test runners) and a fail-closed allow-list would over-block. The
enforced invariant is "a read-only/gate role cannot commit/push/install or mutate git state" — the
separation-of-duties property the SECURE audit flagged. Tighter per-role Bash allow-listing is a future
option if a role needs it.
