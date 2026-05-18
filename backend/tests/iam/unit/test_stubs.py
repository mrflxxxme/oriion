"""Unit: _stubs.multitenancy + _stubs.audit signatures (replaced in 00.2.5)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from src._stubs.audit import emit_audit_event
from src._stubs.multitenancy import provision_initial_workspace


@pytest.mark.asyncio
async def test_multitenancy_stub_deterministic() -> None:
    uid = uuid4()
    a = await provision_initial_workspace(uid)
    b = await provision_initial_workspace(uid)
    assert a.workspace_id == b.workspace_id
    assert a.cell_id == b.cell_id


@pytest.mark.asyncio
async def test_multitenancy_stub_unique_per_user() -> None:
    a = await provision_initial_workspace(uuid4())
    b = await provision_initial_workspace(uuid4())
    assert a.workspace_id != b.workspace_id


@pytest.mark.asyncio
async def test_audit_stub_accepts_full_signature() -> None:
    await emit_audit_event(
        actor_type="user",
        actor_id=uuid4(),
        action="iam.user.registered",
        resource_type="user",
        resource_id=uuid4(),
        payload={"foo": "bar"},
        ip="1.2.3.4",
        user_agent="pytest",
    )
    # Minimal — actor only
    await emit_audit_event(
        actor_type="system",
        actor_id=uuid4(),
        action="iam.test",
        resource_type="x",
    )
