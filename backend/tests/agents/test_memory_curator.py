"""Unit tests for the memory-curator agents-layer (Phase 01.4b).

Covers the pure schemas + factories + router role wiring. The orchestration
behaviour (should_remember → entries, billing-as-step) is exercised against the
runtime ``MemoryExtractor`` in ``tests/runtime/test_memory_extraction.py``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.agents.memory_curator import (
    ROLE_KEY_MEMORY_FILTER,
    ROLE_KEY_MEMORY_SUMMARY,
    MemoryExtraction,
    MemoryExtractionEntry,
    build_conversation_summarizer_agent,
    build_memory_extraction_agent,
)
from src.llm_gateway.services.router_service import ROLE_TO_MODEL, resolve_max_tokens

from tests._fixtures.canned_pydantic_ai.fake_model import FakeLLMGatewayModel


def test_build_curator_agents_smoke() -> None:
    """Both factories construct against a fake model (no network)."""
    filter_agent = build_memory_extraction_agent(model=FakeLLMGatewayModel(ROLE_KEY_MEMORY_FILTER))
    summary_agent = build_conversation_summarizer_agent(
        model=FakeLLMGatewayModel(ROLE_KEY_MEMORY_SUMMARY)
    )
    assert filter_agent is not None
    assert summary_agent is not None


def test_memory_extraction_defaults_to_no_op() -> None:
    """The common case: nothing worth remembering → empty, falsey verdict."""
    verdict = MemoryExtraction()
    assert verdict.should_remember is False
    assert verdict.entries == []


def test_memory_extraction_entry_defaults_kind_fact() -> None:
    entry = MemoryExtractionEntry(content="Клиент работает на рынке РФ.")
    assert entry.kind == "fact"
    assert entry.title is None
    assert entry.tags == []


def test_memory_extraction_entry_rejects_empty_content() -> None:
    """content is the payload — an empty string is a parse error (PromptedOutput
    retries), never a blank memory row."""
    with pytest.raises(ValidationError):
        MemoryExtractionEntry(content="")


def test_memory_extraction_entry_rejects_unknown_kind() -> None:
    """kind is Literal-constrained to the cell-memory CHECK values (minus the
    summarizer-only 'conversation_summary')."""
    with pytest.raises(ValidationError):
        MemoryExtractionEntry(content="x", kind="conversation_summary")  # type: ignore[arg-type]


def test_curator_roles_route_to_lite_deepseek_chat() -> None:
    """Both curator roles map to the lite deepseek-chat tier with a small budget."""
    assert ROLE_TO_MODEL[ROLE_KEY_MEMORY_FILTER] == ("deepseek", "deepseek-chat")
    assert ROLE_TO_MODEL[ROLE_KEY_MEMORY_SUMMARY] == ("deepseek", "deepseek-chat")
    assert resolve_max_tokens(ROLE_KEY_MEMORY_FILTER) == 1024
    assert resolve_max_tokens(ROLE_KEY_MEMORY_SUMMARY) == 1024
