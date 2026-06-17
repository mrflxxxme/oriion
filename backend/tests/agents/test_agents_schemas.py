"""Unit: agents bounded-context Pydantic schemas (AC-W1-17 coverage)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.agents.schemas import (
    AgentArchetypeOut,
    AgentInstanceOut,
    TeamPresetOut,
    TeamProvisionRequest,
    TeamProvisionResponse,
)


def test_agent_archetype_out_from_attributes() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        slug="researcher",
        vertical_slug="horizontal",
        display_name="Исследователь",
        role_category="researcher",
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        model_fallback=None,
        tools_allowed=["web_search", "read_url"],
        is_active=True,
        status="draft",
    )
    out = AgentArchetypeOut.model_validate(row)
    assert out.slug == "researcher"
    assert out.tools_allowed == ["web_search", "read_url"]
    assert out.is_active is True


def test_agent_instance_out_from_attributes() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        cell_id=uuid4(),
        agent_archetype_id=uuid4(),
        custom_name=None,
        custom_settings_jsonb={"k": "v"},
        total_tasks_completed=3,
        last_used_at=None,
        created_at=datetime.now(UTC),
        archived_at=None,
    )
    out = AgentInstanceOut.model_validate(row)
    assert out.total_tasks_completed == 3
    assert out.custom_settings_jsonb == {"k": "v"}


def test_team_preset_out_from_attributes() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="Твои личные ассистенты",
        description="desc",
        archetype_ids=[uuid4(), uuid4()],
        default_workflow_dag_json={"nodes": []},
    )
    out = TeamPresetOut.model_validate(row)
    assert out.slug == "productivity-core"
    assert len(out.archetype_ids) == 2


def test_team_provision_request_and_response() -> None:
    req = TeamProvisionRequest(preset_key="productivity-core")
    assert req.preset_key == "productivity-core"

    resp = TeamProvisionResponse(
        team_preset_id=uuid4(),
        cell_id=uuid4(),
        agent_instances=[],
    )
    assert resp.agent_instances == []
