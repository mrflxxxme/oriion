"""Row-Level Security context-setter for the 3-GUC tenant model.

Per ADR-009 amendment 2026-05-19 the application sets THREE Postgres session
locals on every tenant-scoped transaction so downstream contexts can pick the
GUC matching their filter granularity:

    SET LOCAL app.current_user_id      = '<uuid>';
    SET LOCAL app.current_workspace_id = '<uuid>';
    SET LOCAL app.current_cell_id      = '<uuid>';

Each Postgres `SET LOCAL` resets at transaction end — `set_tenant_context`
relies on the caller's outer transaction (SQLAlchemy session) for cleanup.

Used by:
    * FastAPI dependency `get_tenant_db_session` (this module).
    * Phase 00.4 LLM gateway request handlers (workspace-scoped queries).
    * Phase 00.3 multitenancy + audit services.
    * Integration tests (`backend/tests/_shared/test_rls.py`).

Default-deny posture: missing GUC → `_shared.current_user_id()` returns NULL
→ all multitenancy + per-cell RLS policies evaluate FALSE → zero rows visible.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["set_tenant_context", "clear_tenant_context"]


@asynccontextmanager
async def set_tenant_context(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    cell_id: UUID,
    user_id: UUID,
) -> AsyncIterator[AsyncSession]:
    """Bind the three RLS GUCs to the current Postgres session-local config.

    Usage::

        async with set_tenant_context(
            session,
            workspace_id=workspace.id,
            cell_id=cell.id,
            user_id=user.id,
        ) as s:
            await s.execute(select(Task))   # RLS filters by cell_id automatically

    The three keyword-only args make accidental positional misuse impossible
    (e.g. swapping workspace_id and cell_id is a security-grade bug).

    Postgres `SET LOCAL` is bound to the current transaction; on commit /
    rollback the values are dropped automatically. No explicit RESET needed.
    """
    # Postgres `SET LOCAL <name> = <value>` does NOT accept bound parameters —
    # the statement is parsed lexically without prepared-statement substitution.
    # We use `set_config(name, value, is_local := true)` instead: a function
    # call that DOES accept parameters and has the same per-transaction
    # session-local semantics as SET LOCAL.
    await session.execute(
        text("SELECT set_config('app.current_user_id', :u, true)"),
        {"u": str(user_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :w, true)"),
        {"w": str(workspace_id)},
    )
    await session.execute(
        text("SELECT set_config('app.current_cell_id', :c, true)"),
        {"c": str(cell_id)},
    )
    try:
        yield session
    finally:
        # Postgres `SET LOCAL` auto-resets at transaction end. Nothing to do.
        pass


async def clear_tenant_context(session: AsyncSession) -> None:
    """Explicitly unset all three GUCs to NULL within the current transaction.

    Use in tests that want to assert default-deny posture (missing GUC → no
    rows) within a single transaction without rolling back.
    """
    await session.execute(text("SELECT set_config('app.current_user_id', '', true)"))
    await session.execute(text("SELECT set_config('app.current_workspace_id', '', true)"))
    await session.execute(text("SELECT set_config('app.current_cell_id', '', true)"))
