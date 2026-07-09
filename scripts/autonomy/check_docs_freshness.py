#!/usr/bin/env python3
"""ADR-040 D9 — docs-freshness gate.

Cheap guard against the drift the exit-ritual is supposed to prevent: a phase
that has been MERGED but whose own spec-file still says ``Status: Pending`` (or
``In progress``). It reads ``.planning/STATUS.md`` as the source of truth for
which phases are done, and cross-checks each phase spec-file's own ``Status:``.

Merged-detection is deliberately precise to avoid false reds: a phase counts as
"done" only when STATUS.md has a **subject line** of the form
``… Phase <id> [+ <id> …] — … <terminal-marker> …`` (the phase-status paragraphs
and the history-table rows). An incidental "Next → 01.8c" mention on some other
subject's ✅ line does NOT mark 01.8c done.

Terminal markers: ``✅``, ``MERGED``, ``COMPLETE``/``Code-complete``, ``Split``.

Run from the repo root (stdlib only, Python 3.12):

    python scripts/autonomy/check_docs_freshness.py

Exits 0 + OK when fresh; exits 1 + lists each merged-but-Pending phase spec.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_STATUS_REL = Path(".planning/STATUS.md")
_PHASES_GLOB = ".planning/roadmap/*/phases/*.md"

# A phase id: NN.M with an optional single letter and an optional -ui / -mail
# suffix (e.g. 01.6, 01.9a, 01.4-ui, 01.8-mail).
_PHASE_ID_RE = re.compile(r"\b(\d{2}\.\d+[a-z]?(?:-(?:ui|mail))?)\b")


def _ascii(text: str) -> str:
    """ASCII-safe rendering for the Windows cp1251 console (repo convention)."""
    return text.encode("ascii", "replace").decode("ascii")


def _rel(path: Path) -> str:
    """Repo-relative posix path when possible, else the path as given (tmp tests)."""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()

_TERMINAL_TOKENS = ("✅", "MERGED", "COMPLETE", "CODE-COMPLETE", "SPLIT")  # ✅
_NONTERMINAL_TOKENS = ("PENDING", "IN PROGRESS", "\U0001f504")  # 🔄


def merged_phase_ids(status_text: str) -> set[str]:
    """Phase ids that STATUS.md marks done via a subject line + terminal marker.

    A phase is "done" only when it is the SUBJECT of a status line — the clause
    before the first em-dash names it (e.g. "**Phase 01.7 + 01.8-mail + 01.8 — ✅
    MERGED**"). This deliberately ignores incidental post-dash mentions such as
    "… — ✅ Complete. Next → 01.8c", so the next phase is not marked merged.
    """
    merged: set[str] = set()
    for line in status_text.splitlines():
        if not any(tok in line.upper() for tok in _TERMINAL_TOKENS):
            continue
        subject = line.split("—", 1)[0]  # text before the first em-dash
        if "PHASE" not in subject.upper():
            continue
        for pid in _PHASE_ID_RE.findall(subject):
            merged.add(pid)
    return merged


def spec_phase_id(spec_path: Path) -> str | None:
    """Leading phase id of a canonical phase spec filename, or None."""
    m = _PHASE_ID_RE.match(spec_path.name)
    return m.group(1) if m else None


def spec_status_line(spec_path: Path) -> str | None:
    """First ``Status:`` line of a spec file (the header status), or None."""
    for line in spec_path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^[>*\s\-]*\**status:?\**", line, re.IGNORECASE):
            return line
    return None


def is_nonterminal(status_line: str) -> bool:
    upper = status_line.upper()
    if any(tok in upper for tok in _TERMINAL_TOKENS):
        return False
    return any(tok in upper for tok in _NONTERMINAL_TOKENS)


def find_stale(status_text: str, spec_paths: list[Path]) -> list[str]:
    """Return ``"<spec>: merged in STATUS but Status: <x>"`` for each stale spec."""
    merged = merged_phase_ids(status_text)
    stale: list[str] = []
    for spec in spec_paths:
        name = spec.name
        if name.endswith("-PLAN.md") or name.endswith("-VERIFICATION.md"):
            continue
        pid = spec_phase_id(spec)
        if pid is None or pid not in merged:
            continue
        status_line = spec_status_line(spec)
        # No detectable Status line -> can't assert staleness (legacy specs express
        # it differently, incl. Cyrillic "Статус"). Conservative: skip, don't fail.
        if status_line is None:
            continue
        if is_nonterminal(status_line):
            stale.append(f"{_rel(spec)}: merged ({pid}) but spec Status is still non-terminal ('{_ascii(status_line.strip()[:80])}')")
    return stale


def main() -> int:
    status_path = _REPO_ROOT / _STATUS_REL
    if not status_path.is_file():
        print(f"ERROR: STATUS.md not found at {status_path}", file=sys.stderr)
        return 1

    status_text = status_path.read_text(encoding="utf-8")
    spec_paths = sorted(_REPO_ROOT.glob(_PHASES_GLOB))
    stale = find_stale(status_text, spec_paths)

    if stale:
        print("ADR-040 D9 docs-freshness FAILED -- merged phase(s) with a non-terminal spec Status:")
        for line in stale:
            print(f"  {line}")
        print("\nFlip each spec's Status to its terminal state (exit-ritual doc-sync, ADR-040 D9c).")
        return 1

    print(f"OK -- no merged phase left with a Pending/In-progress spec ({len(spec_paths)} specs scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
