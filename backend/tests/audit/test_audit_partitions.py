"""Integration: audit.audit_log has the expected monthly partitions (AC7).

Asserts the parent table is RANGE-partitioned and the seed partitions
(audit_log_2026_05, audit_log_2026_06) plus the DEFAULT catch-all
(audit_log_default) all attach to it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_is_range_partitioned(db_session: AsyncSession) -> None:
    """pg_partitioned_table confirms parent is partitioned, strategy 'r' (range)."""
    # pg_partitioned_table.partstrat is `"char"` — asyncpg surfaces this as
    # `bytes` (a single byte), so we cast to text in SQL for a portable
    # string comparison.
    result = await db_session.execute(
        text(
            """
            SELECT partstrat::text
              FROM pg_partitioned_table pt
              JOIN pg_class c ON c.oid = pt.partrelid
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'audit'
               AND c.relname = 'audit_log'
            """
        )
    )
    rows = result.all()
    assert len(rows) == 1, "audit.audit_log must be a partitioned table"
    assert rows[0][0] == "r", "expected RANGE partitioning strategy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_has_seed_partitions(db_session: AsyncSession) -> None:
    """pg_inherits confirms 2026_05, 2026_06, default partitions exist."""
    result = await db_session.execute(
        text(
            """
            SELECT child.relname
              FROM pg_inherits
              JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
              JOIN pg_class child  ON child.oid  = pg_inherits.inhrelid
              JOIN pg_namespace pn ON pn.oid = parent.relnamespace
             WHERE pn.nspname = 'audit'
               AND parent.relname = 'audit_log'
            """
        )
    )
    children = {row[0] for row in result.all()}
    assert {
        "audit_log_2026_05",
        "audit_log_2026_06",
        "audit_log_default",
    } <= children, f"missing seed partitions; got {children}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_log_default_partition_is_default(
    db_session: AsyncSession,
) -> None:
    """audit_log_default is the DEFAULT partition (catch-all)."""
    result = await db_session.execute(
        text(
            """
            SELECT pg_get_expr(c.relpartbound, c.oid)
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'audit'
               AND c.relname = 'audit_log_default'
            """
        )
    )
    rows = result.all()
    assert len(rows) == 1
    assert rows[0][0] == "DEFAULT"
