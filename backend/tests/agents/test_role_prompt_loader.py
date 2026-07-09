"""Unit tests for role_prompt_loader — frontmatter + 9-section structure."""

from __future__ import annotations

import pytest
from src.agents.exceptions import RolePromptParseError
from src.agents.services.role_prompt_loader import load_role_prompt, parse_role_prompt_text


def test_load_canonical_coordinator_prompt():
    """The shipped coordinator.md must parse + present 9 sections."""
    rp = load_role_prompt("coordinator")
    assert rp.role_id == "coordinator"
    assert (
        rp.version == "1.0.1"
    )  # hardened 01.1 (AC-W1-25); PATCH bump 01.8c brand-rename teamly->profiki
    assert rp.contract_type == "role-prompt"
    assert len(rp.sections) >= 9
    # Section 1 is identity & mission per the canonical structure.
    assert "Координатор" in rp.sections[1] or "Coordinator" in rp.sections[1]
    # composed system prompt strips frontmatter.
    assert "---" not in rp.composed_system_prompt().split("\n")[0]


def test_load_all_four_productivity_core_prompts():
    """All four productivity-core role-prompts must parse."""
    for slug in ("coordinator", "researcher", "writer", "analyst"):
        rp = load_role_prompt(slug)
        assert rp.role_id == slug
        assert len(rp.sections) >= 9, f"{slug} has only {len(rp.sections)} sections"


def test_parse_missing_frontmatter_raises():
    raw = "# 1. Section\nbody\n"
    with pytest.raises(RolePromptParseError, match="missing YAML frontmatter"):
        parse_role_prompt_text(raw, role_filename="test.md")


def test_parse_missing_required_key_raises():
    raw = "---\nrole_id: x\n---\n# 1. Section\nbody\n"
    with pytest.raises(RolePromptParseError, match="missing required keys"):
        parse_role_prompt_text(raw, role_filename="test.md")


def test_parse_too_few_sections_raises():
    raw = (
        "---\nrole_id: x\nversion: 0.1.0\nstatus: Proposed\n"
        "model_default: deepseek-chat\ncontract_type: role-prompt\n---\n"
        "# 1. Identity\nbody\n"
    )
    with pytest.raises(RolePromptParseError, match="expected 9 numbered sections"):
        parse_role_prompt_text(raw, role_filename="test.md")


def test_parse_non_monotonic_sections_raises():
    body_sections = "".join(f"# {n}. Section {n}\nbody\n" for n in [1, 2, 3, 5, 4, 6, 7, 8, 9])
    raw = (
        "---\nrole_id: x\nversion: 0.1.0\nstatus: Proposed\n"
        "model_default: deepseek-chat\ncontract_type: role-prompt\n---\n" + body_sections
    )
    with pytest.raises(RolePromptParseError, match="not monotonic"):
        parse_role_prompt_text(raw, role_filename="test.md")
