"""verify_evidence.py freshness semantics (ADR-037 D3).

The evidence artifact records the commit the gate ran against; committing the
artifact itself advances the branch tip, so freshness is defined as "no commit
after the gate touches anything OUTSIDE evidence/". These tests build a real
throwaway git repo and drive the stdlib verifier through both sides of that
boundary: an evidence-only tail must verify, a code commit after the gate must
stale the evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "scripts" / "autonomy" / "verify_evidence.py"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, "--no-verify")
    return _git(repo, "rev-parse", "HEAD")


def _run_verifier(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def evidence_repo(tmp_path: Path) -> tuple[Path, str]:
    """Throwaway repo: one code commit (the gate target) + manifest/evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@teamly-ai")
    _git(repo, "config", "user.name", "tooling-test")
    (repo / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    gate_sha = _commit_all(repo, "feat: code under test")

    evidence_dir = repo / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "manifest.json").write_text(
        json.dumps({"phase": "test", "required_gates": ["docker_integration"]}),
        encoding="utf-8",
    )
    (evidence_dir / "docker_integration.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "docker_integration",
                "head_sha": gate_sha,
                "timestamp": "2026-07-03T00:00:00Z",
                "verdict": "PASS",
            }
        ),
        encoding="utf-8",
    )
    return repo, gate_sha


def test_evidence_only_tail_is_fresh(evidence_repo: tuple[Path, str]) -> None:
    repo, _ = evidence_repo
    _commit_all(repo, "docs(evidence): gate artifacts")

    result = _run_verifier(repo)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "evidence-only tail" in result.stdout


def test_code_commit_after_gate_stales_evidence(
    evidence_repo: tuple[Path, str],
) -> None:
    repo, _ = evidence_repo
    _commit_all(repo, "docs(evidence): gate artifacts")
    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    _commit_all(repo, "feat: sneaky change after the gate ran")

    result = _run_verifier(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "STALE" in result.stdout


def test_mixed_commit_after_gate_stales_evidence(
    evidence_repo: tuple[Path, str],
) -> None:
    """A commit touching evidence/ AND code must NOT count as evidence-only."""
    repo, _ = evidence_repo
    (repo / "code.py").write_text("VALUE = 3\n", encoding="utf-8")
    _commit_all(repo, "mixed: evidence + code in one commit")

    result = _run_verifier(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "STALE" in result.stdout
