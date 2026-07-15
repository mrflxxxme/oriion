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

SCHEMA_VERSION = 2
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# Covers every AC notation in canon: AC-02.1.3 (phase), AC-W1-4 / AC-W1-11 (wave), AC-3.6 (01.2).
_AC_ID_RE = re.compile(r"^AC-[A-Za-z0-9]+([.-][A-Za-z0-9]+)*$")
_REQUIRED_FIELDS = ("schema_version", "gate", "head_sha", "timestamp", "verdict", "ac_ids")


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


def _commit_files(sha: str) -> list[str] | None:
    """Paths touched by ``sha`` (vs its first parent). None on git failure."""
    try:
        out = subprocess.run(
            ["git", "show", "--name-only", "--format=", "--first-parent", sha],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _last_non_evidence_commit(start_sha: str, evidence_dir: str) -> str:
    """Walk first-parent past commits that touch ONLY ``evidence_dir``.

    Resolves the head_sha chicken-and-egg: the evidence artifact records the
    commit the gate ran against, but COMMITTING the artifact advances the tip,
    so a literal ``head_sha == tip`` can never hold (the commit hash cannot
    appear inside its own tree). Freshness therefore means: no commit AFTER
    the gate ran touches anything outside ``evidence_dir``. The teeth are
    preserved — one code/docs path in a later commit stops the walk and the
    evidence is stale again.
    """
    prefix = evidence_dir.rstrip("/\\") + "/"
    sha = start_sha
    # Bound the walk: a legitimate tail is 1-2 evidence-only commits.
    for _ in range(5):
        files = _commit_files(sha)
        if not files or not all(f.startswith(prefix) for f in files):
            return sha
        try:
            out = subprocess.run(
                ["git", "rev-parse", f"{sha}^"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return sha
        parent = out.stdout.strip()
        if not _SHA_RE.match(parent):
            return sha
        sha = parent
    return sha


def _changed_files(base_ref: str) -> set[str] | None:
    """Repo-relative paths this PR changes vs ``base_ref`` (three-dot diff).

    Three-dot (``base...HEAD``) diffs HEAD against the merge-base, i.e. exactly
    the PR's own commits — so evidence left on the base branch by a PRIOR squash
    (inherited unchanged into this PR) does NOT appear here. Returns None on any
    git failure so the caller can fail-closed (verify all, never silently skip).
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return {ln.strip().replace("\\", "/") for ln in out.stdout.splitlines() if ln.strip()}


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
    problems.extend(_validate_ac_ids(payload.get("ac_ids"), gate))
    return problems


def _validate_ac_ids(ac_ids: Any, gate: str) -> list[str]:
    """Per D-34: an artifact must name the claims it discharges, not just its gate.

    A green gate is not proof that a given AC was tested — v1 bound evidence to
    the gate alone, which is how AC-W1-4 reached main as dead code (unit-green,
    CI-green, nothing calling it).
    """
    if not isinstance(ac_ids, list) or not ac_ids:
        return ["ac_ids must be a non-empty list of AC ids this artifact discharges (D-34)"]
    problems = [
        f"ac_ids entry {ac!r} is not a valid AC id (expected e.g. AC-02.6.3)"
        for ac in ac_ids
        if not (isinstance(ac, str) and _AC_ID_RE.match(ac))
    ]
    if len(set(ac_ids)) != len(ac_ids):
        problems.append(f"ac_ids for '{gate}' contains duplicates")
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
    parser.add_argument(
        "--base-ref",
        default=None,
        help=(
            "Base ref (e.g. origin/main / the PR base sha) to scope verification "
            "to gates THIS PR adds or modifies. When set, a required gate whose "
            "evidence file the PR does not touch — and whose manifest is unchanged "
            "vs the base — is skipped as inherited, so a PR that merely inherits "
            "evidence left on main by a prior squash is not failed for its "
            "staleness. A PR that changes the manifest re-verifies ALL gates (must "
            "ship fresh evidence). Omit for verify-all (backward-compatible)."
        ),
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

    resolved_sha = _last_non_evidence_commit(expected_sha, args.evidence_dir)
    if resolved_sha != expected_sha:
        print(
            f"[ci-evidence] tip {expected_sha[:12]} is an evidence-only tail; "
            f"gates must have run against {resolved_sha[:12]} (last non-evidence commit)"
        )
        expected_sha = resolved_sha

    evidence_dir = Path(args.evidence_dir)
    # PR-scoping — fixes evidence inherited from a prior squash. With a base ref,
    # only verify gates THIS PR introduces: its own evidence file changed, or the
    # manifest changed (editing the manifest re-declares the whole gate set → all
    # must ship fresh evidence). A PR that merely inherits evidence left on main by
    # an earlier squash touches neither → the gate is skipped, not failed for
    # staleness. `changed is None` (no base ref, or git failed) → fail-closed:
    # verify everything, never silently skip a real gate.
    ev_prefix = args.evidence_dir.rstrip("/\\")
    changed = _changed_files(args.base_ref) if args.base_ref else None
    manifest_touched = changed is not None and f"{ev_prefix}/manifest.json" in changed

    failures = 0
    skipped = 0
    print(f"[ci-evidence] verifying {len(required)} gate(s) against {expected_sha[:12]}")
    for gate in required:
        if changed is not None and not manifest_touched and f"{ev_prefix}/{gate}.json" not in changed:
            print(f"  [SKIP] {gate}: inherited from {args.base_ref} (evidence not modified by this PR)")
            skipped += 1
            continue
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
            kind = payload.get("kind")
            kind_str = f" [{kind}]" if kind else ""
            acs = ", ".join(payload["ac_ids"])
            print(f"  [OK]   {gate}: PASS{kind_str}{cost_str} -> {acs}")

    if failures:
        print(f"[ci-evidence] FAIL: {failures} gate(s) missing/stale/failed -merge blocked.")
        return 1
    if skipped and skipped == len(required):
        print(
            "[ci-evidence] all declared gates inherited-unchanged from base "
            "(none introduced by this PR). OK."
        )
        return 0
    print("[ci-evidence] all declared gates verified fresh + PASS. OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
