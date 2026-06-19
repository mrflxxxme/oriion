"""AC-W1-14: audit_log cold-storage archival — serialization + upload contract.

Exercises ``archive_audit_log`` with a fake session + a fake S3 putter (no live
bucket): asserts the deterministic object key, gzipped-JSONL body, row count, and
that an empty window still produces a (valid, empty) object. The live upload to a
real S3-compatible bucket (MinIO) is proven by ``infra/observability/proof/``.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from src.audit.models import AuditLog
from src.audit.services.archival_service import archive_audit_log, archive_key


class _FakeResult:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[AuditLog]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows

    async def execute(self, _stmt: Any) -> _FakeResult:
        return _FakeResult(self._rows)


class _FakeS3:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:  # noqa: N803
        self.calls.append({"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType})


def _row(action: str) -> AuditLog:
    return AuditLog(
        id=uuid4(),
        ts=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        actor_type="user",
        actor_id=uuid4(),
        action=action,
        payload={"k": "v"},
    )


def test_archive_key_is_deterministic_for_window() -> None:
    before = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert archive_key(before) == "audit_log/2026/06/01/audit_log_before_20260601T120000Z.jsonl.gz"


@pytest.mark.asyncio
async def test_archive_audit_log_serializes_and_uploads_jsonl_gz() -> None:
    rows = [_row("login"), _row("logout")]
    session = _FakeSession(rows)
    s3 = _FakeS3()
    before = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    result = await archive_audit_log(session, s3, bucket="cold-bucket", before=before)  # type: ignore[arg-type]

    assert result.row_count == 2
    assert result.object_key == "audit_log/2026/06/01/audit_log_before_20260601T120000Z.jsonl.gz"
    assert result.byte_size > 0
    assert len(s3.calls) == 1
    call = s3.calls[0]
    assert call["Bucket"] == "cold-bucket"
    assert call["Key"] == result.object_key
    assert call["ContentType"] == "application/gzip"

    lines = gzip.decompress(call["Body"]).decode("utf-8").splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    assert [p["action"] for p in parsed] == ["login", "logout"]
    assert parsed[0]["payload"] == {"k": "v"}
    assert parsed[0]["actor_type"] == "user"


@pytest.mark.asyncio
async def test_archive_audit_log_empty_window_uploads_empty_object() -> None:
    session = _FakeSession([])
    s3 = _FakeS3()
    before = datetime(2026, 6, 1, tzinfo=UTC)

    result = await archive_audit_log(session, s3, bucket="b", before=before)  # type: ignore[arg-type]

    assert result.row_count == 0
    assert len(s3.calls) == 1
    assert gzip.decompress(s3.calls[0]["Body"]) == b""
