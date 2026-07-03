#!/usr/bin/env python3
"""Provision the funded ``backend/.env`` into the active worktree (ADR-037 preflight).

The autonomous runner works in a fresh git worktree per run. Live goldens need a
funded ``backend/.env`` (DeepSeek/Yandex/Brave keys), but secrets must NEVER be
committed. This helper copies the single **canonical** funded env — kept at the
MAIN worktree's ``backend/.env`` (git-ignored, the one checkout that persists) —
into the active worktree's ``backend/.env`` when it is absent.

Security invariants (all enforced, not assumed):
- The destination MUST be git-ignored. If ``git check-ignore`` does not claim it,
  the copy is REFUSED (exit 3) — better a stuck run than a staged secret.
- An existing destination is never overwritten (idempotent; exit 0).
- Values are NEVER printed — only the key COUNT and provider key NAMES-present.
- Stdlib-only, ASCII console output (Windows cp1251-safe).

Exit codes: 0 = provisioned or already present · 2 = no canonical env configured
(runner treats as "live gates unavailable" stuck-path) · 3 = refused (dest not
ignored / not inside a worktree) · 1 = unexpected error.

Usage (runner preflight, before any live-golden gate):
  python scripts/autonomy/provision_env.py
  python scripts/autonomy/provision_env.py --check   # report only, copy nothing
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

_REL = "backend/.env"


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=cwd
    )


def _active_worktree() -> Path | None:
    proc = _git("rev-parse", "--show-toplevel")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def _main_worktree() -> Path | None:
    """First entry of ``git worktree list`` is the main (non-linked) worktree."""
    proc = _git("worktree", "list", "--porcelain")
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree ") :].strip())
    return None


def _is_git_ignored(path_rel: str, cwd: Path) -> bool:
    # check-ignore exits 0 iff the path is ignored.
    return _git("check-ignore", path_rel, cwd=cwd).returncode == 0


def _key_summary(env_path: Path) -> str:
    """Provider key names present with SET/empty — NEVER the values."""
    providers = ("DEEPSEEK", "YANDEX", "GIGACHAT", "BRAVE", "OPENAI", "ANTHROPIC")
    count = 0
    present: list[str] = []
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.isupper():
            count += 1
        if key.startswith(providers) and val.strip():
            present.append(key)
    return f"{count} keys; funded: {', '.join(sorted(present)) or 'NONE'}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Report status only; copy nothing."
    )
    args = parser.parse_args(argv)

    active = _active_worktree()
    if active is None:
        print("[provision-env] not inside a git worktree", file=sys.stderr)
        return 3

    dest = active / _REL
    if dest.exists():
        print(f"[provision-env] present: {_REL} ({_key_summary(dest)})")
        return 0

    main_wt = _main_worktree()
    if main_wt is None:
        print("[provision-env] cannot resolve the main worktree", file=sys.stderr)
        return 1
    canonical = main_wt / _REL
    if not canonical.exists():
        print(
            f"[provision-env] no canonical funded env at {canonical} - live gates "
            "unavailable (configure it once on the main checkout)",
            file=sys.stderr,
        )
        return 2

    # Security gate: the destination MUST be git-ignored before we write a secret.
    if not _is_git_ignored(_REL, cwd=active):
        print(
            f"[provision-env] REFUSED: {_REL} is not git-ignored in this worktree - "
            "refusing to place a secret where it could be staged",
            file=sys.stderr,
        )
        return 3

    if args.check:
        print(f"[provision-env] would provision {_REL} from {canonical} ({_key_summary(canonical)})")
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(canonical, dest)
    with contextlib.suppress(OSError):  # best-effort perms (no-op on Windows)
        dest.chmod(0o600)
    print(f"[provision-env] provisioned {_REL} ({_key_summary(dest)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
