#!/usr/bin/env python3
"""Verify autonomy gate evidence artifacts against the current commit.

Per ADR-037 D3. A phase that runs local-only gates (live goldens, Docker
integration, adversarial audit) which GitHub CI cannot run MUST commit an
evidence artifact per gate under ``evidence/<gate>.json`` and declare the
required gates in ``evidence/manifest.json``. This script (invoked by the
``ci-evidence`` workflow AND runnable locally) asserts, for every declared
gate: the artifact exists, is fresh (``head_sha`` == the commit under test),
and ``verdict == "PASS"``. Any miss → non-zero exit → merge blocked.

Non-breaking by design: no manifest, or an empty ``required_gates`` list,
means the phase has no local-only gates → exit 0.

Stdlib-only so CI can run it as bare ``python scripts/autonomy/verify_evidence.py``
without a virtualenv.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_FIELDS = ("schema_version", "gate", "head_sha", "timestamp", "verdict")


def _git_head_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout.strip() or None


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _validate_evidence(payload: Any, gate: str, expected_sha: str) -> list[str]:
    """Return a list of human-readable problems (empty == the gate passes)."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return [f"evidence for '{gate}' is not a JSON object"]

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            problems.append(f"missing required field '{field}'")
    if problems:
        return problems

    if payload["schema_version"] != SCHEMA_VERSION:
        problems.append(
            f"schema_version {payload['schema_version']!r} != {SCHEMA_VERSION}"
        )
    if payload["gate"] != gate:
        problems.append(
            f"gate field {payload['gate']!r} != declared gate {gate!r}"
        )
    head_sha = str(payload["head_sha"])
    if not _SHA_RE.match(head_sha):
        problems.append(f"head_sha {head_sha!r} is not a 40-char sha")
    elif head_sha != expected_sha:
        problems.append(
            f"STALE: evidence head_sha {head_sha[:12]} != commit under test "
            f"{expected_sha[:12]} -gate did not run against this code"
        )
    if payload["verdict"] != "PASS":
        problems.append(f"verdict is {payload['verdict']!r}, not PASS")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="evidence/manifest.json")
    parser.add_argument("--evidence-dir", default="evidence")
    parser.add_argument(
        "--head-sha",
        default=None,
        help="Commit the gates must have run against. Defaults to `git rev-parse HEAD`.",
    )
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"[ci-evidence] no manifest at {manifest_path} -no local-only gates to verify. OK.")
        return 0

    try:
        manifest = _load_json(manifest_path)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[ci-evidence] FAIL: cannot read manifest {manifest_path}: {exc}")
        return 1

    required = manifest.get("required_gates", []) if isinstance(manifest, dict) else None
    if not isinstance(required, list):
        print("[ci-evidence] FAIL: manifest.required_gates must be a list")
        return 1
    if not required:
        print("[ci-evidence] manifest declares no required gates. OK.")
        return 0

    expected_sha = args.head_sha or _git_head_sha()
    if not expected_sha or not _SHA_RE.match(expected_sha):
        print(
            "[ci-evidence] FAIL: could not resolve the commit-under-test sha "
            "(pass --head-sha or run inside a git repo)"
        )
        return 1

    evidence_dir = Path(args.evidence_dir)
    failures = 0
    print(f"[ci-evidence] verifying {len(required)} gate(s) against {expected_sha[:12]}")
    for gate in required:
        ev_path = evidence_dir / f"{gate}.json"
        if not ev_path.exists():
            print(f"  [MISS] {gate}: no evidence artifact at {ev_path}")
            failures += 1
            continue
        try:
            payload = _load_json(ev_path)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [FAIL] {gate}: cannot read {ev_path}: {exc}")
            failures += 1
            continue
        problems = _validate_evidence(payload, gate, expected_sha)
        if problems:
            failures += 1
            for problem in problems:
                print(f"  [FAIL] {gate}: {problem}")
        else:
            cost = payload.get("cost_usd")
            cost_str = f" (${cost})" if cost is not None else ""
            print(f"  [OK]   {gate}: PASS{cost_str}")

    if failures:
        print(f"[ci-evidence] FAIL: {failures} gate(s) missing/stale/failed -merge blocked.")
        return 1
    print("[ci-evidence] all declared gates verified fresh + PASS. OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
