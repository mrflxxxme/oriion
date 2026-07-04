#!/usr/bin/env python3
"""Delegating shim for the premerge tripwire hook.

The armed Claude Code PreToolUse hook runs `python scripts/autonomy/premerge_hook.py`
resolved from the Bash tool's *current* working directory. When the cwd is the
repo root the canonical hook (``<root>/scripts/autonomy/premerge_hook.py``) runs.
When the cwd is ``backend/`` the same relative path lands here — so this shim must
exist and delegate to the canonical hook, or every Bash/PowerShell tool call is
bricked (see memory: premerge-hook-cwd-fragility). ``backend/scripts/`` is tracked,
so this file is a legitimate, committed safety net — do NOT ``rm -rf`` it.

Contract is identical to the real hook: stdin JSON in, exit 0 = allow / 2 = block.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    """Walk up until we find the canonical hook under scripts/autonomy/."""
    for parent in [start, *start.parents]:
        if (parent / "scripts" / "autonomy" / "premerge_hook.py").is_file() and parent != start:
            # `parent != start` guards against re-selecting this shim's own dir.
            return parent
        if (parent / ".claude" / "autonomy" / "tripwire.yaml").is_file():
            return parent
    return None


def main() -> int:
    raw = sys.stdin.buffer.read()
    here = Path(__file__).resolve()
    # This shim lives at <root>/backend/scripts/autonomy/premerge_hook.py, so the
    # repo root is three parents up. Fall back to an upward search if the layout
    # ever changes.
    root = here.parents[3] if len(here.parents) >= 4 else None
    canonical = root / "scripts" / "autonomy" / "premerge_hook.py" if root else None
    if not (canonical and canonical.is_file()):
        root = _find_repo_root(here.parent)
        canonical = root / "scripts" / "autonomy" / "premerge_hook.py" if root else None
    if not (canonical and canonical.is_file()):
        # Cannot locate the real hook. Fail OPEN only for non-merge intent: if the
        # payload mentions a merge, block; otherwise allow so tooling isn't bricked.
        if b"gh pr merge" in raw:
            print("[premerge-shim] BLOCKED: cannot locate canonical hook to verify tripwire.", file=sys.stderr)
            return 2
        return 0
    proc = subprocess.run(
        [sys.executable, str(canonical)],
        input=raw,
        cwd=str(canonical.parents[2]),
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
