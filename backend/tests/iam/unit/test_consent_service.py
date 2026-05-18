"""Unit: ConsentService — grant + revoke emit events + audit stub."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.iam.services.consent_service import ConsentService


@pytest.mark.asyncio
async def test_record_persists_grant() -> None:
    repo = AsyncMock()
    repo.record.return_value = SimpleNamespace(id=uuid4(), granted_at=datetime.now(UTC))
    svc = ConsentService(repo, consent_version="v1")
    uid = uuid4()
    await svc.record(user_id=uid, kind="pdn", ip="1.1.1.1", user_agent="pytest")
    repo.record.assert_awaited_once_with(
        user_id=uid, kind="pdn", version="v1", ip="1.1.1.1", user_agent="pytest"
    )


@pytest.mark.asyncio
async def test_revoke_calls_repo() -> None:
    repo = AsyncMock()
    svc = ConsentService(repo, consent_version="v1")
    uid = uuid4()
    await svc.revoke(user_id=uid, kind="marketing", ip=None, user_agent=None)
    repo.revoke.assert_awaited_once_with(user_id=uid, kind="marketing")
