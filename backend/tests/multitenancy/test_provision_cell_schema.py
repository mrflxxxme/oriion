"""Integration: multitenancy.provision_cell_schema(uuid) SQL function.

Requires real Postgres with migrations applied. Since Phase 01.4 (ADR-011
Wave-1) memory lives in a single `memory` schema (RLS by cell_id), so the
provisioner creates ONLY an empty `cell_<uuid>` schema — the dead per-cell
`memory_entries` placeholder was removed (migration
`multitenancy/0006_provision_cell_schema_drop_memory`). Asserts:
  * the function returns a stable schema name (`cell_<uuid_underscored>`);
  * the schema exists but carries NO `memory_entries` table;
  * the function stays idempotent.

The pgvector ANN smoke now lives against the single `memory` schema in
`tests/memory/test_memory_integration.py` (embedding round-trip).

Note: the <30s provisioning SLO (AC2) is a perf target, not a correctness
property — tracked as a perf SLI elsewhere, intentionally not asserted here.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_provision_cell_schema_creates_empty_schema(
    db_session: AsyncSession,
) -> None:
    cell_id = uuid4()
    expected_schema = f"cell_{str(cell_id).replace('-', '_')}"

    result = await db_session.execute(
        text("SELECT multitenancy.provision_cell_schema(:cell_id)"),
        {"cell_id": str(cell_id)},
    )
    schema_name = result.scalar()
    assert schema_name == expected_schema

    # The schema exists ...
    schema_exists = await db_session.execute(
        text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
        {"s": schema_name},
    )
    assert schema_exists.scalar() == 1

    # ... but the dead per-cell memory_entries placeholder is NOT created.
    cols_result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = 'memory_entries'"
        ),
        {"s": schema_name},
    )
    assert cols_result.first() is None, "per-cell memory_entries should no longer be provisioned"


@pytest.mark.asyncio
async def test_provision_cell_schema_idempotent(db_session: AsyncSession) -> None:
    cell_id = uuid4()
    r1 = await db_session.execute(
        text("SELECT multitenancy.provision_cell_schema(:c)"),
        {"c": str(cell_id)},
    )
    r2 = await db_session.execute(
        text("SELECT multitenancy.provision_cell_schema(:c)"),
        {"c": str(cell_id)},
    )
    assert r1.scalar() == r2.scalar()
