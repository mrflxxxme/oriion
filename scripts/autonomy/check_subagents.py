#!/usr/bin/env python3
"""ADR-040 D8 — native-subagent conformance gate.

The 11 persistent roles (ADR-023) are spawnable Claude Code subagents defined by
``.claude/agents/<role>.md`` (frontmatter + a thin body pointing at the role's
handbook under ``.claude/agents/<role>/``). This gate keeps those spawn-entries
honest so the judge-panel / reviewer lenses (ADR-037 D5) spawn real roles:

For every ``.claude/agents/<role>.md`` it asserts:
  1. Parseable YAML-ish frontmatter delimited by ``---`` ... ``---``.
  2. ``name`` equals the file stem (so ``subagent_type=<role>`` resolves).
  3. ``description`` non-empty, ``tools`` non-empty, ``model`` present.
  4. A sibling handbook dir ``.claude/agents/<name>/`` with ``system-prompt.md``
     and ``profile.md`` exists (the single source of truth the body points to).

And the reverse: every role dir with a ``profile.md`` has a spawn-entry file, so a
new role can't silently ship without being spawnable.

Run from the repo root (stdlib only, Python 3.12):

    python scripts/autonomy/check_subagents.py

Exits 0 + prints OK when all entries conform; exits 1 + prints each violation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root = scripts/autonomy/ -> scripts/ -> <root>.
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_AGENTS_DIR_REL = Path(".claude/agents")

_REQUIRED_KEYS = ("name", "description", "tools", "model")


def _rel(path: Path) -> str:
    """Repo-relative posix path when possible, else the path as given (tmp tests)."""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the leading ``---`` frontmatter as a flat str->str map, or None.

    Only simple ``key: value`` scalar lines are parsed (the spawn-entries use no
    nested YAML), which keeps this stdlib-only (no PyYAML dependency in CI).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    # No closing delimiter.
    return None


def check_entry(entry_path: Path, agents_dir: Path) -> list[str]:
    """Return a list of violation strings for one ``<role>.md`` spawn-entry."""
    rel = _rel(entry_path)
    stem = entry_path.stem
    problems: list[str] = []

    fm = parse_frontmatter(entry_path.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{rel}: missing or unterminated '---' frontmatter"]

    for key in _REQUIRED_KEYS:
        if not fm.get(key):
            problems.append(f"{rel}: frontmatter key '{key}' missing or empty")

    name = fm.get("name", "")
    if name and name != stem:
        problems.append(f"{rel}: frontmatter name '{name}' != file stem '{stem}'")

    handbook = agents_dir / stem
    if not (handbook / "system-prompt.md").is_file():
        problems.append(f"{rel}: handbook '{_rel(handbook)}/system-prompt.md' not found")
    if not (handbook / "profile.md").is_file():
        problems.append(f"{rel}: handbook '{_rel(handbook)}/profile.md' not found")

    return problems


def find_violations(agents_dir: Path) -> list[str]:
    """Core gate (pure w.r.t. the given dir): forward + reverse conformance."""
    violations: list[str] = []

    entries = sorted(p for p in agents_dir.glob("*.md"))
    entry_stems = {p.stem for p in entries}
    for entry in entries:
        violations.extend(check_entry(entry, agents_dir))

    # Reverse: a role dir with a profile.md must have a spawn-entry file.
    for role_dir in sorted(p for p in agents_dir.iterdir() if p.is_dir()):
        if role_dir.name == "_shared":
            continue
        if (role_dir / "profile.md").is_file() and role_dir.name not in entry_stems:
            violations.append(
                f"{_rel(role_dir)}/: role handbook has no spawnable '.claude/agents/{role_dir.name}.md' entry (ADR-040 D8)"
            )

    return violations


def main() -> int:
    agents_dir = _REPO_ROOT / _AGENTS_DIR_REL
    if not agents_dir.is_dir():
        print(f"ERROR: agents dir not found at {agents_dir}", file=sys.stderr)
        return 1

    violations = find_violations(agents_dir)
    if violations:
        print("ADR-040 D8 subagent conformance FAILED:")
        for line in violations:
            print(f"  {line}")
        return 1

    count = len(sorted(agents_dir.glob("*.md")))
    print(f"OK -- {count} spawnable subagent entries conform (frontmatter + handbook).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
