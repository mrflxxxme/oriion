#!/usr/bin/env python3
"""PreToolUse hook — tripwire enforcement on `gh pr merge` (ADR-037 D2, Block C).

Defense-in-depth over the runner's explicit classify-step: ANY `gh pr merge`
issued from a Claude session in this repo (Bash/PowerShell tool) is intercepted.
If the PR's diff matches a tripwire category (.claude/autonomy/tripwire.yaml)
and RUN-QUEUE has no approved ack for that PR — the merge is BLOCKED (exit 2).

Scope: only agent-initiated CLI merges. The founder's manual merges via the
GitHub UI are untouched (a UI merge never passes through this hook), which is
exactly the D2 boundary: the machine pauses, the founder's click proceeds.

Contract (Claude Code hooks):
  stdin  — JSON {tool_name, tool_input:{command: ...}}
  exit 0 — allow;  exit 2 — block (stderr is fed back to the agent)
Fast path: non-merge commands exit 0 on a pure string check (no subprocess).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Command-position only: line start or after ; & | ( — a *mention* of
# "gh pr merge" mid-line (e.g. inside a PR-body here-string) must NOT match.
# First live firing of the armed hook was exactly that false positive.
_MERGE_RE = re.compile(
    r"(?:^|[;&|(])\s*gh\s+pr\s+merge\b(?P<rest>[^|;&\n]*)", re.MULTILINE
)
_PR_NUM_RE = re.compile(r"\s(\d+)\b")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _block(msg: str) -> int:
    print(f"[premerge-hook] BLOCKED: {msg}", file=sys.stderr)
    return 2


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def main() -> int:
    # utf-8-sig: PowerShell pipes (and some shells) prepend a BOM that breaks
    # json.loads. Read bytes + decode BOM-tolerantly.
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        if "gh pr merge" in raw:
            # Fail CLOSED when it matters: the input mentions a merge but we
            # cannot verify the tripwire. A silent allow here would be the exact
            # hole this hook exists to close.
            return _block(
                "hook input is unparseable but mentions `gh pr merge` - tripwire "
                "unverifiable; not merging blind. Re-issue as a plain `gh pr merge <N>`."
            )
        return 0  # unparseable and unrelated to merging — do not interfere
    command = str((payload.get("tool_input") or {}).get("command") or "")

    m = _MERGE_RE.search(command)
    if not m:
        return 0  # fast path: not a merge

    # --- resolve PR number ---------------------------------------------------
    num_match = _PR_NUM_RE.search(m.group("rest"))
    if num_match:
        pr = num_match.group(1)
    else:
        head = _run(["gh", "pr", "view", "--json", "number", "--jq", ".number"])
        if head.returncode != 0 or not head.stdout.strip().isdigit():
            return _block(
                "cannot resolve the PR number from the command or the current branch. "
                "Merge with an explicit number: `gh pr merge <N> ...`"
            )
        pr = head.stdout.strip()

    # --- changed files -------------------------------------------------------
    files_proc = _run(["gh", "pr", "view", pr, "--json", "files", "--jq", ".files[].path"])
    if files_proc.returncode != 0:
        return _block(f"cannot list changed files for PR #{pr} (gh exit {files_proc.returncode}). Tripwire unverifiable — not merging blind.")
    files = [ln.strip() for ln in files_proc.stdout.splitlines() if ln.strip()]
    if not files:
        return 0  # empty PR — nothing to trip

    # --- classify ------------------------------------------------------------
    classify = _run(
        ["uv", "run", "--project", "backend", "python",
         "scripts/autonomy/classify_tripwire.py", "--files", *files]
    )
    if classify.returncode == 0:
        return 0  # clean — auto-merge allowed
    if classify.returncode != 10:
        return _block(
            f"tripwire classifier failed (exit {classify.returncode}): "
            f"{(classify.stderr or classify.stdout).strip()[:300]}. Not merging blind."
        )

    # --- tripwire matched: require an approved ack ---------------------------
    ack = _run([sys.executable, "scripts/autonomy/run_queue.py", "check-ack", "--pr", pr])
    if ack.returncode == 0:
        print(f"[premerge-hook] PR #{pr}: tripwire matched, approved ack found - allowing merge.", file=sys.stderr)
        return 0

    categories = ", ".join(
        cat.get("category", "?") for cat in json.loads(classify.stdout).get("categories", [])
    ) if classify.stdout.strip().startswith("{") else "see classifier output"
    return _block(
        f"PR #{pr} matches tripwire categories [{categories}] and has NO approved ack "
        f"(ADR-037 D2). Add a RUN-QUEUE entry (`python scripts/autonomy/run_queue.py add "
        f"--kind ack-needed --pr {pr} ...`), notify the founder, and wait for "
        f"`/autonomy:ack <ID> approved` before merging."
    )


if __name__ == "__main__":
    sys.exit(main())
