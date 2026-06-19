"""Unit tests for StrategicContext + its threading into CoordinatorDeps (AC-W1-3).

Covers the Master → Coordinator strategic-brief carrier: validation, the
markdown preamble, and that the new ``CoordinatorDeps`` fields default to
``None`` so the horizontal path is untouched (AC-W1-3.1 / 3.8).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.agents.strategic_context import StrategicContext
from src.agents.tools.delegate import CoordinatorDeps


def test_strategic_context_minimal_fields() -> None:
    sc = StrategicContext(objective="Сделать кампанию", vertical_tag="agency_marketing_ru")
    assert sc.domain_constraints == []
    assert sc.success_criteria == []
    assert sc.parent_task_id is None


def test_strategic_context_rejects_empty_objective() -> None:
    with pytest.raises(ValidationError):
        StrategicContext(objective="", vertical_tag="agency_marketing_ru")


def test_strategic_context_rejects_empty_vertical_tag() -> None:
    with pytest.raises(ValidationError):
        StrategicContext(objective="x", vertical_tag="")


def test_preamble_includes_objective_constraints_and_criteria() -> None:
    sc = StrategicContext(
        objective="Запустить контент-воронку для клиента",
        vertical_tag="agency_marketing_ru",
        domain_constraints=["бюджет ≤ 50к", "только РФ-каналы"],
        success_criteria=["≥3 креатива", "CTA на каждом"],
    )
    preamble = sc.as_coordinator_preamble()
    assert "agency_marketing_ru" in preamble
    assert "Запустить контент-воронку для клиента" in preamble
    assert "бюджет ≤ 50к" in preamble
    assert "только РФ-каналы" in preamble
    assert "≥3 креатива" in preamble
    assert "CTA на каждом" in preamble


def test_preamble_omits_empty_sections() -> None:
    sc = StrategicContext(objective="O", vertical_tag="agency_marketing_ru")
    preamble = sc.as_coordinator_preamble()
    assert "Доменные ограничения" not in preamble
    assert "Критерии успеха" not in preamble


def test_coordinator_deps_defaults_have_no_master_state() -> None:
    """AC-W1-3.1/3.8: the new fields default to None → horizontal path unchanged."""
    deps = CoordinatorDeps(cell_id=uuid4(), task_id=uuid4(), user_id=uuid4())
    assert deps.strategic_context is None
    assert deps.master_recorder is None
