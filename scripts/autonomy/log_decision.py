#!/usr/bin/env python3
"""Append a uniform entry to the autonomy decisions-log (ADR-037 D4).

Under the autonomous runner the agent OWNS most forks — it decides and records
the decision instead of asking the founder. Uniform logging is what replaces
founder oversight: it is the founder's post-hoc audit trail of "what did the
agent decide, and why". Architectural decisions ALSO get an ADR (pass --adr);
everything else lives only here.

Appends to .planning/_session-context/DECISIONS-LOG.md (created with a header on
first use). Stdlib-only; content is written UTF-8 (rationale may be Russian),
console output is ASCII-only (safe on a Windows cp1251 console).

Example:
  python scripts/autonomy/log_decision.py --phase 01.5 --kind impl \\
    --fork "Yjs doc storage: one row per doc vs event-sourced updates" \\
    --decision "one row per doc (JSONB snapshot + updated_at)" \\
    --rationale "simpler, fits existing repo pattern; event-sourcing not needed pre-Wave-4" \\
    --reversibility reversible
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_LOG = ".planning/_session-context/DECISIONS-LOG.md"
_HEADER = (
    "# Autonomy decisions-log\n\n"
    "> Append-only. Every agent-owned fork the autonomous runner resolved without "
    "asking the founder (ADR-037 D4). The founder's post-hoc audit trail. "
    "Architectural entries also have an ADR (see `ADR-refs`). "
    "Written by `scripts/autonomy/log_decision.py`.\n"
)
_KINDS = ("impl", "arch", "escalated")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_entry(args: argparse.Namespace, ts: str) -> str:
    tag = args.kind + (f" | {args.adr}" if args.adr else "")
    lines = [
        f"### {ts} | phase {args.phase} | {tag}",
        f"- Fork: {args.fork}",
        f"- Decision: {args.decision}",
        f"- Rationale: {args.rationale}",
        f"- Reversibility: {args.reversibility}",
    ]
    if args.session:
        lines.append(f"- Session: {args.session}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--fork", required=True, help="One-line fork description.")
    parser.add_argument("--decision", required=True, help="What was chosen.")
    parser.add_argument("--rationale", required=True, help="Why (vs the rubric).")
    parser.add_argument("--kind", choices=_KINDS, default="impl")
    parser.add_argument("--reversibility", default="reversible")
    parser.add_argument("--adr", default=None, help="ADR ref if architectural, e.g. ADR-038.")
    parser.add_argument("--session", default=None)
    parser.add_argument("--log-path", default=_DEFAULT_LOG)
    parser.add_argument("--timestamp", default=None, help="Override UTC ts (else now).")
    args = parser.parse_args(argv)

    if args.kind == "arch" and not args.adr:
        print("[log_decision] WARN: kind=arch without --adr; architectural decisions should reference an ADR.")

    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = args.timestamp or _now_utc()
    entry = build_entry(args, ts)

    is_new = not log_path.exists()
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        if is_new:
            fh.write(_HEADER)
        fh.write("\n" + entry)

    print(f"[log_decision] appended {args.kind} decision for phase {args.phase} -> {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
