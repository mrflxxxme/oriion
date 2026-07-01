#!/usr/bin/env python3
"""RUN-QUEUE — the autonomous runner's founder-facing interrupt queue (ADR-037 D8).

Every interrupt event the runner produces (ack-needed | escalation | revert |
stuck | complete) is appended here so the founder always has ONE place to see
"what is waiting for me / what happened while I was away". `/autonomy:ack`
resolves entries; the pre-merge tripwire hook consults `check-ack` before
allowing a tripwire-matched merge.

File: .planning/_session-context/RUN-QUEUE.md (markdown, machine-parseable
header lines). Stdlib-only; ASCII console output (Windows cp1251-safe);
file body UTF-8 (summaries may be Russian).

Commands:
  add        --kind K --phase P [--pr N] --summary S [--details ...] -> prints new ID
  resolve    ID --verdict approved|rejected [--note ...]
  check-ack  --pr N   (exit 0 = approved ack exists for this PR; 3 = not acked)
  pending    (list pending entries; exit 0 always)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_QUEUE = ".planning/_session-context/RUN-QUEUE.md"
_KINDS = ("ack-needed", "escalation", "revert", "stuck", "complete")
_HEADER = (
    "# RUN-QUEUE — autonomous runner interrupt queue\n\n"
    "> Append-only log of runner interrupt events (ADR-037 D8): ack-needed / "
    "escalation / revert / stuck / complete. Pending entries are waiting for the "
    "founder; resolve with `/autonomy:ack <ID> <verdict>`. Written by "
    "`scripts/autonomy/run_queue.py`.\n"
)
# ### RQ-20260702-001 | ack-needed | pr:76 | phase:01.5 | 2026-07-02T10:00:00Z | status:pending
_ENTRY_RE = re.compile(
    r"^### (?P<id>RQ-\d{8}-\d{3}) \| (?P<kind>[a-z-]+) \| pr:(?P<pr>[^ ]+) \| "
    r"phase:(?P<phase>[^ ]+) \| (?P<ts>[^ ]+) \| status:(?P<status>\w+)(?P<rest>.*)$"
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _next_id(lines: list[str], date_part: str) -> str:
    prefix = f"RQ-{date_part}-"
    seqs = [
        int(m.group("id").rsplit("-", 1)[1])
        for line in lines
        if (m := _ENTRY_RE.match(line)) and m.group("id").startswith(prefix)
    ]
    return f"{prefix}{(max(seqs) + 1) if seqs else 1:03d}"


def cmd_add(args: argparse.Namespace) -> int:
    path = Path(args.queue_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = _read_lines(path)
    ts = args.timestamp or _now_utc()
    entry_id = args.id or _next_id(lines, ts[:10].replace("-", ""))
    pr = args.pr if args.pr is not None else "-"

    block = [
        f"### {entry_id} | {args.kind} | pr:{pr} | phase:{args.phase} | {ts} | status:pending",
        f"- Summary: {args.summary}",
    ]
    for detail in args.details or []:
        block.append(f"- {detail}")
    if args.kind in ("ack-needed", "escalation"):
        block.append(f"- Resolve: `/autonomy:ack {entry_id} approved|rejected`")

    is_new = not lines
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        if is_new:
            fh.write(_HEADER)
        fh.write("\n" + "\n".join(block) + "\n")
    print(entry_id)
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    path = Path(args.queue_path)
    lines = _read_lines(path)
    ts = args.timestamp or _now_utc()
    hit = False
    for i, line in enumerate(lines):
        m = _ENTRY_RE.match(line)
        if m and m.group("id") == args.id:
            if m.group("status") != "pending":
                print(f"[run-queue] {args.id} is already status:{m.group('status')}")
                return 4
            lines[i] = (
                line.replace("status:pending", "status:resolved")
                + f" | resolved:{ts} | verdict:{args.verdict}"
            )
            if args.note:
                lines.insert(i + 1, f"- Resolution note: {args.note}")
            hit = True
            break
    if not hit:
        print(f"[run-queue] no pending entry with id {args.id}")
        return 4
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"[run-queue] {args.id} resolved: {args.verdict}")
    return 0


def cmd_check_ack(args: argparse.Namespace) -> int:
    for line in _read_lines(Path(args.queue_path)):
        m = _ENTRY_RE.match(line)
        if (
            m
            and m.group("kind") == "ack-needed"
            and m.group("pr") == str(args.pr)
            and m.group("status") == "resolved"
            and "verdict:approved" in m.group("rest")
        ):
            print(f"[run-queue] pr:{args.pr} ACK approved ({m.group('id')})")
            return 0
    print(f"[run-queue] pr:{args.pr} has NO approved ack")
    return 3


def cmd_pending(args: argparse.Namespace) -> int:
    found = 0
    for line in _read_lines(Path(args.queue_path)):
        m = _ENTRY_RE.match(line)
        if m and m.group("status") == "pending":
            found += 1
            print(f"{m.group('id')} | {m.group('kind')} | pr:{m.group('pr')} | phase:{m.group('phase')} | {m.group('ts')}")
    if not found:
        print("[run-queue] no pending entries")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-path", default=_DEFAULT_QUEUE)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--kind", choices=_KINDS, required=True)
    p_add.add_argument("--phase", required=True)
    p_add.add_argument("--pr", default=None)
    p_add.add_argument("--summary", required=True)
    p_add.add_argument("--details", nargs="*", default=None)
    p_add.add_argument("--id", default=None, help="Override auto ID (tests).")
    p_add.add_argument("--timestamp", default=None)

    p_res = sub.add_parser("resolve")
    p_res.add_argument("id")
    p_res.add_argument("--verdict", choices=("approved", "rejected"), required=True)
    p_res.add_argument("--note", default=None)
    p_res.add_argument("--timestamp", default=None)

    p_chk = sub.add_parser("check-ack")
    p_chk.add_argument("--pr", required=True)

    sub.add_parser("pending")

    args = parser.parse_args(argv)
    # argparse fills queue_path on the top-level namespace for all subcommands.
    return {"add": cmd_add, "resolve": cmd_resolve, "check-ack": cmd_check_ack, "pending": cmd_pending}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
