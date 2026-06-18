"""Unit: agents routers (handlers called directly with stubbed session/service)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from src.agents.models import AgentArchetype, AgentInstance, TeamPreset
from src.agents.routers import archetypes as archetypes_router
from src.agents.routers import instances as instances_router
from src.agents.routers import teams as teams_router
from src.agents.schemas import TeamProvisionRequest
from src.agents.services.archetype_service import ArchetypeService
from src.agents.services.team_provisioning_service import TeamProvisioningService

from tests.agents._session_stub import Result, StubSession


def _full_archetype() -> AgentArchetype:
    arc = AgentArchetype(
        slug="researcher",
        vertical_slug="horizontal",
        display_name="Исследователь",
        role_category="researcher",
        prompt_version="0.1.0",
        model_provider_slug="deepseek",
        model_name="deepseek-chat",
        tools_allowed=["web_search"],
    )
    arc.id = uuid4()
    arc.model_fallback = None
    arc.is_active = True
    arc.status = "draft"
    return arc


def _full_instance(cell_id: UUID) -> AgentInstance:
    inst = AgentInstance(cell_id=cell_id, agent_archetype_id=uuid4())
    inst.id = uuid4()
    inst.custom_name = None
    inst.custom_settings_jsonb = {}
    inst.total_tasks_completed = 0
    inst.last_used_at = None
    inst.created_at = datetime.now(UTC)
    inst.archived_at = None
    return inst


class _FakeArchetypeService:
    def __init__(self, rows: list[AgentArchetype]) -> None:
        self._rows = rows
        self.called_with: str | None = None

    async def list_active(self, *, vertical_slug: str | None = None) -> list[AgentArchetype]:
        self.called_with = vertical_slug
        return self._rows


class _FakeProvisioningService:
    def __init__(self, instances: list[AgentInstance]) -> None:
        self._instances = instances

    async def provision_team(
        self, *, preset_slug: str, cell_id: UUID, user_id: UUID
    ) -> list[AgentInstance]:
        return self._instances


@pytest.mark.asyncio
async def test_list_archetypes_handler() -> None:
    service = _FakeArchetypeService([_full_archetype()])
    out = await archetypes_router.list_archetypes(
        vertical_slug="horizontal",
        service=service,  # type: ignore[arg-type]
    )
    assert len(out) == 1
    assert out[0].slug == "researcher"
    assert service.called_with == "horizontal"


def test_get_archetype_service_factory() -> None:
    svc = archetypes_router.get_archetype_service(db=StubSession())  # type: ignore[arg-type]
    assert isinstance(svc, ArchetypeService)


@pytest.mark.asyncio
async def test_list_cell_agents_handler() -> None:
    cell_id = uuid4()
    session = StubSession(results=[Result(scalar_list=[_full_instance(cell_id)])])
    out = await instances_router.list_cell_agents(cell_id=cell_id, db=session)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].cell_id == cell_id


@pytest.mark.asyncio
async def test_provision_team_handler() -> None:
    cell_id = uuid4()
    instances = [_full_instance(cell_id)]
    preset = TeamPreset(
        vertical_slug="horizontal",
        slug="productivity-core",
        display_name="Твои личные ассистенты",
        archetype_ids=[uuid4()],
    )
    preset.id = uuid4()
    session = StubSession(results=[Result(scalar=preset)])
    auth = SimpleNamespace(user=SimpleNamespace(id=uuid4()))

    resp = await teams_router.provision_team(
        cell_id=cell_id,
        payload=TeamProvisionRequest(preset_key="productivity-core"),
        db=session,  # type: ignore[arg-type]
        auth=auth,  # type: ignore[arg-type]
        service=_FakeProvisioningService(instances),  # type: ignore[arg-type]
    )
    assert resp.cell_id == cell_id
    assert resp.team_preset_id == preset.id
    assert len(resp.agent_instances) == 1


def test_get_team_provisioning_service_factory() -> None:
    svc = teams_router.get_team_provisioning_service(db=StubSession())  # type: ignore[arg-type]
    assert isinstance(svc, TeamProvisioningService)
