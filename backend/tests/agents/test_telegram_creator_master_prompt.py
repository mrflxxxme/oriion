"""Unit: the shipped telegram_creator Master prompt loads + is contract-valid.

Mirrors ``test_role_prompt_loader_master.py::test_real_agency_marketing_master_prompt_is_contract_valid``
for the second Wave-1 vertical (Phase 01.10). Guards the real artifact at
``contracts/role-prompts/masters/telegram_creator.md`` via the host-walk
resolution used by ``scripts/live_golden_master.py``-style evaluator scripts.
"""

from __future__ import annotations

import os

import pytest
from src.agents.services.role_prompt_loader import load_master_prompt


def test_real_telegram_creator_master_prompt_is_contract_valid() -> None:
    if os.environ.get("ROLE_PROMPTS_DIR", "").strip():
        pytest.skip("ROLE_PROMPTS_DIR override active — host-walk not exercised")
    prompt = load_master_prompt("telegram_creator")
    assert prompt.role_id == "master-telegram-creator"
    assert prompt.contract_type == "role-prompt"
    assert prompt.status == "draft"
    assert prompt.version == "0.1.0"
    assert prompt.model_default == "deepseek-chat"
    assert len(prompt.sections) == 9
    # composed prompt drops the frontmatter.
    composed = prompt.composed_system_prompt()
    assert "role_id:" not in composed
    assert "Master-Agent вертикали «Telegram-крейтор»" in composed
