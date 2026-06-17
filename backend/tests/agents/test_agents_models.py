"""Unit: agents SQLAlchemy models construct + map to canonical table names."""

from __future__ import annotations

from uuid import uuid4

from src.agents.models import AgentArchetype, AgentInstance, TeamPreset


def test_agent_archetype_constructs() -> None:
    arc = AgentArchetype(
        slug="researcher",
        vertical_slug="horizontal",
        display_name="Исследователь",
        role_category="researcher",
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=["web_search", "read_url"],
    )
    assert arc.__tablename__ == "agent_archetypes"
    assert arc.__table_args__[-1] == {"schema": "agents"}
    assert arc.slug == "researcher"
    assert arc.tools_allowed == ["web_search", "read_url"]


def test_team_preset_constructs() -> None:
    preset = TeamPreset(
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="Твои личные ассистенты",
        archetype_ids=[uuid4(), uuid4()],
    )
    assert preset.__tablename__ == "team_presets"
    assert len(preset.archetype_ids) == 2


def test_agent_instance_constructs() -> None:
    inst = AgentInstance(cell_id=uuid4(), agent_archetype_id=uuid4())
    assert inst.__tablename__ == "agent_instances"
    assert inst.cell_id is not None
