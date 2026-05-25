"""FastAPI router smoke — POST/GET/cancel + SSE stream endpoint.

Uses FastAPI TestClient + dependency_overrides so real DB/auth aren't
needed. Covers src/tasks/routers/tasks.py + src/tasks/routers/stream.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src._shared.middleware.tenant_context import get_tenant_db_session
from src.iam.middleware import AuthenticatedUser, get_current_user
from src.tasks.models import Task
from src.tasks.routers.stream import router as stream_router
from src.tasks.routers.tasks import get_task_service
from src.tasks.routers.tasks import router as tasks_router


@dataclass
class _FakeUser:
    id: Any
    email: str = "test@example.com"
    is_email_verified: bool = True


def _build_fake_task(task_id: Any, cell_id: Any, user_id: Any) -> Task:
    t = Task(
        cell_id=cell_id,
        initiated_by_user_id=user_id,
        title="Fake task",
        description="",
        status="queued",
        priority=5,
        input_jsonb={"prompt": "hi"},
    )
    t.id = task_id
    t.parent_task_id = None
    t.agent_instance_id = None
    t.started_at = None
    t.completed_at = None
    t.total_cost_credits = Decimal(0)
    t.total_input_tokens = 0
    t.total_output_tokens = 0
    t.created_at = datetime.now(UTC)
    return t


class _FakeTaskService:
    """Minimal TaskService stub — only the methods routers invoke."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.cancelled: list[Any] = []
        self.next_task: Task | None = None

    async def create_task(self, **kwargs: Any) -> Task:
        self.created.append(kwargs)
        task = _build_fake_task(uuid4(), kwargs["cell_id"], kwargs["user_id"])
        task.title = kwargs["title"]
        task.description = kwargs["description"]
        task.input_jsonb = {"prompt": kwargs["prompt"]}
        return task

    async def get_task(self, task_id: Any) -> Task:
        return self.next_task or _build_fake_task(task_id, uuid4(), uuid4())

    async def cancel_task(self, task_id: Any) -> list[Any]:
        self.cancelled.append(task_id)
        return [uuid4(), uuid4()]  # 2 fake descendants


@pytest.fixture
def fake_user() -> _FakeUser:
    return _FakeUser(id=uuid4())


@pytest.fixture
def fake_service() -> _FakeTaskService:
    return _FakeTaskService()


@pytest.fixture
def app(fake_user: _FakeUser, fake_service: _FakeTaskService) -> FastAPI:
    a = FastAPI()
    a.include_router(tasks_router, prefix="/api/v1")
    a.include_router(stream_router, prefix="/api/v1")

    async def _override_user() -> AuthenticatedUser:
        # AuthenticatedUser is a frozen dataclass — provide both `claims`
        # and `user`. Routers only read .user.id, so a MagicMock satisfies
        # the claims slot without constructing a full AccessTokenClaims.
        return AuthenticatedUser(claims=MagicMock(), user=fake_user)  # type: ignore[arg-type]

    async def _override_db() -> AsyncIterator[Any]:
        # Unused — get_task_service is also overridden so this never
        # actually runs. Kept for completeness.
        yield None

    a.dependency_overrides[get_current_user] = _override_user
    a.dependency_overrides[get_tenant_db_session] = _override_db
    a.dependency_overrides[get_task_service] = lambda: fake_service
    return a


def test_create_task_returns_202(app: FastAPI, fake_service: _FakeTaskService) -> None:
    client = TestClient(app)
    cell_id = uuid4()
    r = client.post(
        f"/api/v1/cells/{cell_id}/tasks",
        json={"title": "Demo", "description": "d", "prompt": "hello"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["title"] == "Demo"
    assert body["status"] == "queued"
    assert fake_service.created[0]["cell_id"] == cell_id
    assert fake_service.created[0]["prompt"] == "hello"


def test_get_task_returns_200(app: FastAPI, fake_service: _FakeTaskService) -> None:
    client = TestClient(app)
    cell_id, task_id = uuid4(), uuid4()
    r = client.get(f"/api/v1/cells/{cell_id}/tasks/{task_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(task_id)


def test_cancel_task_returns_202_with_cascade(app: FastAPI, fake_service: _FakeTaskService) -> None:
    client = TestClient(app)
    cell_id, task_id = uuid4(), uuid4()
    r = client.post(f"/api/v1/cells/{cell_id}/tasks/{task_id}/cancel")
    assert r.status_code == 202
    body = r.json()
    assert body["task_id"] == str(task_id)
    assert body["status"] == "cancelled"
    assert len(body["cascaded_to"]) == 2  # _FakeTaskService returns 2
    assert fake_service.cancelled == [task_id]


def test_stream_endpoint_mounted_in_app(app: FastAPI) -> None:
    """SSE endpoint plumbing — verify route registered (don't subscribe;
    that would block because no publisher events fire in this unit test).

    Full SSE event-order assertion lives in tests/agents/test_market_brief_
    demo_flow.py (the demo-flow integration test) where the orchestrator
    actually emits events. Here we just confirm the route plugs into the
    app's router tree under the expected prefix.
    """
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/v1/cells/{cell_id}/tasks/{task_id}/stream" in routes
