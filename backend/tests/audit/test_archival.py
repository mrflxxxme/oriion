"""AC-W1-14: audit_log archival to RU Object Storage — serialization + run logic.

Boto3-free (the S3 wiring is scripts/archive_audit_log.py); here we exercise the
pure serialization, key derivation, and the archive_audit_log control flow with a
fake session + fake uploader.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from src.audit.archival import (
    ArchiveResult,
    archive_audit_log,
    build_archive_key,
    fetch_archivable_rows,
    serialize_audit_rows,
)
from src.audit.models import AuditLog


def _row(action: str, *, ts: datetime, payload: dict[str, Any] | None = None) -> AuditLog:
    row = AuditLog(actor_type="user", action=action)
    row.id = uuid4()
    row.ts = ts
    row.actor_id = uuid4()
    row.resource_type = "task"
    row.resource_id = uuid4()
    row.cell_id = uuid4()
    row.workspace_id = uuid4()
    row.payload = payload
    row.ip = "203.0.113.7"
    row.user_agent = "pytest"
    return row


class _FakeResult:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows

    def scalars(self) -> Any:
        rows = self._rows

        class _Scalars:
            def all(self) -> list[AuditLog]:
                return rows

        return _Scalars()


class _FakeSession:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows
        self.executed = 0

    async def execute(self, _stmt: Any) -> _FakeResult:
        self.executed += 1
        return _FakeResult(self._rows)


def test_serialize_audit_rows_roundtrips_jsonl() -> None:
    rows = [
        _row("login.success", ts=datetime(2023, 1, 1, tzinfo=UTC), payload={"k": "значение"}),
        _row("task.created", ts=datetime(2023, 1, 2, tzinfo=UTC)),
    ]
    data = serialize_audit_rows(rows)
    lines = gzip.decompress(data).decode("utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["action"] == "login.success"
    assert first["payload"] == {"k": "значение"}
    assert first["ip"] == "203.0.113.7"
    # JSON is round-trippable + non-ASCII preserved.
    assert "значение" in lines[0]


def test_serialize_empty_is_valid_empty_gzip() -> None:
    data = serialize_audit_rows([])
    assert gzip.decompress(data) == b""


def test_build_archive_key_partitions_by_run_month() -> None:
    key = build_archive_key(
        cutoff=datetime(2023, 1, 1, tzinfo=UTC),
        generated_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC),
    )
    assert key == ("audit_log/2026/06/audit-before-20230101T000000Z-20260617T120000Z.jsonl.gz")


@pytest.mark.asyncio
async def test_fetch_archivable_rows_returns_scalars() -> None:
    rows = [_row("a", ts=datetime(2020, 1, 1, tzinfo=UTC))]
    session = _FakeSession(rows)
    got = await fetch_archivable_rows(session, cutoff=datetime(2023, 1, 1, tzinfo=UTC))  # type: ignore[arg-type]
    assert got == rows
    assert session.executed == 1


@pytest.mark.asyncio
async def test_archive_uploads_and_reports_result() -> None:
    rows = [
        _row("a", ts=datetime(2020, 1, 1, tzinfo=UTC)),
        _row("b", ts=datetime(2020, 1, 2, tzinfo=UTC)),
    ]
    session = _FakeSession(rows)
    captured: list[tuple[str, bytes]] = []

    async def _uploader(key: str, data: bytes) -> None:
        captured.append((key, data))

    now = datetime(2026, 6, 17, tzinfo=UTC)
    result = await archive_audit_log(
        session,  # type: ignore[arg-type]
        uploader=_uploader,
        now=now,
        retention_days=1095,
    )

    assert isinstance(result, ArchiveResult)
    assert result.row_count == 2
    assert result.object_key is not None and result.object_key.startswith("audit_log/2026/06/")
    assert result.byte_size > 0
    assert len(captured) == 1
    key, data = captured[0]
    assert key == result.object_key
    assert len(gzip.decompress(data).decode("utf-8").splitlines()) == 2


@pytest.mark.asyncio
async def test_archive_no_rows_is_noop() -> None:
    session = _FakeSession([])
    calls: list[Any] = []

    async def _uploader(key: str, data: bytes) -> None:
        calls.append((key, data))

    result = await archive_audit_log(
        session,  # type: ignore[arg-type]
        uploader=_uploader,
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )
    assert result == ArchiveResult(object_key=None, row_count=0, byte_size=0)
    assert calls == []  # nothing uploaded on an empty window
