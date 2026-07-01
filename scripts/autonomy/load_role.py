#!/usr/bin/env python3
"""Compose a spawnable prompt for an Oriion AI-team role (ADR-037 Block C).

Closes the ADR-023 design-vs-reality gap: the 11 role dirs under
`.claude/agents/<role>/` are handbooks (profile / system-prompt / workflows /
tools-allowlist), NOT native Claude Code subagents. The autonomous runner
composes a role's spawn-prompt with this script and passes it to a
general-purpose `Task` spawn — so the pipeline can actually delegate to
planner / implementers / reviewers / verifier / evaluator without converting
the handbooks.

Output (stdout, UTF-8): system-prompt.md (the actual spawn prompt) +
tools-allowlist.md (enforced scope, ADR §7) + optional workflows.md and a
checklist. Keep the default lean — workflows/checklists are JIT context.

Examples:
  python scripts/autonomy/load_role.py --role backend-implementer
  python scripts/autonomy/load_role.py --role verifier --with-workflows
  python scripts/autonomy/load_role.py --role reviewer-backend --checklist pr-review-backend
  python scripts/autonomy/load_role.py --list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_AGENTS_DIR = ".claude/agents"
_NON_ROLE_DIRS = {"_shared"}


def _repo_root() -> Path:
    # scripts/autonomy/load_role.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def _roles(agents_dir: Path) -> list[str]:
    return sorted(
        p.name
        for p in agents_dir.iterdir()
        if p.is_dir() and p.name not in _NON_ROLE_DIRS and (p / "system-prompt.md").exists()
    )


def _section(title: str, body: str) -> str:
    return f"\n\n<!-- ==== {title} ==== -->\n\n{body.strip()}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", default=None)
    parser.add_argument("--agents-dir", default=None, help="Defaults to <repo>/.claude/agents.")
    parser.add_argument("--with-workflows", action="store_true", help="Append workflows.md.")
    parser.add_argument("--checklist", default=None, help="Checklist name (без .md) из checklists/.")
    parser.add_argument("--list", action="store_true", help="List available roles and exit.")
    args = parser.parse_args(argv)

    # The composed prompt contains non-cp1251 glyphs (arrows etc.) — force UTF-8
    # stdout so a Windows cp1251 console doesn't UnicodeEncodeError.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    agents_dir = Path(args.agents_dir) if args.agents_dir else _repo_root() / _AGENTS_DIR
    if not agents_dir.is_dir():
        print(f"[load_role] agents dir not found: {agents_dir}", file=sys.stderr)
        return 1

    if args.list:
        for role in _roles(agents_dir):
            print(role)
        return 0

    if not args.role:
        print("[load_role] --role is required (or --list)", file=sys.stderr)
        return 1

    role_dir = agents_dir / args.role
    system_prompt = role_dir / "system-prompt.md"
    if not system_prompt.exists():
        print(
            f"[load_role] unknown role '{args.role}' (no {system_prompt}). "
            f"Available: {', '.join(_roles(agents_dir))}",
            file=sys.stderr,
        )
        return 1

    parts: list[str] = [
        f"<!-- Oriion role spawn-prompt: {args.role} (composed by scripts/autonomy/load_role.py; "
        "sources: .claude/agents/{role}/ per ADR-023 §4) -->",
        _section("SYSTEM PROMPT", system_prompt.read_text(encoding="utf-8")),
    ]

    allowlist = role_dir / "tools-allowlist.md"
    if allowlist.exists():
        parts.append(_section("TOOLS ALLOWLIST (enforced — AGENTS.md global rule 7)", allowlist.read_text(encoding="utf-8")))

    if args.with_workflows:
        workflows = role_dir / "workflows.md"
        if workflows.exists():
            parts.append(_section("WORKFLOWS", workflows.read_text(encoding="utf-8")))
        else:
            print(f"[load_role] note: {args.role} has no workflows.md", file=sys.stderr)

    if args.checklist:
        checklist = role_dir / "checklists" / f"{args.checklist}.md"
        if not checklist.exists():
            available = sorted(p.stem for p in (role_dir / "checklists").glob("*.md"))
            print(
                f"[load_role] checklist '{args.checklist}' not found for {args.role}. "
                f"Available: {', '.join(available) or '(none)'}",
                file=sys.stderr,
            )
            return 1
        parts.append(_section(f"CHECKLIST: {args.checklist}", checklist.read_text(encoding="utf-8")))

    print("".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
