"""role_scope_hook.py — PreToolUse per-role tool-scope enforcement (chip task_dd666049).

Drives the pure ``evaluate(payload)`` with synthetic PreToolUse payloads + a subprocess
smoke on the exit-code contract (0 allow / 2 block). Verifies: main agent + implementers
are never blocked (fail-open on identity), restricted roles are path/mutation fenced
(fail-closed on Write scope), and command-position matching for Bash.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "role_scope_hook.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("role_scope_hook", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _p(agent: str | None, tool: str, **tool_input: object) -> dict[str, object]:
    payload: dict[str, object] = {"tool_name": tool, "tool_input": tool_input}
    if agent is not None:
        payload["agent_type"] = agent
    return payload


# ---- fail-open on identity: main agent + implementers are never blocked ----


def test_main_agent_never_blocked() -> None:
    mod = _load()
    # No agent_type = main agent: even a source write or a git commit passes.
    assert mod.evaluate(_p(None, "Write", file_path="backend/src/x.py"))[0] is True
    assert mod.evaluate(_p(None, "Bash", command="git commit -m x"))[0] is True


def test_unrestricted_role_never_blocked() -> None:
    mod = _load()
    assert mod.evaluate(_p("backend-implementer", "Write", file_path="backend/src/x.py"))[0] is True
    assert mod.evaluate(_p("backend-implementer", "Bash", command="git commit -m x"))[0] is True
    assert (
        mod.evaluate(_p("Explore", "Bash", command="rm -rf /tmp/x"))[0] is True
    )  # built-in, not restricted


# ---- Write/Edit fail-closed path scope for restricted roles ----


def test_reviewer_write_scope() -> None:
    mod = _load()
    assert (
        mod.evaluate(
            _p("reviewer-security", "Write", file_path="revisions/01.8c-reviewer-security.md")
        )[0]
        is True
    )
    assert (
        mod.evaluate(
            _p(
                "reviewer-security",
                "Edit",
                file_path="/abs/repo/revisions/01.8c-reviewer-security-critical.md",
            )
        )[0]
        is True
    )
    ok, reason = mod.evaluate(
        _p("reviewer-security", "Edit", file_path="backend/src/security/dlp.py")
    )
    assert ok is False and "out of scope" in reason
    assert mod.evaluate(_p("reviewer-backend", "Write", file_path="backend/src/x.py"))[0] is False


def test_verifier_and_architect_and_evaluator_write_scope() -> None:
    mod = _load()
    assert (
        mod.evaluate(_p("verifier", "Write", file_path="verification-reports/01.8c/report.md"))[0]
        is True
    )
    assert mod.evaluate(_p("verifier", "Write", file_path="backend/tests/test_x.py"))[0] is False
    assert (
        mod.evaluate(_p("architect", "Write", file_path=".planning/decisions/ADR-050-x.md"))[0]
        is True
    )
    assert mod.evaluate(_p("architect", "Write", file_path="backend/src/main.py"))[0] is False
    assert (
        mod.evaluate(_p("evaluator", "Write", file_path=".tmp/evaluator-runs/r1/out.json"))[0]
        is True
    )
    assert (
        mod.evaluate(_p("evaluator", "Write", file_path="evidence/judge_panel_x.json"))[0] is True
    )
    assert (
        mod.evaluate(
            _p("evaluator", "Write", file_path=".planning/contracts/role-prompts/analyst.md")
        )[0]
        is False
    )


def test_write_without_path_is_fail_closed() -> None:
    mod = _load()
    ok, reason = mod.evaluate(_p("verifier", "Write"))
    assert ok is False and "unverifiable" in reason


# ---- Bash mutation deny-list for restricted roles ----


def test_bash_denies_mutations_allows_reads() -> None:
    mod = _load()
    deny = [
        "git commit -m x",
        "git push origin main",
        "git reset --hard",
        "git rebase main",
        "git checkout -- file.py",
        "rm -rf build",
        "sudo apt install x",
        "chmod +x s.sh",
        "npm install",
        "pip install requests",
        "uv add httpx",
        "git push --force-with-lease origin f",
    ]
    for cmd in deny:
        ok, _ = mod.evaluate(_p("reviewer-backend", "Bash", command=cmd))
        assert ok is False, f"should block: {cmd}"
    allow = [
        "git status",
        "git diff origin/main",
        "git log --oneline -5",
        "pytest -q",
        "npm test",
        "ruff check backend/src",
        "mypy backend/",
        "git checkout feature-x",
        "bandit -r backend/src -f json",
        "npm run typecheck",
    ]
    for cmd in allow:
        ok, _ = mod.evaluate(_p("reviewer-backend", "Bash", command=cmd))
        assert ok is True, f"should allow: {cmd}"


def test_bash_command_position_not_substring() -> None:
    mod = _load()
    # "git commit" mentioned inside a quoted echo is NOT at command position -> allow.
    assert mod.evaluate(_p("verifier", "Bash", command='echo "how to git commit"'))[0] is True
    # but chained after && it IS -> block.
    assert mod.evaluate(_p("verifier", "Bash", command="pytest -q && git commit -m x"))[0] is False


def test_non_write_bash_tools_pass() -> None:
    mod = _load()
    assert mod.evaluate(_p("reviewer-security", "Read", file_path="backend/src/x.py"))[0] is True
    assert mod.evaluate(_p("reviewer-security", "Grep", pattern="secret"))[0] is True


def test_subprocess_exit_codes() -> None:
    mod_allow = json.dumps(_p("reviewer-backend", "Bash", command="pytest -q"))
    mod_block = json.dumps(_p("reviewer-backend", "Bash", command="git commit -m x"))
    r_allow = subprocess.run(
        [sys.executable, str(SCRIPT)], input=mod_allow, capture_output=True, text=True
    )
    r_block = subprocess.run(
        [sys.executable, str(SCRIPT)], input=mod_block, capture_output=True, text=True
    )
    assert r_allow.returncode == 0, r_allow.stderr
    assert r_block.returncode == 2
    assert "BLOCKED" in r_block.stderr
    # Unparseable payload -> fail-open (exit 0), never bricks tool calls.
    r_bad = subprocess.run(
        [sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True
    )
    assert r_bad.returncode == 0
