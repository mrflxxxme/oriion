"""Unit: output-DLP builder + audit adapter (Phase 01.6, ADR-039).

No DB. Validates ``build_output_dlp_screen`` wires the task/cell/workspace
context into the guard, and that ``EmitAuditSink`` maps a block onto
``emit_audit_event`` with the system actor + a value-free payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.runtime.security_guardrails import (
    DLP_BLOCK_ACTION,
    GUARDRAIL_ACTOR_ID,
    EmitAuditSink,
    build_output_dlp_screen,
)
from src.security.exceptions import DlpViolation

VALID_INN10 = "7830002293"


@dataclass
class _FakeSink:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def record_dlp_block(
        self,
        *,
        task_id: UUID,
        cell_id: UUID | None,
        workspace_id: UUID | None,
        categories: tuple[str, ...],
        finding_count: int,
    ) -> None:
        self.calls.append(
            {
                "task_id": task_id,
                "cell_id": cell_id,
                "workspace_id": workspace_id,
                "categories": categories,
                "finding_count": finding_count,
            }
        )


class TestBuilder:
    async def test_clean_text_no_raise_no_audit(self) -> None:
        sink = _FakeSink()
        screen = build_output_dlp_screen(
            session=None,  # type: ignore[arg-type]
            task_id=uuid4(),
            cell_id=uuid4(),
            workspace_id=uuid4(),
            audit=sink,
        )
        await screen("Маркетинговый бриф без ПДн.")
        assert sink.calls == []

    async def test_pii_audits_with_context_and_raises(self) -> None:
        sink = _FakeSink()
        task_id, cell_id, workspace_id = uuid4(), uuid4(), uuid4()
        screen = build_output_dlp_screen(
            session=None,  # type: ignore[arg-type]
            task_id=task_id,
            cell_id=cell_id,
            workspace_id=workspace_id,
            audit=sink,
        )
        with pytest.raises(DlpViolation):
            await screen(f"ИНН {VALID_INN10}")
        assert len(sink.calls) == 1
        call = sink.calls[0]
        assert call["task_id"] == task_id
        assert call["cell_id"] == cell_id
        assert call["workspace_id"] == workspace_id
        assert call["categories"] == ("inn",)


class TestEmitAuditSink:
    async def test_maps_block_to_emit_audit_event(self) -> None:
        captured: dict[str, Any] = {}

        async def _fake_emit(**kwargs: Any) -> None:
            captured.update(kwargs)

        task_id, cell_id, workspace_id = uuid4(), uuid4(), uuid4()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("src.runtime.security_guardrails.emit_audit_event", _fake_emit)
            sink = EmitAuditSink(session="SESSION")  # type: ignore[arg-type]
            await sink.record_dlp_block(
                task_id=task_id,
                cell_id=cell_id,
                workspace_id=workspace_id,
                categories=("inn", "snils"),
                finding_count=2,
            )

        assert captured["action"] == DLP_BLOCK_ACTION
        assert captured["actor_type"] == "system"
        assert captured["actor_id"] == GUARDRAIL_ACTOR_ID
        assert captured["resource_type"] == "task"
        assert captured["resource_id"] == task_id
        assert captured["cell_id"] == cell_id
        assert captured["workspace_id"] == workspace_id
        assert captured["session"] == "SESSION"
        assert captured["payload"] == {"categories": ["inn", "snils"], "finding_count": 2}
