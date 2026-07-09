"""Unit: telegram-creator golden-dataset parses (count + schema).

Validates the AI-baseline golden-dataset shipped this phase (Phase 01.10) —
30 golden tasks (5 primary-task buckets × 6 variants: 2 easy / 3 medium /
1 hard) + 5 adversarial probes — mirrors the ``agency-marketing-ru``
golden-dataset shape/frontmatter contract (per
``golden-dataset/README.md``). No live LLM calls — this only parses the
on-disk markdown+YAML-frontmatter files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_REQUIRED_TASK_KEYS = {
    "id",
    "slug",
    "difficulty",
    "primary_task",
    "agent_archetype",
    "archetype_path",
    "created_by",
    "created_at",
    "adversarial",
    "last_evaluated",
}
_REQUIRED_ADVERSARIAL_KEYS = {
    "id",
    "slug",
    "difficulty",
    "primary_task",
    "agent_archetype",
    "created_by",
    "created_at",
    "adversarial",
    "pass_threshold",
    "last_evaluated",
}
_PRIMARY_TASKS = {
    "content-plan",
    "post-drafting",
    "channel-audit",
    "compliance-audit",
    "monetization-and-repurposing",
}


def _golden_dataset_dir() -> Path:
    # backend/tests/agents/test_x.py -> parents[3] == repo root (matches
    # role_prompt_loader.py's host-walk depth convention for its own file).
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / ".planning" / "verticals" / "telegram-creator" / "golden-dataset"


_BARE_NUMERIC_ID_RE = re.compile(r"^(id:\s*)(\d+)\s*$", re.MULTILINE)


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    assert match is not None, f"{path.name}: missing YAML frontmatter"
    fm_text = match.group(1)
    # `id: 010`-style bare zero-padded numerals are YAML-1.1 octal literals to
    # PyYAML's safe_load (e.g. "010" resolves to the int 8, not 10) — quote
    # the scalar before parsing so `id` round-trips as the zero-padded string
    # the filename prefix actually encodes. This is a test-parsing concern
    # only; the on-disk frontmatter convention (bare `id: NNN`) intentionally
    # matches agency-marketing-ru / wb-seller and is left untouched.
    fm_text = _BARE_NUMERIC_ID_RE.sub(r'\1"\2"', fm_text, count=1)
    frontmatter = yaml.safe_load(fm_text)
    assert isinstance(frontmatter, dict), f"{path.name}: frontmatter must be a mapping"
    return frontmatter


def _numeric_prefix(filename: str) -> int:
    return int(filename.split("-", 1)[0])


def _zero_padded_prefix(filename: str) -> str:
    return filename.split("-", 1)[0]


@pytest.fixture(scope="module")
def golden_dir() -> Path:
    d = _golden_dataset_dir()
    assert d.is_dir(), f"golden-dataset dir not found at {d}"
    return d


def test_golden_dataset_has_exactly_30_tasks(golden_dir: Path) -> None:
    task_files = sorted((golden_dir / "tasks").glob("[0-9][0-9][0-9]-*.md"))
    assert len(task_files) == 30, [f.name for f in task_files]


def test_golden_dataset_has_exactly_5_adversarial_probes(golden_dir: Path) -> None:
    probe_files = sorted((golden_dir / "adversarial").glob("A[0-9][0-9][0-9]-*.md"))
    assert len(probe_files) == 5, [f.name for f in probe_files]


def test_golden_tasks_frontmatter_schema_and_ids(golden_dir: Path) -> None:
    task_files = sorted((golden_dir / "tasks").glob("[0-9][0-9][0-9]-*.md"))
    seen_ids: set[int] = set()
    difficulty_counts: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
    primary_task_counts: dict[str, int] = {}
    for path in task_files:
        fm = _parse_frontmatter(path)
        missing = _REQUIRED_TASK_KEYS - fm.keys()
        assert not missing, f"{path.name}: missing frontmatter keys {sorted(missing)}"
        assert fm["adversarial"] is False, f"{path.name}: golden task must have adversarial: false"
        assert fm["difficulty"] in difficulty_counts, f"{path.name}: unexpected difficulty"
        assert fm["primary_task"] in _PRIMARY_TASKS, f"{path.name}: unexpected primary_task"
        assert fm["agent_archetype"] == "master-telegram-creator"

        assert str(fm["id"]) == _zero_padded_prefix(path.name), f"{path.name}: id/filename mismatch"
        seen_ids.add(_numeric_prefix(path.name))
        difficulty_counts[fm["difficulty"]] += 1
        primary_task_counts[fm["primary_task"]] = primary_task_counts.get(fm["primary_task"], 0) + 1

    assert seen_ids == set(range(1, 31)), sorted(seen_ids)
    # Coverage matrix: 5 primary tasks x 6 variants (2 easy/3 medium/1 hard).
    assert difficulty_counts == {"easy": 10, "medium": 15, "hard": 5}
    assert primary_task_counts == dict.fromkeys(_PRIMARY_TASKS, 6)


def test_adversarial_probes_frontmatter_schema_and_ids(golden_dir: Path) -> None:
    probe_files = sorted((golden_dir / "adversarial").glob("A[0-9][0-9][0-9]-*.md"))
    seen_ids: set[str] = set()
    for path in probe_files:
        fm = _parse_frontmatter(path)
        missing = _REQUIRED_ADVERSARIAL_KEYS - fm.keys()
        assert not missing, f"{path.name}: missing frontmatter keys {sorted(missing)}"
        assert fm["adversarial"] is True, f"{path.name}: probe must have adversarial: true"
        assert fm["difficulty"] == "adversarial"
        assert fm["pass_threshold"] == "100%"
        assert fm["agent_archetype"] == "master-telegram-creator"
        seen_ids.add(str(fm["id"]))

    assert seen_ids == {"A001", "A002", "A003", "A004", "A005"}


def test_golden_dataset_readme_and_adversarial_readme_present(golden_dir: Path) -> None:
    assert (golden_dir / "README.md").is_file()
    assert (golden_dir / "adversarial" / "README.md").is_file()
