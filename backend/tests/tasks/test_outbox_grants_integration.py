"""Regression: tasks.outbox grants the app role write + drain privileges.

Audit P3 (2026-06-18): migration 0005 created ``tasks.outbox`` without granting
``oriion_app`` any privileges, so the web-tier outbox WRITE and the relay drain
would fail "permission denied" in production. Migration 0006 adds the grant.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration


async def test_oriion_app_can_write_and_drain_outbox(db_engine: AsyncEngine) -> None:
    """As ``oriion_app``: INSERT (web write) + SELECT/UPDATE (relay drain) must all
    succeed. Fails "permission denied" without the 0006 grant. Rolled back so the
    probe row never leaks into the shared container."""
    ce_id = uuid4()
    async with db_engine.connect() as conn:
        tx = await conn.begin()
        try:
            await conn.execute(text("SET LOCAL ROLE oriion_app"))
            # Web-tier write path.
            await conn.execute(
                text(
                    "INSERT INTO tasks.outbox (ce_id, ce_type, ce_source, data) "
                    "VALUES (:cid, 'oriion.tasks.created.v1', "
                    "'oriion://contexts/tasks', '{}'::jsonb)"
                ),
                {"cid": str(ce_id)},
            )
            # Relay drain path: read the unpublished row + stamp published_at.
            ce_type = (
                await conn.execute(
                    text("SELECT ce_type FROM tasks.outbox WHERE ce_id = :cid"),
                    {"cid": str(ce_id)},
                )
            ).scalar_one()
            assert ce_type == "oriion.tasks.created.v1"
            await conn.execute(
                text("UPDATE tasks.outbox SET published_at = now() WHERE ce_id = :cid"),
                {"cid": str(ce_id)},
            )
        finally:
            await tx.rollback()
