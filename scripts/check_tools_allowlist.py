#!/usr/bin/env python3
"""ADR-028 P-AUDIT-3 — tools-allowlist → registry conformance gate.

Every tool slug referenced by a role/agent ``tools_allowed:`` allowlist MUST
exist in the canonical registry ``.planning/tools/registry.md``. An unknown slug
blocks merge (exit 1).

Canonical home of the policy:
- ``.planning/decisions/ADR-028-policies-registry.md`` §P-AUDIT-3
- ``.planning/tools/registry.md`` — the single source of truth for slugs

Allowlist sources (the parseable, slug-based form):
- ``.planning/verticals/<slug>/prompts/<role>.md`` — YAML frontmatter with a
  ``tools_allowed:`` list of registry slugs.

NOTE on ``.claude/agents/<role>/tools-allowlist.md``: ADR-028 also names these as
allowlists, but they are authored as prose markdown tables keyed by descriptive
bold tool names (``**Read**``, ``**Bash (write/mutate)**``, …) rather than a
machine-parseable list of registry slugs. They are intentionally NOT scoped here
to avoid false positives; the registry's slug-based contract is enforced against
the vertical-prompt frontmatter, which is the form that uses registry slugs.

Run from the repo root (stdlib only, Python 3.12):

    python scripts/check_tools_allowlist.py

Exits 0 and prints ``OK`` when every referenced slug is known; exits 1 and prints
each offending ``<file>: <slug>`` when one or more unknown slugs are found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Repo root = parent of this script's directory (``scripts/``).
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# Canonical registry, relative to repo root.
_REGISTRY_REL = Path(".planning/tools/registry.md")

# Glob (relative to repo root) for the slug-based allowlist sources.
_ALLOWLIST_GLOB = ".planning/verticals/*/prompts/*.md"

# Registry slugs appear as the first column of a markdown table wrapped in
# backticks, e.g. ``| `memory.cells_search` | … |`` for namespaced slugs, and
# ``| `Read` | … |`` for the built-in PascalCase tools. Capture the backticked
# token at the start of a table row.
_REGISTRY_SLUG_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|")

# A bullet item inside the ``tools_allowed:`` YAML block, e.g. ``  - tasks.create``
# (optionally trailed by an inline ``# comment``).
_ALLOWLIST_ITEM_RE = re.compile(r"^\s*-\s+([^\s#]+)\s*(?:#.*)?$")


def load_registry_slugs(registry_path: Path) -> set[str]:
    """Return the canonical set of tool slugs declared in the registry."""
    text = registry_path.read_text(encoding="utf-8")
    slugs: set[str] = set()
    for line in text.splitlines():
        match = _REGISTRY_SLUG_RE.match(line)
        if match is None:
            continue
        token = match.group(1).strip()
        # Skip the table header separator row and the column header ``Slug``.
        if token.lower() == "slug" or set(token) <= {"-", ":", " "}:
            continue
        slugs.add(token)
    return slugs


def extract_allowlist_slugs(allowlist_path: Path) -> list[str]:
    """Return slugs referenced in a file's ``tools_allowed:`` frontmatter block.

    Only the contiguous YAML list immediately following ``tools_allowed:`` is
    parsed. The block ends at the next non-list, non-comment, non-blank line
    (e.g. another frontmatter key or the closing ``---``).
    """
    text = allowlist_path.read_text(encoding="utf-8")
    slugs: list[str] = []
    in_block = False
    for raw in text.splitlines():
        if not in_block:
            # Enter the block at the YAML key line ``tools_allowed:`` (allowing
            # leading indentation). The key name — not arbitrary trailing text —
            # must be ``tools_allowed``.
            key = raw.split(":", 1)[0].strip()
            if key == "tools_allowed" and raw.rstrip().endswith(":"):
                in_block = True
            continue
        stripped = raw.strip()
        if stripped == "" or stripped.startswith("#"):
            # Blank lines and pure-comment lines stay inside the block.
            continue
        item = _ALLOWLIST_ITEM_RE.match(raw)
        if item is None:
            # First non-list line ends the block (next key or ``---``).
            break
        slugs.append(item.group(1).strip())
    return slugs


def find_unknown_slugs(registry_path: Path, allowlist_paths: list[Path]) -> list[str]:
    """Core gate: return ``"<file>: <slug>"`` for each slug missing from registry.

    Pure function — takes explicit paths so tests can drive it directly. Paths
    are reported relative to the repo root when possible, else as given.
    """
    known = load_registry_slugs(registry_path)
    violations: list[str] = []
    for path in allowlist_paths:
        try:
            display = path.resolve().relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            display = path.as_posix()
        for slug in extract_allowlist_slugs(path):
            if slug not in known:
                violations.append(f"{display}: {slug}")
    return violations


def _collect_allowlist_paths(repo_root: Path) -> list[Path]:
    """Discover all slug-based allowlist source files under the repo root."""
    return sorted(repo_root.glob(_ALLOWLIST_GLOB))


def main() -> int:
    registry_path = _REPO_ROOT / _REGISTRY_REL
    if not registry_path.is_file():
        print(f"ERROR: registry not found at {registry_path}", file=sys.stderr)
        return 1

    allowlist_paths = _collect_allowlist_paths(_REPO_ROOT)
    violations = find_unknown_slugs(registry_path, allowlist_paths)

    if violations:
        print("ADR-028 P-AUDIT-3 conformance FAILED — unknown tool slugs:")
        for line in violations:
            print(f"  {line}")
        print(
            f"\nEach slug above must exist in {_REGISTRY_REL.as_posix()} "
            "or be added there via the registry-update PR process."
        )
        return 1

    checked = len(allowlist_paths)
    print(f"OK -- all tool slugs across {checked} allowlist file(s) exist in the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
