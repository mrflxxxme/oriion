"""Unit: SQLAlchemy mapping assertions for mcp.ConnectorCredential.

No database — verifies the model declaration (schema, table, columns,
constraints, indexes) so a mis-typed mapping is caught before integration.
Mirrors ``tests/mcp/test_models.py`` for MCPConnection.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from src.mcp.models import ConnectorCredential


def test_table_in_mcp_schema() -> None:
    table = ConnectorCredential.__table__
    assert table.schema == "mcp"
    assert table.name == "connector_credentials"


def test_columns_match_ddl() -> None:
    cols = {c.name for c in ConnectorCredential.__table__.columns}
    assert cols == {
        "id",
        "workspace_id",
        "connector_slug",
        "cred_encrypted",
        "cred_fingerprint",
        "label",
        "is_active",
        "created_by",
        "created_at",
        "updated_at",
        "revoked_at",
    }


def test_unique_and_check_constraints_declared() -> None:
    constraint_names = {
        c.name for c in ConnectorCredential.__table__.constraints if c.name is not None
    }
    assert "connector_credentials_unique_label" in constraint_names
    assert "connector_credentials_connector_slug_check" in constraint_names


def test_partial_active_index_declared() -> None:
    index_names = {idx.name for idx in ConnectorCredential.__table__.indexes}
    assert "connector_credentials_workspace_active_idx" in index_names


def test_nullable_columns() -> None:
    cols = {c.name: c.nullable for c in ConnectorCredential.__table__.columns}
    assert cols["workspace_id"] is False
    assert cols["connector_slug"] is False
    assert cols["cred_encrypted"] is False
    assert cols["cred_fingerprint"] is False
    assert cols["created_by"] is False
    assert cols["revoked_at"] is True


def test_workspace_fk_cascades() -> None:
    fks = list(ConnectorCredential.__table__.c.workspace_id.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.column.table.schema == "multitenancy"
    assert fk.column.table.name == "workspaces"
    assert fk.ondelete == "CASCADE"


def test_instance_attributes_round_trip() -> None:
    cred = ConnectorCredential(
        workspace_id=uuid4(),
        connector_slug="telegram-bot",
        cred_encrypted=b"\x00\x01ciphertext",
        cred_fingerprint="abc12345",
        label="main",
        created_by=uuid4(),
    )
    assert cred.connector_slug == "telegram-bot"
    assert cred.cred_fingerprint == "abc12345"
    assert isinstance(cred.workspace_id, UUID)
    assert cred.cred_encrypted == b"\x00\x01ciphertext"
