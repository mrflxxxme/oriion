"""Tests for scripts/check_tools_allowlist.py — ADR-028 P-AUDIT-3 gate.

Covers:
  (a) the real repository passes the conformance check (registry + live
      vertical-prompt allowlists are mutually consistent);
  (b) a synthetic allowlist referencing a bogus slug fails;
  (c) frontmatter parsing boundaries (comments, block termination, built-ins).

The script lives in the repo-root ``scripts/`` directory (one level above
``backend/``). It is loaded via importlib from its absolute path so the tests do
not depend on ``scripts`` being importable on ``sys.path``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

# backend/tests/tooling/ -> repo root is three parents up from this file's dir.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_tools_allowlist.py"
_REGISTRY_PATH = _REPO_ROOT / ".planning" / "tools" / "registry.md"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_tools_allowlist", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MOD = _load_module()


def _write_allowlist(path: Path, slugs: list[str]) -> Path:
    """Write a minimal vertical-prompt file with a ``tools_allowed:`` block."""
    lines = ["---", "role: synthetic", "tools_allowed:"]
    lines += [f"  - {slug}" for slug in slugs]
    lines += ["---", "", "# Body", "Some prose.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_script_path_exists() -> None:
    assert _SCRIPT_PATH.is_file(), f"missing script at {_SCRIPT_PATH}"
    assert _REGISTRY_PATH.is_file(), f"missing registry at {_REGISTRY_PATH}"


def test_registry_parses_to_known_slugs() -> None:
    slugs = _MOD.load_registry_slugs(_REGISTRY_PATH)
    # Sanity: a representative slug from each registry category is present, and
    # the table-header / separator rows did not leak in as pseudo-slugs.
    assert "memory.cells_search" in slugs
    assert "tasks.create" in slugs
    assert "llm.chat_completions" in slugs
    assert "Read" in slugs
    assert "Slug" not in slugs
    assert "---" not in slugs


def test_real_repo_passes() -> None:
    """(a) The live registry + vertical-prompt allowlists are conformant."""
    allowlist_paths = _MOD._collect_allowlist_paths(_REPO_ROOT)
    assert allowlist_paths, "expected at least one vertical-prompt allowlist file"
    violations = _MOD.find_unknown_slugs(_REGISTRY_PATH, allowlist_paths)
    assert violations == [], f"unexpected conformance violations: {violations}"


def test_real_repo_main_returns_zero(capsys) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: the CLI entrypoint reports OK and returns 0 on the clean repo."""
    rc = _MOD.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_bogus_slug_fails(tmp_path: Path) -> None:
    """(b) A synthetic allowlist with an unknown slug is reported as a violation."""
    bad = _write_allowlist(
        tmp_path / "bogus.md",
        ["tasks.create", "this.is_not_in_registry", "Read"],
    )
    violations = _MOD.find_unknown_slugs(_REGISTRY_PATH, [bad])
    assert len(violations) == 1
    assert "this.is_not_in_registry" in violations[0]
    assert "bogus.md" in violations[0]


def test_all_valid_slugs_pass(tmp_path: Path) -> None:
    good = _write_allowlist(
        tmp_path / "good.md",
        ["tasks.create", "llm.chat_completions", "memory.roles_search", "Read"],
    )
    assert _MOD.find_unknown_slugs(_REGISTRY_PATH, [good]) == []


def test_extract_handles_comments_and_block_end(tmp_path: Path) -> None:
    """Inline + standalone comments stay in-block; the next YAML key ends it."""
    path = tmp_path / "commented.md"
    path.write_text(
        "\n".join(
            [
                "---",
                "role: x",
                "tools_allowed:",
                "  # leading comment line",
                "  - tasks.create  # inline comment",
                "  - llm.chat_completions",
                "model_provider: anthropic",  # next key terminates the block
                "  - tasks.get",  # outside the block: must be ignored
                "---",
            ]
        ),
        encoding="utf-8",
    )
    slugs = _MOD.extract_allowlist_slugs(path)
    assert slugs == ["tasks.create", "llm.chat_completions"]


def test_extract_returns_empty_when_no_block(tmp_path: Path) -> None:
    path = tmp_path / "no_block.md"
    path.write_text("---\nrole: x\n---\n\n# Body only\n", encoding="utf-8")
    assert _MOD.extract_allowlist_slugs(path) == []
