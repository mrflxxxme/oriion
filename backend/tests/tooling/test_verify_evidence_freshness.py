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


# ── PR diff-scoping (--base-ref): evidence inherited from a prior squash ──────


def _run_verifier_scoped(repo: Path, base_ref: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), "--base-ref", base_ref],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_inherited_evidence_unchanged_is_skipped(
    evidence_repo: tuple[Path, str],
) -> None:
    """The core fix: evidence left on the base by a prior squash that THIS PR does
    NOT touch is skipped, not failed for staleness."""
    repo, _ = evidence_repo
    _commit_all(repo, "docs(evidence): gate artifacts")
    (repo / "unrelated.py").write_text("X = 1\n", encoding="utf-8")
    base_sha = _commit_all(repo, "feat: base advances past the gate (evidence stale)")
    # The PR: a code-only commit off base — touches no evidence/.
    (repo / "code.py").write_text("VALUE = 99\n", encoding="utf-8")
    _commit_all(repo, "feat: PR touches code only")

    # Legacy (unscoped) still stales — proves the bug the scoping fixes.
    legacy = _run_verifier(repo)
    assert legacy.returncode == 1 and "STALE" in legacy.stdout

    scoped = _run_verifier_scoped(repo, base_sha)
    assert scoped.returncode == 0, scoped.stdout + scoped.stderr
    assert "SKIP" in scoped.stdout and "inherited" in scoped.stdout


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@teamly-ai")
    _git(repo, "config", "user.name", "tooling-test")
    return repo


def _write_evidence(repo: Path, gates: list[str], head_sha: str) -> None:
    ev = repo / "evidence"
    ev.mkdir(exist_ok=True)
    (ev / "manifest.json").write_text(
        json.dumps({"phase": "p", "required_gates": gates}), encoding="utf-8"
    )
    for gate in gates:
        (ev / f"{gate}.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": gate,
                    "head_sha": head_sha,
                    "timestamp": "2026-07-09T00:00:00Z",
                    "verdict": "PASS",
                }
            ),
            encoding="utf-8",
        )


def test_scoped_pr_shipping_fresh_evidence_is_verified(tmp_path: Path) -> None:
    """Teeth kept: a PR that ships its OWN fresh evidence is still verified."""
    repo = _init_repo(tmp_path)
    (repo / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    base_sha = _commit_all(repo, "feat: base (no evidence)")
    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    pr_code_sha = _commit_all(repo, "feat: PR code")
    _write_evidence(repo, ["docker_integration"], head_sha=pr_code_sha)
    _commit_all(repo, "docs(evidence): fresh gate artifacts")

    result = _run_verifier_scoped(repo, base_sha)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK]" in result.stdout and "docker_integration" in result.stdout


def test_scoped_manifest_change_without_evidence_fails(tmp_path: Path) -> None:
    """Teeth kept: editing the manifest re-declares the gate set, so a newly
    declared gate with no evidence still fails under scoping."""
    repo = _init_repo(tmp_path)
    (repo / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    gate_sha = _commit_all(repo, "feat: base code")
    _write_evidence(repo, ["docker_integration"], head_sha=gate_sha)
    base_sha = _commit_all(repo, "docs(evidence): base gate")
    # PR: declare a new gate in the manifest but ship no artifact for it.
    (repo / "evidence" / "manifest.json").write_text(
        json.dumps({"phase": "p", "required_gates": ["docker_integration", "live_golden"]}),
        encoding="utf-8",
    )
    _commit_all(repo, "docs(evidence): declare live_golden (no artifact)")

    result = _run_verifier_scoped(repo, base_sha)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "live_golden" in result.stdout and "MISS" in result.stdout
