"""check_docs_freshness.py — ADR-040 D9 docs-freshness gate.

Verifies merged-detection keys off the SUBJECT clause (before the em-dash) — so a
"Next -> 01.8c" mention is not treated as merged — and that a merged phase whose
spec Status is still non-terminal is flagged (AC: synthetic stale caught).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "check_docs_freshness.py"

_EMDASH = "—"

_STATUS = (
    f"**Phase 01.7 + 01.8-mail + 01.8 {_EMDASH} ✅ MERGED** details here.\n"
    f"**Phase 01.6 {_EMDASH} ✅ Code-complete** more.\n"
    f"**Docs-refinement {_EMDASH} ✅ Complete.** Next → `/autonomy:run 01.8c` (autonomy).\n"
    f"| 00.1 {_EMDASH} Repo | ✅ Complete | done |\n"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_docs_freshness", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_merged_ids_use_subject_not_incidental_mention() -> None:
    mod = _load()
    merged = mod.merged_phase_ids(_STATUS)
    assert "01.7" in merged
    assert "01.8-mail" in merged
    assert "01.6" in merged
    # "Next -> 01.8c" is AFTER the em-dash on a non-"Phase" subject -> not merged.
    assert "01.8c" not in merged


def test_merged_but_pending_spec_is_flagged(tmp_path: Path) -> None:
    mod = _load()
    spec_dir = tmp_path / "phases"
    spec_dir.mkdir(parents=True)
    stale = spec_dir / "01.7-rbac.md"
    stale.write_text("# Phase 01.7\n\n- **Status:** \U0001f504 In progress\n", encoding="utf-8")
    fresh = spec_dir / "01.6-security.md"
    fresh.write_text("# Phase 01.6\n\n- **Status:** ✅ Merged\n", encoding="utf-8")

    findings = mod.find_stale(_STATUS, [stale, fresh])
    assert len(findings) == 1
    assert "01.7-rbac.md" in findings[0]
    assert "non-terminal" in findings[0]


def test_plan_and_verification_files_skipped(tmp_path: Path) -> None:
    mod = _load()
    spec_dir = tmp_path / "phases"
    spec_dir.mkdir(parents=True)
    plan = spec_dir / "01.7-PLAN.md"
    plan.write_text("- **Status:** Pending\n", encoding="utf-8")
    assert mod.find_stale(_STATUS, [plan]) == []


def test_no_status_line_is_skipped_not_failed(tmp_path: Path) -> None:
    mod = _load()
    spec_dir = tmp_path / "phases"
    spec_dir.mkdir(parents=True)
    legacy = spec_dir / "01.6-security.md"  # merged, but no parseable Status line
    legacy.write_text("# Phase 01.6\n\nsome prose, no status field\n", encoding="utf-8")
    assert mod.find_stale(_STATUS, [legacy]) == []


def test_real_tree_is_fresh() -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout + res.stderr
