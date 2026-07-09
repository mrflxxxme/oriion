#!/usr/bin/env python3
"""ADR-040 D2 — OpenAPI snapshot export + drift check.

The guarded public API contract is the **generated** snapshot of the live FastAPI
schema, not the hand-written ``.planning/contracts/<ctx>/api.yaml`` drafts. This
script exports ``src.main:app.openapi()`` to
``.planning/contracts/openapi.snapshot.json`` in a deterministic, sorted form so a
``git diff`` is meaningful. CI runs ``--check``: it regenerates the schema and
compares it byte-for-byte against the committed snapshot — any difference (a route
added/removed/changed, a schema field renamed) fails the job. A breaking change
therefore surfaces as both a red CI check and a ``public_api_contracts`` tripwire
signal (the snapshot lives under ``.planning/contracts/**``).

Importing ``src.main`` is import-only (no lifespan / DB) — ``app.openapi()`` walks
the registered routes and Pydantic models. Run under the backend venv:

    # write / refresh the snapshot (from repo root):
    uv run --project backend python scripts/autonomy/export_openapi.py

    # CI drift check (non-zero on drift):
    uv run --project backend python scripts/autonomy/export_openapi.py --check
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_SNAPSHOT_REL = Path(".planning/contracts/openapi.snapshot.json")


def canonical_json(spec: dict[str, Any]) -> str:
    """Deterministic serialization: sorted keys, 2-space indent, trailing NL."""
    return json.dumps(spec, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def build_live_spec() -> dict[str, Any]:
    """Import the FastAPI app and return its OpenAPI schema.

    Deferred import so the rest of the module (and its unit tests of the pure diff
    helpers) never pays the backend-import cost.
    """
    from src.main import app  # deferred import: keep the backend-import cost off unit tests

    return app.openapi()


def diff_text(committed: str, live: str) -> str:
    """Unified diff committed→live (empty string when identical)."""
    if committed == live:
        return ""
    return "".join(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            live.splitlines(keepends=True),
            fromfile="committed openapi.snapshot.json",
            tofile="live app.openapi()",
        )
    )


def write_snapshot(snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(canonical_json(build_live_spec()), encoding="utf-8")


def check_snapshot(snapshot_path: Path) -> tuple[bool, str]:
    """Return (is_fresh, diff). Not-fresh when the file is missing or drifted."""
    live = canonical_json(build_live_spec())
    if not snapshot_path.is_file():
        try:
            shown = snapshot_path.resolve().relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            shown = snapshot_path.as_posix()
        return False, f"snapshot missing at {shown}"
    committed = snapshot_path.read_text(encoding="utf-8")
    return (committed == live), diff_text(committed, live)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or drift-check the OpenAPI snapshot (ADR-040 D2).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare live schema to the committed snapshot; non-zero on drift (CI mode).",
    )
    args = parser.parse_args(argv)
    snapshot_path = _REPO_ROOT / _SNAPSHOT_REL

    if not args.check:
        write_snapshot(snapshot_path)
        print(f"OK -- wrote {_SNAPSHOT_REL.as_posix()}")
        return 0

    fresh, diff = check_snapshot(snapshot_path)
    if fresh:
        print(f"OK -- {_SNAPSHOT_REL.as_posix()} matches the live FastAPI schema.")
        return 0
    print("OpenAPI snapshot DRIFT — the live schema differs from the committed snapshot (ADR-040 D2):")
    print(diff or "  (snapshot file missing)")
    print(
        "\nRegenerate with: uv run --project backend python scripts/autonomy/export_openapi.py\n"
        "A breaking API change also raises the public_api_contracts tripwire — expected."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
