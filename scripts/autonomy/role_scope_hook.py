#!/usr/bin/env python3
"""PreToolUse hook — per-role tool-scope enforcement (chip task_dd666049).

Closes the 01.8c SECURE-audit P2. Native subagent frontmatter ``tools:`` is COARSE
(the Claude Code harness enforces the tool list) but the fine-grained path /
sub-command scope documented in each ``.claude/agents/<role>/tools-allowlist.md`` was
prompt-enforced only — a prompt-injected read-only reviewer/verifier formally still
had ``Write``/``Bash`` and could mutate source or commit, defeating separation-of-duties.
This hook makes that scope CAPABILITY-enforced for the read-only / gate roles.

Mechanism (Claude Code docs — PreToolUse fires for subagents and the payload carries
``agent_type`` when the call originates inside a subagent; absent for the main agent):
  * no ``agent_type`` (main agent) OR ``agent_type`` not a restricted role  -> ALLOW.
  * restricted role (reviewer-security/-backend/-frontend, verifier, architect, evaluator):
      - Write/Edit: ``file_path`` MUST sit under the role's allowed write-prefix(es)
        (derived from its tools-allowlist.md "Allowed (write)") — else BLOCK (fail-closed).
      - Bash: BLOCK the dangerous-mutation verbs (git commit/push/reset/rebase/merge/
        cherry-pick/revert/``checkout --``/restore/clean/stash-drop/branch-D/worktree,
        ``--force``, ``rm -r``, sudo, chmod/chown, package installs) — the security core
        of every handbook's "Denied (hard)". Read / test / scan / eval commands pass.

Fail posture: fail-OPEN on identity-unknown (never block the main agent / implementers /
unparseable Claude-generated payloads — the compensating tripwire+ack merge gate + backend
CI remain), fail-CLOSED within a restricted role's Write path-check. Purely additive.

DESIGN NOTE — the policy below is a CURATED mirror of the handbooks' "Allowed (write)" /
"Denied (hard)" sections, not a runtime parse of the prose tables: a reworded markdown
table would silently disable enforcement, which is worse than a reviewed policy that
``check_subagents.py`` cross-checks for coarse tool-set consistency. Keep this in sync
when a role's tools-allowlist.md write-scope changes.

Contract (Claude Code hooks): stdin JSON; exit 0 = allow; exit 2 = block (stderr -> agent).
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# Per-role allowed Write/Edit path-prefixes (repo-relative, forward-slash), from each
# .claude/agents/<role>/tools-allowlist.md "Allowed (write — narrow)" section.
_WRITE_ALLOW: dict[str, tuple[str, ...]] = {
    "reviewer-security": ("revisions/",),
    "reviewer-backend": ("revisions/",),
    "reviewer-frontend": ("revisions/",),
    "verifier": ("verification-reports/",),
    "architect": (".planning/decisions/", ".planning/_meta/audits/", ".planning/risks/"),
    "evaluator": (".tmp/evaluator-runs/", "evidence/"),
}
RESTRICTED: frozenset[str] = frozenset(_WRITE_ALLOW)

# Dangerous Bash mutations denied to every restricted (read-only/gate) role. Command-
# position aware (line start or after ; & | ( ) so a mention inside a quoted string /
# path does not match. Mirrors the handbooks' "Denied (hard)" verbs.
_CMD = r"(?:^|[;&|(]\s*)"
_DENY: tuple[re.Pattern[str], ...] = (
    re.compile(
        _CMD + r"git\s+(?:commit|push|reset|rebase|merge|cherry-pick|revert|restore|clean)\b", re.I
    ),
    re.compile(_CMD + r"git\s+checkout\s+--", re.I),
    re.compile(_CMD + r"git\s+branch\s+-[dD]\b", re.I),
    re.compile(_CMD + r"git\s+stash\s+(?:drop|pop|apply|clear)\b", re.I),
    re.compile(_CMD + r"git\s+worktree\b", re.I),
    re.compile(r"--force(?:-with-lease)?\b", re.I),
    re.compile(_CMD + r"rm\s+-[a-z]*[rf]", re.I),
    re.compile(_CMD + r"sudo\b", re.I),
    re.compile(_CMD + r"(?:chmod|chown)\b", re.I),
    re.compile(r"\b(?:pip3?|uv|poetry|npm|pnpm|yarn)\s+(?:install|add|ci)\b", re.I),
    re.compile(r"\buv\s+pip\s+install\b", re.I),
)


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _under(norm_path: str, prefix: str) -> bool:
    """True if norm_path sits under `prefix` (as a full path segment)."""
    return ("/" + norm_path).find("/" + prefix) != -1


def _dangerous(command: str) -> str:
    for rx in _DENY:
        m = rx.search(command)
        if m:
            return m.group(0).strip()
    return ""


def evaluate(payload: dict[str, Any]) -> tuple[bool, str]:
    """Return (allow, reason). Pure — unit-tested against synthetic payloads."""
    agent = str(payload.get("agent_type") or "")
    if agent not in RESTRICTED:
        return True, ""  # main agent / implementer / built-in / unknown -> not our concern

    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}

    if tool in ("Write", "Edit", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        if not path:
            return False, f"{agent}: {tool} with no file_path — scope unverifiable (fail-closed)."
        allowed = _WRITE_ALLOW[agent]
        if any(_under(_norm(path), pfx) for pfx in allowed):
            return True, ""
        return False, (
            f"{agent} is a read-only/gate role: it may only Write/Edit under "
            f"{list(allowed)} (per .claude/agents/{agent}/tools-allowlist.md). "
            f"'{path}' is out of scope. Emit your verdict/report there; delegate code "
            f"changes to an implementer."
        )

    if tool == "Bash":
        hit = _dangerous(str(tool_input.get("command") or ""))
        if hit:
            return False, (
                f"{agent} is a read-only/gate role: '{hit}' is a denied mutation "
                f"(tools-allowlist.md 'Denied (hard)'). Reviewers/verifiers do not "
                f"commit/push/install or mutate source — emit a verdict and let an "
                f"implementer act."
            )
        return True, ""

    return True, ""  # Read/Grep/Glob/WebFetch/ToolSearch/Task/etc. -> allow


def main() -> int:
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Fail-OPEN: the payload is Claude-generated, not user input; an unparseable
        # blob means we cannot identify the caller, so we must not block every tool call.
        return 0
    if not isinstance(payload, dict):
        return 0

    allow, reason = evaluate(payload)
    if allow:
        return 0
    print(f"[role-scope-hook] BLOCKED: {reason}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
