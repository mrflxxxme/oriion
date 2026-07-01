#!/usr/bin/env python3
"""Classify a PR diff against the autonomy tripwire (ADR-037 D2).

The autonomous runner calls this BEFORE auto-merging a green phase. If any
changed file matches a tripwire category (DB migrations · auth/RBAC/sessions ·
billing · secrets/keys · public contracts), the phase must NOT auto-merge:
it goes to RUN-QUEUE + notify + wait for founder ``/ack``. No match → auto-merge.

Exit codes:
  0  clean — no tripwire category matched → auto-merge allowed
  10 tripwire matched → pause-and-ack required (NOT an error; a decision signal)
  1  usage / IO error

Reads ``.claude/autonomy/tripwire.yaml``. Needs PyYAML → run via the backend
venv: ``uv run --project backend python scripts/autonomy/classify_tripwire.py``.

Changed files come from (in priority order): ``--files a b c``, or ``--diff-base
<ref>`` (runs ``git diff --name-only <ref>...HEAD``), default base ``origin/main``.
Emits a JSON verdict to stdout for the runner to consume.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG = Path(".claude/autonomy/tripwire.yaml")


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a path glob (with ``**``) to an anchored regex on '/'-paths.

    ``**`` matches across directory separators; ``*`` matches within a segment;
    ``?`` matches a single non-separator char.
    """
    i = 0
    out: list[str] = ["^"]
    n = len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if i + 1 < n and glob[i + 1] == "*":
                # ** → any chars incl '/'. Swallow an optional trailing '/'.
                i += 2
                if i < n and glob[i] == "/":
                    out.append("(?:.*/)?")
                    i += 1
                else:
                    out.append(".*")
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return re.compile("".join(out))


def _changed_files(args: argparse.Namespace) -> list[str]:
    if args.files:
        return [f.strip().replace("\\", "/") for f in args.files if f.strip()]
    base = args.diff_base
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[tripwire] cannot compute git diff against {base}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    return [ln.strip().replace("\\", "/") for ln in out.stdout.splitlines() if ln.strip()]


def classify(files: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return matched categories: [{category, reason, matched_files:[...]}]."""
    matches: list[dict[str, Any]] = []
    for name, spec in (config.get("categories") or {}).items():
        patterns = [_glob_to_regex(g) for g in (spec.get("globs") or [])]
        hit = sorted({f for f in files if any(p.match(f) for p in patterns)})
        if hit:
            matches.append(
                {"category": name, "reason": spec.get("reason", ""), "matched_files": hit}
            )
    return matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(_DEFAULT_CONFIG))
    parser.add_argument("--diff-base", default="origin/main")
    parser.add_argument("--files", nargs="*", default=None, help="Explicit file list (skips git).")
    args = parser.parse_args(argv)

    try:
        import yaml
    except ImportError:
        print("[tripwire] PyYAML required — run via `uv run --project backend python ...`", file=sys.stderr)
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[tripwire] config not found: {config_path}", file=sys.stderr)
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    files = _changed_files(args)
    matches = classify(files, config)
    verdict = {
        "changed_files": len(files),
        "tripwire_matched": bool(matches),
        "decision": "pause-and-ack" if matches else "auto-merge",
        "categories": matches,
    }
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 10 if matches else 0


if __name__ == "__main__":
    sys.exit(main())
