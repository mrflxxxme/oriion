"""Role-prompt loader — parse contracts/role-prompts/<role>.md.

Each role-prompt file is a markdown document with:
  1. YAML frontmatter delimited by `---` lines (role_id, version, status,
     model_default, contract_type, preset, ...)
  2. Nine numbered sections starting with `# 1.`, `# 2.`, ... `# 9.`
     covering role identity, behavioral instructions, output contracts,
     quality bar, anti-patterns, few-shot examples, vocabulary,
     handoffs, self-evaluation.

Phase 00.5b Commit 5 first-pass alignment hardening per T5: mechanical
checks (frontmatter parses + 9-section structure present). v1.0.0 SemVer
lift — Phase 01.1 retro per AC14.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.agents.exceptions import RolePromptParseError

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SECTION_HEADER_RE = re.compile(r"^# (\d+)\. ", re.MULTILINE)
_EXPECTED_SECTION_COUNT = 9


@dataclass(frozen=True)
class RolePrompt:
    """Parsed role-prompt — frontmatter + sections + raw text."""

    role_id: str
    version: str
    status: str
    model_default: str
    preset: str
    contract_type: str
    language: str
    frontmatter: dict[str, Any]
    sections: dict[int, str]
    raw_text: str

    def composed_system_prompt(self) -> str:
        """Return the full text minus frontmatter — what feeds Pydantic-AI."""
        return _FRONTMATTER_RE.sub("", self.raw_text, count=1).strip()


def parse_role_prompt_text(raw: str, *, role_filename: str) -> RolePrompt:
    """Parse one role-prompt markdown string. Raises RolePromptParseError."""
    fm_match = _FRONTMATTER_RE.match(raw)
    if not fm_match:
        raise RolePromptParseError(
            f"{role_filename}: missing YAML frontmatter (expected --- delimited "
            "block at file start). See contracts/role-prompts/coordinator.md "
            "for the canonical shape."
        )
    try:
        frontmatter = yaml.safe_load(fm_match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise RolePromptParseError(
            f"{role_filename}: frontmatter YAML parse failed — {exc}"
        ) from exc

    if not isinstance(frontmatter, dict):
        raise RolePromptParseError(
            f"{role_filename}: frontmatter must be a YAML mapping, got "
            f"{type(frontmatter).__name__}"
        )

    required = {"role_id", "version", "status", "model_default", "contract_type"}
    missing = required - frontmatter.keys()
    if missing:
        raise RolePromptParseError(
            f"{role_filename}: frontmatter missing required keys {sorted(missing)}"
        )

    body = raw[fm_match.end() :]
    section_numbers = [int(m.group(1)) for m in _SECTION_HEADER_RE.finditer(body)]
    if len(section_numbers) < _EXPECTED_SECTION_COUNT:
        raise RolePromptParseError(
            f"{role_filename}: expected {_EXPECTED_SECTION_COUNT} numbered "
            f"sections (# 1. ... # 9.), found {len(section_numbers)} "
            f"({section_numbers}). T5 alignment hardening requires the full "
            "9-section structure for first-pass acceptance."
        )
    # Section monotonicity — # 1, # 2, ... must be in order, no gaps.
    expected_seq = list(range(1, _EXPECTED_SECTION_COUNT + 1))
    if section_numbers[:_EXPECTED_SECTION_COUNT] != expected_seq:
        raise RolePromptParseError(
            f"{role_filename}: section numbers not monotonic 1..9 "
            f"(saw {section_numbers[: _EXPECTED_SECTION_COUNT]})"
        )

    # Extract each section's content.
    section_texts: dict[int, str] = {}
    spans = list(_SECTION_HEADER_RE.finditer(body))
    for i, m in enumerate(spans):
        n = int(m.group(1))
        start = m.end()
        end = spans[i + 1].start() if i + 1 < len(spans) else len(body)
        section_texts[n] = body[start:end].strip()

    return RolePrompt(
        role_id=str(frontmatter["role_id"]),
        version=str(frontmatter["version"]),
        status=str(frontmatter["status"]),
        model_default=str(frontmatter["model_default"]),
        preset=str(frontmatter.get("preset", "")),
        contract_type=str(frontmatter["contract_type"]),
        language=str(frontmatter.get("language", "ru")),
        frontmatter=frontmatter,
        sections=section_texts,
        raw_text=raw,
    )


def load_role_prompt(role_slug: str, *, prompts_dir: Path | None = None) -> RolePrompt:
    """Load `contracts/role-prompts/<role_slug>.md` and parse it.

    The default ``prompts_dir`` walks up from this file to find
    ``.planning/contracts/role-prompts``. Override for tests.
    """
    if prompts_dir is None:
        # Walk: backend/src/agents/services/role_prompt_loader.py →
        # backend/src/agents/services → backend/src/agents → backend/src →
        # backend → repo-root → .planning/contracts/role-prompts
        here = Path(__file__).resolve()
        repo_root = here.parents[4]
        prompts_dir = repo_root / ".planning" / "contracts" / "role-prompts"

    path = prompts_dir / f"{role_slug}.md"
    if not path.exists():
        raise RolePromptParseError(
            f"role-prompt not found at {path}. Expected one of "
            "{coordinator, researcher, writer, analyst}.md under "
            ".planning/contracts/role-prompts/."
        )
    return parse_role_prompt_text(path.read_text(encoding="utf-8"), role_filename=str(path))
