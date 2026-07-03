"""Cell-scoped RLS + updated_at boilerplate for migrations (house pattern).

Why this exists (ADR-037 D2, grill 2026-07-03): the tripwire content-classifier
auto-merges a migration only when its ``upgrade()`` is a **statically provable**
pure-greenfield CREATE. The historical idiom — an ``f"ALTER TABLE {tbl} ..."``
loop — is NOT statically provable (``{tbl}`` is a variable), so such migrations
keep the founder ack. Calling these helpers with **literal** table names instead
keeps the migration body f-string-free, so a pure-CREATE migration can be
recognized and auto-merged. The f-strings live HERE (tested, trusted code), not
in the migration.

Emit exactly what memory/billing/artifacts migrations emit by hand:
  cell_scoped_rls(op, "artifacts.foo")     -> ENABLE + FORCE RLS + cell policy
  updated_at_trigger(op, "artifacts.foo")  -> BEFORE UPDATE trigger via _shared

Table names are trusted literals supplied by the migration author; these helpers
never take user/runtime input.
"""

from __future__ import annotations

from alembic import op


def _leaf(table: str) -> str:
    """`schema.table` -> `table` for deriving trigger/policy names."""
    return table.rsplit(".", 1)[-1]


def cell_scoped_rls(table: str, *, policy: str | None = None) -> None:
    """ENABLE + FORCE ROW LEVEL SECURITY + a `cell_id = current_cell_id()` policy.

    Mirrors the house direct-predicate policy (USING + WITH CHECK) used across
    memory/billing/artifacts. ``policy`` defaults to ``<table>_cell_isolation``.
    """
    policy_name = policy or f"{_leaf(table)}_cell_isolation"
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY {policy_name} ON {table}
            USING (cell_id = _shared.current_cell_id())
            WITH CHECK (cell_id = _shared.current_cell_id());
        """
    )


def updated_at_trigger(table: str, *, name: str | None = None) -> None:
    """BEFORE UPDATE trigger calling ``_shared.set_updated_at()`` (house helper)."""
    trigger = name or f"{_leaf(table)}_set_updated_at"
    op.execute(
        f"""
        CREATE TRIGGER {trigger}
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )
