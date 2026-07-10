"""check_subagents.py — ADR-040 D8 native-subagent conformance gate.

Drives the pure ``find_violations(agents_dir)`` against synthetic trees plus a
real-tree subprocess smoke (guards the live 11 spawn-entries stay conformant).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "check_subagents.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_subagents", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_role(agents: Path, name: str, *, body_frontmatter: str, handbook: bool = True) -> None:
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.md").write_text(body_frontmatter, encoding="utf-8")
    if handbook:
        hb = agents / name
        hb.mkdir(parents=True, exist_ok=True)
        (hb / "profile.md").write_text("# profile\n", encoding="utf-8")
        (hb / "system-prompt.md").write_text("# system prompt\n", encoding="utf-8")


_VALID = (
    "---\nname: {name}\ndescription: does a thing\ntools: Read, Grep\nmodel: opus\n---\n\nbody\n"
)


def test_valid_tree_has_no_violations(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True)
    _make_role(agents, "architect", body_frontmatter=_VALID.format(name="architect"))
    _make_role(agents, "planner", body_frontmatter=_VALID.format(name="planner"))
    assert mod.find_violations(agents) == []


def test_name_mismatch_and_missing_key_flagged(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    # name != stem, and no 'model' key.
    _make_role(
        agents,
        "verifier",
        body_frontmatter="---\nname: wrong\ndescription: x\ntools: Read\n---\nbody\n",
    )
    violations = mod.find_violations(agents)
    joined = "\n".join(violations)
    assert "name 'wrong' != file stem 'verifier'" in joined
    assert "'model' missing or empty" in joined


def test_missing_handbook_flagged(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    _make_role(agents, "designer", body_frontmatter=_VALID.format(name="designer"), handbook=False)
    violations = mod.find_violations(agents)
    assert any("system-prompt.md' not found" in v for v in violations)


def test_reverse_handbook_without_entry_flagged(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    agents.mkdir(parents=True)
    # A role handbook dir with profile.md but no spawnable <role>.md entry.
    hb = agents / "evaluator"
    hb.mkdir()
    (hb / "profile.md").write_text("# p\n", encoding="utf-8")
    (hb / "system-prompt.md").write_text("# s\n", encoding="utf-8")
    violations = mod.find_violations(agents)
    assert any("no spawnable" in v and "evaluator" in v for v in violations)


def test_missing_frontmatter_flagged(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    agents.mkdir(parents=True)
    (agents / "planner.md").write_text("no frontmatter here\n", encoding="utf-8")
    violations = mod.find_violations(agents)
    assert any("frontmatter" in v for v in violations)


def test_unknown_tool_name_flagged(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    _make_role(
        agents,
        "architect",
        body_frontmatter="---\nname: architect\ndescription: x\ntools: Read, Bazh, Grep\nmodel: opus\n---\nbody\n",
    )
    violations = mod.find_violations(agents)
    assert any("unknown Claude Code tool 'Bazh'" in v for v in violations)


def test_scoped_role_gaps_flags_missing(tmp_path: Path) -> None:
    mod = _load()
    agents = tmp_path / "agents"
    agents.mkdir(parents=True)
    gaps = mod.scoped_role_gaps(agents)  # empty dir -> all 6 scoped roles missing
    assert len(gaps) >= 6
    assert any("reviewer-security" in g for g in gaps)


def test_scoped_role_gaps_real_tree_clean() -> None:
    """The live .claude/agents/ carries all 6 role_scope_hook-scoped roles + allowlists."""
    mod = _load()
    assert mod.scoped_role_gaps(REPO_ROOT / ".claude" / "agents") == []


def test_real_tree_conforms() -> None:
    """The committed 11 spawn-entries must pass (guards ongoing conformance)."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout + res.stderr
