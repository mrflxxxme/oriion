"""check_main_health.py — PR-only workflows must not pin main unhealthy.

After ci-evidence became a PR-only merge gate, its last main-branch run is a
stale failure forever (it never runs on push again). The health verdict must
ignore failing testimony from workflows that no longer trigger on push, while
still counting them when they do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "check_main_health.py"

_spec = importlib.util.spec_from_file_location("check_main_health", SCRIPT)
assert _spec is not None and _spec.loader is not None
check_main_health = importlib.util.module_from_spec(_spec)
sys.modules["check_main_health"] = check_main_health
_spec.loader.exec_module(check_main_health)

RUNS = [
    {
        "workflowName": "ci-security",
        "status": "completed",
        "conclusion": "success",
        "headSha": "b" * 40,
    },
    {
        "workflowName": "ci-evidence",
        "status": "completed",
        "conclusion": "failure",
        "headSha": "a" * 40,
    },
]


def test_pr_only_failure_is_ignored() -> None:
    verdict = check_main_health.evaluate(RUNS, push_workflows={"ci-security"})
    assert verdict["healthy"] is True
    assert verdict["ignored_pr_only"] == ["ci-evidence"]
    assert verdict["failures"] == []


def test_push_triggered_failure_still_counts() -> None:
    verdict = check_main_health.evaluate(RUNS, push_workflows={"ci-security", "ci-evidence"})
    assert verdict["healthy"] is False
    assert [f["workflow"] for f in verdict["failures"]] == ["ci-evidence"]


def test_none_push_set_keeps_conservative_behavior() -> None:
    verdict = check_main_health.evaluate(RUNS, push_workflows=None)
    assert verdict["healthy"] is False


def test_push_trigger_probe() -> None:
    pr_only = "name: ci-evidence\non:\n  pull_request:\n    branches: [main]\n"
    both = "name: x\non:\n  pull_request:\n  push:\n    branches: [main]\n"
    inline = "name: y\non: [push]\n"
    assert check_main_health._workflow_has_push_trigger(pr_only) is False
    assert check_main_health._workflow_has_push_trigger(both) is True
    assert check_main_health._workflow_has_push_trigger(inline) is True
