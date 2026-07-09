"""export_openapi.py — ADR-040 D2 OpenAPI snapshot export + drift check.

Tests the pure helpers (deterministic serialization, unified diff) and the
freshness check with an injected fake schema — no need to import the FastAPI app.
A route/schema change (synthetic breaking-diff) must be caught (non-empty diff /
not-fresh), which is what the ci-backend `--check` step relies on.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "export_openapi.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_openapi", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_canonical_json_is_deterministic_and_sorted() -> None:
    mod = _load()
    a = mod.canonical_json({"b": 1, "a": {"y": 2, "x": 1}})
    b = mod.canonical_json({"a": {"x": 1, "y": 2}, "b": 1})
    assert a == b  # key order independent
    assert a.endswith("\n")
    assert a.index('"a"') < a.index('"b"')  # sorted


def test_diff_text_empty_when_identical_and_nonempty_on_change() -> None:
    mod = _load()
    base = {"paths": {"/health": {"get": {}}}}
    assert mod.diff_text(mod.canonical_json(base), mod.canonical_json(base)) == ""
    # Synthetic breaking change: a route removed.
    changed = {"paths": {}}
    diff = mod.diff_text(mod.canonical_json(base), mod.canonical_json(changed))
    assert diff != ""
    assert "/health" in diff


def test_check_snapshot_fresh_and_drifted(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    mod = _load()
    live = {"openapi": "3.1.0", "paths": {"/x": {"get": {}}}}
    monkeypatch.setattr(mod, "build_live_spec", lambda: live)

    snap = tmp_path / "openapi.snapshot.json"
    # Missing file -> not fresh.
    fresh, diff = mod.check_snapshot(snap)
    assert not fresh and "missing" in diff

    # Matching committed snapshot -> fresh.
    snap.write_text(mod.canonical_json(live), encoding="utf-8")
    fresh, diff = mod.check_snapshot(snap)
    assert fresh and diff == ""

    # Drifted committed snapshot -> not fresh, diff shows it.
    snap.write_text(mod.canonical_json({"openapi": "3.1.0", "paths": {}}), encoding="utf-8")
    fresh, diff = mod.check_snapshot(snap)
    assert not fresh and diff != ""


def test_committed_snapshot_exists() -> None:
    """The repo ships a snapshot (ci-backend --check compares against it)."""
    assert (REPO_ROOT / ".planning" / "contracts" / "openapi.snapshot.json").is_file()
