"""Unit: agents CloudEvents emitters emit the right ce_type + data shape."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from src.agents import events


@pytest.mark.asyncio
async def test_emit_team_provisioned_shape() -> None:
    cell_id, preset_id, user_id = uuid4(), uuid4(), uuid4()
    instance_ids = [uuid4(), uuid4()]
    with patch.object(events, "emit_cloudevent", new=AsyncMock()) as emit:
        await events.emit_team_provisioned(
            cell_id=cell_id,
            team_preset_id=preset_id,
            preset_slug="productivity-core",
            agent_instance_ids=instance_ids,
            provisioned_by_user_id=user_id,
        )
    emit.assert_awaited_once()
    kwargs: dict[str, Any] = emit.await_args.kwargs
    assert kwargs["ce_type"] == "oriion.agents.team_provisioned.v1"
    assert kwargs["data"]["preset_slug"] == "productivity-core"
    assert kwargs["data"]["agent_instance_ids"] == [str(x) for x in instance_ids]


@pytest.mark.asyncio
async def test_emit_instance_created_shape() -> None:
    with patch.object(events, "emit_cloudevent", new=AsyncMock()) as emit:
        await events.emit_instance_created(
            agent_instance_id=uuid4(),
            cell_id=uuid4(),
            agent_archetype_id=uuid4(),
            archetype_slug="researcher",
        )
    emit.assert_awaited_once()
    assert emit.await_args.kwargs["ce_type"] == "oriion.agents.instance_created.v1"
    assert emit.await_args.kwargs["data"]["archetype_slug"] == "researcher"
