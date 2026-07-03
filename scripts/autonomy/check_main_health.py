#!/usr/bin/env python3
"""Main-branch health verdict + offender attribution (ADR-037 D7, Block D).

The autonomous runner auto-merges; a merged phase can redden `main` later (the
next phase's CI, a re-run). This script gives the runner a deterministic
verdict: per workflow, take the LATEST completed run on main - any failure
means main is unhealthy, and the failing run's head_sha IS the offending
(squash-)merge commit to revert.

Exit codes: 0 = healthy · 20 = unhealthy (failures listed in the JSON verdict)
· 1 = cannot determine (gh error / no data) - treat as "do not merge further".

Reads runs via `gh run list --branch main` (needs gh auth) or from a fixture
file (--runs-json) for tests. Stdout = one JSON verdict object (UTF-8-safe,
ASCII console messages on stderr).

Usage:
  python scripts/autonomy/check_main_health.py
  python scripts/autonomy/check_main_health.py --runs-json fixture.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
# Workflows that gate merges (deploy-staging is push-triggered ops, not a gate).
_GATE_WORKFLOWS = ("ci-backend", "ci-frontend", "ci-security", "ci-evidence")
_FIELDS = "conclusion,headSha,workflowName,status,createdAt,url,databaseId"


def _fetch_runs(limit: int) -> list[dict[str, Any]] | None:
    proc = subprocess.run(
        ["gh", "run", "list", "--branch", "main", "--limit", str(limit), "--json", _FIELDS],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        print(f"[main-health] gh run list failed: {proc.stderr.strip()[:200]}", file=sys.stderr)
        return None
    try:
        runs = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("[main-health] gh returned unparseable JSON", file=sys.stderr)
        return None
    return runs if isinstance(runs, list) else None


def _workflow_has_push_trigger(text: str) -> bool:
    """Crude-but-safe YAML probe: does the workflow's ``on:`` include push?"""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if line.startswith(("on:", '"on":', "'on':")):
            # Inline form: on: [push, pull_request] / on: push
            _, _, inline = stripped.partition(":")
            if "push" in inline:
                return True
            # Block form: scan the indented mapping under on:
            for sub in lines[idx + 1 :]:
                if sub.strip() and not sub.startswith((" ", "\t")):
                    break  # next top-level key
                if sub.strip().startswith("push:"):
                    return True
            return False
    return False


def push_triggered_gate_workflows() -> set[str] | None:
    """Names of gate workflows that run on push to main, per origin/main's tree.

    A workflow that no longer triggers on push (e.g. ci-evidence is a PR-only
    merge gate) cannot testify about main's health - its stale last main-run
    would otherwise pin the verdict to a failure forever. None = cannot
    determine (git error) -> caller keeps the conservative old behavior.
    """
    proc = subprocess.run(
        ["git", "ls-tree", "--name-only", "origin/main", ".github/workflows/"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        return None
    names: set[str] = set()
    for path in proc.stdout.split():
        show = subprocess.run(
            ["git", "show", f"origin/main:{path}"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        if show.returncode != 0:
            return None
        text = show.stdout
        wf_name = next(
            (
                line.partition(":")[2].strip().strip("\"'")
                for line in text.splitlines()
                if line.startswith("name:")
            ),
            path.rsplit("/", 1)[-1],
        )
        if _workflow_has_push_trigger(text):
            names.add(wf_name)
    return names


def evaluate(
    runs: list[dict[str, Any]], push_workflows: set[str] | None = None
) -> dict[str, Any]:
    """Latest COMPLETED run per gate workflow -> verdict. Runs must be newest-first."""
    latest: dict[str, dict[str, Any]] = {}
    last_green_sha: str | None = None
    for run in runs:
        name = str(run.get("workflowName") or "")
        if not any(name.startswith(gate) for gate in _GATE_WORKFLOWS):
            continue
        if run.get("status") != "completed":
            continue  # in-progress runs are not evidence either way
        if name not in latest:
            latest[name] = run
        # earliest-seen success = most recent green anywhere in the window
        if last_green_sha is None and run.get("conclusion") == "success":
            last_green_sha = run.get("headSha")

    ignored_pr_only = sorted(
        name
        for name, run in latest.items()
        if run.get("conclusion") != "success"
        and push_workflows is not None
        and name not in push_workflows
    )
    failures = [
        {
            "workflow": name,
            "conclusion": run.get("conclusion"),
            "offender_sha": run.get("headSha"),
            "url": run.get("url"),
            "run_id": run.get("databaseId"),
        }
        for name, run in sorted(latest.items())
        if run.get("conclusion") != "success" and name not in ignored_pr_only
    ]
    return {
        "healthy": not failures,
        "workflows_seen": sorted(latest),
        "failures": failures,
        "ignored_pr_only": ignored_pr_only,
        "last_green_sha": last_green_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="How many recent runs to inspect.")
    parser.add_argument("--runs-json", default=None, help="Fixture file instead of gh (tests).")
    args = parser.parse_args(argv)

    if args.runs_json:
        try:
            runs = json.loads(Path(args.runs_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[main-health] cannot read fixture: {exc}", file=sys.stderr)
            return 1
        push_workflows: set[str] | None = None  # fixtures: keep pure old behavior
    else:
        runs = _fetch_runs(args.limit)
        if runs is None:
            return 1
        push_workflows = push_triggered_gate_workflows()

    verdict = evaluate(runs, push_workflows)
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    if not verdict["workflows_seen"]:
        print("[main-health] no completed gate-workflow runs found - cannot judge", file=sys.stderr)
        return 1
    if verdict["healthy"]:
        print("[main-health] main is HEALTHY", file=sys.stderr)
        return 0
    print(
        f"[main-health] main is UNHEALTHY: {len(verdict['failures'])} failing workflow(s); "
        f"offender sha(s): {', '.join(sorted({str(f['offender_sha'])[:12] for f in verdict['failures']}))}",
        file=sys.stderr,
    )
    return 20


if __name__ == "__main__":
    sys.exit(main())
