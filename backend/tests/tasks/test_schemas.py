"""Pydantic schemas — round-trip + field validation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.tasks.schemas import (
    TaskArtifactOut,
    TaskCreateRequest,
    TaskOut,
    TaskStepOut,
)


class TestTaskCreateRequest:
    def test_minimal_required_fields(self) -> None:
        req = TaskCreateRequest(title="t", prompt="hello")
        assert req.title == "t"
        assert req.prompt == "hello"
        assert req.description == ""
        assert req.parent_task_id is None

    def test_with_parent_id(self) -> None:
        parent = uuid4()
        req = TaskCreateRequest(title="t", prompt="p", parent_task_id=parent)
        assert req.parent_task_id == parent

    def test_title_max_length(self) -> None:
        with pytest.raises(ValidationError) as exc:
            TaskCreateRequest(title="x" * 256, prompt="p")
        assert "string_too_long" in str(exc.value) or "max_length" in str(exc.value)

    def test_prompt_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskCreateRequest(title="t", prompt="")


class TestTaskOut:
    def test_model_validate_from_attributes(self) -> None:
        class FakeTask:
            id = uuid4()
            cell_id = uuid4()
            parent_task_id = None
            agent_instance_id = None
            initiated_by_user_id = uuid4()
            title = "Demo"
            description = "desc"
            status = "queued"
            priority = 5
            started_at = None
            completed_at = None
            total_cost_credits = Decimal("1.23")
            total_input_tokens = 100
            total_output_tokens = 200
            created_at = datetime.now(UTC)

        out = TaskOut.model_validate(FakeTask())
        assert out.title == "Demo"
        assert out.status == "queued"
        assert out.total_cost_credits == Decimal("1.23")


class TestTaskStepOut:
    def test_jsonb_default_factories(self) -> None:
        step = TaskStepOut(
            id=uuid4(),
            task_id=uuid4(),
            step_index=0,
            agent_archetype_id=uuid4(),
            step_type="coordinator",
            status="succeeded",
            cost_credits=Decimal("0.5"),
            started_at=None,
            completed_at=None,
        )
        assert step.input_jsonb == {}
        assert step.output_jsonb == {}

    def test_jsonb_custom_values(self) -> None:
        step = TaskStepOut(
            id=uuid4(),
            task_id=uuid4(),
            step_index=1,
            agent_archetype_id=uuid4(),
            step_type="researcher",
            status="running",
            cost_credits=Decimal("0"),
            started_at=datetime.now(UTC),
            completed_at=None,
            input_jsonb={"query": "test"},
            output_jsonb={"result": [1, 2, 3]},
        )
        assert step.input_jsonb == {"query": "test"}
        assert step.output_jsonb == {"result": [1, 2, 3]}


class TestTaskArtifactOut:
    def test_content_inline_optional(self) -> None:
        art = TaskArtifactOut(
            id=uuid4(),
            task_id=uuid4(),
            step_id=None,
            artifact_type="brief",
            storage_kind="inline",
            mime_type="text/markdown",
            byte_size=1234,
            content_hash_sha256="a" * 64,
            created_at=datetime.now(UTC),
        )
        assert art.content_inline is None
        assert art.byte_size == 1234

    def test_with_inline_content(self) -> None:
        art = TaskArtifactOut(
            id=uuid4(),
            task_id=uuid4(),
            step_id=uuid4(),
            artifact_type="competitive-matrix",
            storage_kind="inline",
            mime_type="text/markdown",
            byte_size=500,
            content_hash_sha256="b" * 64,
            content_inline={"body": "| col1 | col2 |"},
            created_at=datetime.now(UTC),
        )
        assert art.content_inline == {"body": "| col1 | col2 |"}
