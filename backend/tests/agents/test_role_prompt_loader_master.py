"""Unit tests for load_master_prompt (ADR-029 masters/ subdir loader, AC-W1-3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from src.agents.exceptions import RolePromptParseError
from src.agents.services.role_prompt_loader import load_master_prompt

_VALID_MASTER_PROMPT = """---
role_id: master-agency-marketing-ru
version: 0.1.0
status: reviewed
model_default: deepseek-chat
contract_type: role-prompt
vertical_tag: agency_marketing_ru
---

# 1. Role identity
Ты — Master-Agent вертикали «Маркетинговое агентство».

# 2. Behavioral instructions
Думай как доменный эксперт.

# 3. Output format contracts
Верни MasterPlan.

# 4. Quality standards
Высокий доменный bar.

# 5. Anti-patterns & guardrails
Не выдумывай факты.

# 6. Few-shot examples
Пример кейса.

# 7. Domain-aware vocabulary
CTR, CPL, воронка.

# 8. Handoff protocols
Делегируй Координатору.

# 9. Self-evaluation prompts
Проверь доменное качество.
"""


def _write_master(tmp_path: Path, vertical: str, body: str) -> Path:
    masters = tmp_path / "masters"
    masters.mkdir(parents=True, exist_ok=True)
    (masters / f"{vertical}.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_load_master_prompt_parses_masters_subdir(tmp_path: Path) -> None:
    _write_master(tmp_path, "agency_marketing_ru", _VALID_MASTER_PROMPT)
    prompt = load_master_prompt("agency_marketing_ru", prompts_dir=tmp_path)
    assert prompt.role_id == "master-agency-marketing-ru"
    assert prompt.status == "reviewed"
    assert len(prompt.sections) == 9
    # composed prompt drops the frontmatter.
    assert "role_id:" not in prompt.composed_system_prompt()
    assert "Master-Agent вертикали" in prompt.composed_system_prompt()


def test_load_master_prompt_missing_file_raises(tmp_path: Path) -> None:
    (tmp_path / "masters").mkdir()
    with pytest.raises(RolePromptParseError):
        load_master_prompt("nonexistent_vertical", prompts_dir=tmp_path)


def test_real_agency_marketing_master_prompt_is_contract_valid() -> None:
    """The shipped masters/agency_marketing_ru.md obeys the 9-section contract.

    Guards the real artifact via the host-walk resolution (no ROLE_PROMPTS_DIR).
    """
    import os

    if os.environ.get("ROLE_PROMPTS_DIR", "").strip():
        pytest.skip("ROLE_PROMPTS_DIR override active — host-walk not exercised")
    prompt = load_master_prompt("agency_marketing_ru")
    assert prompt.role_id == "master-agency-marketing-ru"
    assert prompt.contract_type == "role-prompt"
    assert len(prompt.sections) == 9
