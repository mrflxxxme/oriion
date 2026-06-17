"""Integration: multitenancy.provision_cell_schema(uuid) SQL function.

Requires real Postgres with pgvector + migrations applied. Asserts:
  * The function returns a stable schema name (`cell_<uuid_underscored>`).
  * cell_<uuid>.memory_entries table exists with the expected columns.
  * The HNSW index on `embedding` exists.
  * pgvector `<->` query returns neighbors after a sample INSERT (AC5).

Note: the <30s provisioning SLO (AC2) is a perf target, not a correctness
property — a wall-clock assertion here is flaky under CI runner contention, so
it is tracked as a perf SLI elsewhere and intentionally not asserted in this
functional test.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_provision_cell_schema_creates_schema_and_index(
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

    # memory_entries table exists with expected columns.
    cols_result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :s AND table_name = 'memory_entries'"
        ),
        {"s": schema_name},
    )
    cols = {r[0] for r in cols_result.all()}
    assert {
        "id",
        "content",
        "embedding",
        "embedding_provider",
        "embedding_model",
        "embedding_dim",
        "metadata",
        "created_at",
    } <= cols

    # HNSW index present.
    idx_result = await db_session.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = :s AND tablename = 'memory_entries'"
        ),
        {"s": schema_name},
    )
    indexes = {r[0] for r in idx_result.all()}
    assert "memory_entries_embedding_hnsw_idx" in indexes


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


@pytest.mark.asyncio
async def test_pgvector_nearest_neighbor_query(db_session: AsyncSession) -> None:
    """After provisioning, vector ANN search returns rows (AC5 smoke)."""
    cell_id = uuid4()
    res = await db_session.execute(
        text("SELECT multitenancy.provision_cell_schema(:c)"),
        {"c": str(cell_id)},
    )
    schema_name = res.scalar()

    # Insert two rows with 1024-dim unit-like embeddings. NOTE: pgvector's
    # cosine distance is undefined for zero vectors (||v|| = 0) — they're
    # silently excluded from ANN results. So each row must have non-zero
    # magnitude; we set the i-th component to 1.0 and leave the rest at 0.0.
    for i in (0, 1):
        vec = ", ".join(["1.0" if j == i else "0.0" for j in range(1024)])
        await db_session.execute(
            text(
                f'INSERT INTO "{schema_name}".memory_entries '
                "(content, embedding, embedding_provider, embedding_model, embedding_dim) "
                f"VALUES (:c, '[{vec}]'::vector, 'test', 'test', 1024)"
            ),
            {"c": f"row-{i}"},
        )

    # ANN ordering on the cosine operator. Query vector matches row-1 exactly.
    query_vec = ", ".join(["1.0" if j == 1 else "0.0" for j in range(1024)])
    res = await db_session.execute(
        text(
            f'SELECT content FROM "{schema_name}".memory_entries '
            f"ORDER BY embedding <=> '[{query_vec}]'::vector LIMIT 2"
        )
    )
    rows = [r[0] for r in res.all()]
    assert len(rows) == 2
    # The vector matching exactly should come first.
    assert rows[0] == "row-1"
