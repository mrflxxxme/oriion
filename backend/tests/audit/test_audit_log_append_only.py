"""Integration: audit.audit_log is append-only via trigger.

Requires the docker-compose Postgres stack (oriion_test DB with the audit
schema migration applied). Run with::

    pytest -m integration tests/audit/test_audit_log_append_only.py
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_update_is_blocked_by_trigger(
    db_session: AsyncSession,
) -> None:
    """UPDATE on audit.audit_log raises EXCEPTION via deny_update_delete()."""
    actor_id = uuid4()
    # Insert a row inside the test transaction.
    await db_session.execute(
        text(
            "INSERT INTO audit.audit_log (actor_type, actor_id, action) "
            "VALUES ('system', :aid, 'test.action')"
        ),
        {"aid": str(actor_id)},
    )

    # Any UPDATE must raise — wrapped by SQLAlchemy as DBAPIError/IntegrityError.
    with pytest.raises((DBAPIError, IntegrityError)) as excinfo:
        await db_session.execute(
            text("UPDATE audit.audit_log SET action='hijacked' " "WHERE actor_id = :aid"),
            {"aid": str(actor_id)},
        )
    assert "append-only" in str(excinfo.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_delete_is_blocked_by_trigger(
    db_session: AsyncSession,
) -> None:
    """DELETE on audit.audit_log raises EXCEPTION via deny_update_delete()."""
    actor_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO audit.audit_log (actor_type, actor_id, action) "
            "VALUES ('system', :aid, 'test.delete')"
        ),
        {"aid": str(actor_id)},
    )

    with pytest.raises((DBAPIError, IntegrityError)) as excinfo:
        await db_session.execute(
            text("DELETE FROM audit.audit_log WHERE actor_id = :aid"),
            {"aid": str(actor_id)},
        )
    assert "append-only" in str(excinfo.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_insert_succeeds(db_session: AsyncSession) -> None:
    """Sanity: the trigger only blocks UPDATE/DELETE, INSERT works fine."""
    actor_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO audit.audit_log "
            "(actor_type, actor_id, action, resource_type, payload) "
            "VALUES ('user', :aid, 'iam.test', 'user', '{\"k\":\"v\"}'::jsonb)"
        ),
        {"aid": str(actor_id)},
    )
    result = await db_session.execute(
        text("SELECT action, payload FROM audit.audit_log " "WHERE actor_id = :aid"),
        {"aid": str(actor_id)},
    )
    rows = result.all()
    assert len(rows) == 1
    assert rows[0][0] == "iam.test"
