"""provision_env.py — funded-env provisioning security invariants (ADR-037).

Builds throwaway git repos with a linked worktree and drives the stdlib helper
through: absent-dest copy, idempotent no-overwrite, refusal when the destination
is NOT git-ignored (the secret-safety gate), and the no-canonical stuck path.
Uses only a dummy value so nothing real is ever written.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "provision_env.py"
# Low-entropy placeholders only — nothing here should ever match a secret scanner.
DUMMY = "DEEPSEEK_API_KEY=placeholder\nYANDEX_API_KEY=placeholder\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True
    )


@pytest.fixture()
def main_and_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A main repo (with canonical backend/.env) + a linked worktree."""
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "config", "user.email", "t@teamly-ai")
    _git(main, "config", "user.name", "t")
    (main / ".gitignore").write_text("backend/.env\n", encoding="utf-8")
    (main / "backend").mkdir()
    (main / "backend" / ".env").write_text(DUMMY, encoding="utf-8")
    (main / "README.md").write_text("x\n", encoding="utf-8")
    _git(main, "add", "-A")
    _git(main, "commit", "-q", "-m", "init")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))
    return main, wt


def test_provisions_when_absent(main_and_worktree: tuple[Path, Path]) -> None:
    _, wt = main_and_worktree
    assert not (wt / "backend" / ".env").exists()
    res = _run(wt)
    assert res.returncode == 0, res.stderr
    assert (wt / "backend" / ".env").read_text(encoding="utf-8") == DUMMY
    assert "provisioned" in res.stdout
    # the summary reports key NAMES + counts, never values
    assert "placeholder" not in (res.stdout + res.stderr)


def test_idempotent_no_overwrite(main_and_worktree: tuple[Path, Path]) -> None:
    _, wt = main_and_worktree
    (wt / "backend").mkdir(parents=True, exist_ok=True)
    (wt / "backend" / ".env").write_text("PRE=existing\n", encoding="utf-8")
    res = _run(wt)
    assert res.returncode == 0
    assert (wt / "backend" / ".env").read_text(encoding="utf-8") == "PRE=existing\n"
    assert "present" in res.stdout


def test_refuses_when_dest_not_ignored(main_and_worktree: tuple[Path, Path]) -> None:
    main, wt = main_and_worktree
    # Un-ignore backend/.env on the worktree's branch -> the safety gate must fire.
    (wt / ".gitignore").write_text("# nothing ignored\n", encoding="utf-8")
    _git(wt, "add", ".gitignore")
    _git(wt, "commit", "-q", "-m", "un-ignore env")
    res = _run(wt)
    assert res.returncode == 3, res.stdout + res.stderr
    assert not (wt / "backend" / ".env").exists()
    assert "REFUSED" in res.stderr


def test_no_canonical_is_stuck_path(main_and_worktree: tuple[Path, Path]) -> None:
    main, wt = main_and_worktree
    (main / "backend" / ".env").unlink()
    res = _run(wt)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "no canonical" in res.stderr
