"""db_migrations content-downgrade — fail-closed pure-CREATE detection (ADR-037 D2).

The v2 tripwire auto-merges a migration whose upgrade() is a pure greenfield
CREATE, but must keep the ack for ANY existing-object surgery / backfill /
dynamic SQL. These tests pin BOTH classes: a real pure-CREATE downgrades, every
risky shape stays acked, and a mixed batch stays acked.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "autonomy" / "classify_tripwire.py"

_spec = importlib.util.spec_from_file_location("classify_tripwire", SCRIPT)
assert _spec is not None and _spec.loader is not None
ct = importlib.util.module_from_spec(_spec)
sys.modules["classify_tripwire"] = ct
_spec.loader.exec_module(ct)


PURE_CREATE = '''
def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS artifacts;")
    op.execute("""
        CREATE TABLE artifacts.artifacts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cell_id uuid NOT NULL REFERENCES multitenancy.cells(id) ON DELETE CASCADE,
            title text NOT NULL
        );
    """)
    op.execute("CREATE INDEX ix_art_cell ON artifacts.artifacts (cell_id, created_at DESC);")
    op.execute("ALTER TABLE artifacts.artifacts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE artifacts.artifacts FORCE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY p ON artifacts.artifacts USING (cell_id = _shared.current_cell_id());")
    op.execute("GRANT SELECT, INSERT ON artifacts.artifacts TO oriion_app;")

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS artifacts.artifacts;")
'''

ADD_COLUMN = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.foo (id uuid PRIMARY KEY);")
    op.execute("ALTER TABLE artifacts.artifacts ADD COLUMN visibility text DEFAULT 'cell-shared';")
def downgrade() -> None:
    op.execute("DROP TABLE artifacts.foo;")
'''

BACKFILL = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.bar (id uuid PRIMARY KEY);")
    op.execute("UPDATE tasks.tasks SET status = 'migrated' WHERE status IS NULL;")
'''

INDEX_ON_EXISTING = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.baz (id uuid PRIMARY KEY);")
    op.execute("CREATE INDEX ix_hot ON tasks.tasks (created_at);")
'''

DYNAMIC = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.qux (id uuid PRIMARY KEY);")
    op.execute(f"CREATE INDEX ix_{name} ON artifacts.qux (id);")
'''

OP_ADD_COLUMN = '''
def upgrade() -> None:
    op.create_table("newt", sa.Column("id", sa.Uuid, primary_key=True))
    op.add_column("existing", sa.Column("c", sa.Text))
'''

CREATES_NOTHING = '''
def upgrade() -> None:
    op.execute("GRANT SELECT ON tasks.tasks TO oriion_app;")
'''

# The new house idiom (grill option C): literal table names + RLS helpers, no
# f-strings -> statically provable pure-CREATE.
HELPER_MIGRATION = '''
from migrations._rls import cell_scoped_rls, updated_at_trigger

def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.foo (id uuid PRIMARY KEY, cell_id uuid NOT NULL);")
    op.execute("CREATE INDEX ix_foo ON artifacts.foo (cell_id);")
    cell_scoped_rls("artifacts.foo")
    updated_at_trigger("artifacts.foo")
    op.execute("GRANT SELECT, INSERT ON artifacts.foo TO oriion_app;")

def downgrade() -> None:
    op.execute("DROP TABLE artifacts.foo;")
'''

# Same but the helper name is NOT imported from the known module -> spoof guard.
HELPER_NO_IMPORT = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.foo (id uuid PRIMARY KEY);")
    cell_scoped_rls("artifacts.foo")
'''

# An unrecognized call could hide surgery in its own body -> fail-closed ack.
UNKNOWN_CALL = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.foo (id uuid PRIMARY KEY);")
    do_something_sneaky(op, "existing")
'''

# The historical f-string RLS loop (real house style pre-option-C) -> ack.
FSTRING_LOOP = '''
def upgrade() -> None:
    op.execute("CREATE TABLE artifacts.foo (id uuid PRIMARY KEY);")
    for tbl in ("artifacts.foo",):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
'''


def test_helper_migration_is_pure_create() -> None:
    assert ct.migration_is_pure_create(HELPER_MIGRATION) is True


def test_helper_without_import_is_acked() -> None:
    assert ct.migration_is_pure_create(HELPER_NO_IMPORT) is False


def test_unknown_call_is_acked() -> None:
    assert ct.migration_is_pure_create(UNKNOWN_CALL) is False


def test_fstring_loop_is_acked() -> None:
    assert ct.migration_is_pure_create(FSTRING_LOOP) is False


def test_pure_create_is_downgraded() -> None:
    assert ct.migration_is_pure_create(PURE_CREATE) is True


def test_add_column_to_existing_is_acked() -> None:
    assert ct.migration_is_pure_create(ADD_COLUMN) is False


def test_backfill_dml_is_acked() -> None:
    assert ct.migration_is_pure_create(BACKFILL) is False


def test_index_on_existing_table_is_acked() -> None:
    assert ct.migration_is_pure_create(INDEX_ON_EXISTING) is False


def test_dynamic_sql_is_acked() -> None:
    assert ct.migration_is_pure_create(DYNAMIC) is False


def test_op_add_column_is_acked() -> None:
    assert ct.migration_is_pure_create(OP_ADD_COLUMN) is False


def test_migration_creating_nothing_is_acked() -> None:
    assert ct.migration_is_pure_create(CREATES_NOTHING) is False


def test_missing_upgrade_body_is_acked() -> None:
    assert ct.migration_is_pure_create("# not a migration") is False


def test_downgrade_removes_category_when_all_pure(tmp_path: Path) -> None:
    f = tmp_path / "0001_core.py"
    f.write_text(PURE_CREATE, encoding="utf-8")
    matches = [
        {"category": "db_migrations", "reason": "", "matched_files": [str(f)]},
    ]
    note = ct.apply_migration_downgrade(matches)
    assert matches == []  # category dropped -> auto-merge
    assert note is not None and note["downgraded"] is True


def test_mixed_batch_keeps_ack(tmp_path: Path) -> None:
    pure = tmp_path / "0001_core.py"
    pure.write_text(PURE_CREATE, encoding="utf-8")
    risky = tmp_path / "0002_alter.py"
    risky.write_text(ADD_COLUMN, encoding="utf-8")
    matches = [
        {"category": "db_migrations", "reason": "", "matched_files": [str(pure), str(risky)]},
    ]
    note = ct.apply_migration_downgrade(matches)
    assert len(matches) == 1  # kept -> ack
    assert note is not None and note["downgraded"] is False


def test_other_categories_never_downgraded(tmp_path: Path) -> None:
    f = tmp_path / "0001_core.py"
    f.write_text(PURE_CREATE, encoding="utf-8")
    matches = [
        {"category": "db_migrations", "reason": "", "matched_files": [str(f)]},
        {"category": "billing_money", "reason": "", "matched_files": ["backend/src/billing/x.py"]},
    ]
    ct.apply_migration_downgrade(matches)
    # db_migrations dropped, billing stays -> still ack overall
    assert [m["category"] for m in matches] == ["billing_money"]


def test_deleted_migration_file_is_acked(tmp_path: Path) -> None:
    matches = [
        {"category": "db_migrations", "reason": "", "matched_files": [str(tmp_path / "gone.py")]},
    ]
    note = ct.apply_migration_downgrade(matches)
    assert len(matches) == 1  # unreadable -> fail-closed ack
    assert note is None or note["downgraded"] is False
