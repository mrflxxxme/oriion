"""AC-W1-14 audit-archival LIVE upload proof (run from backend/ via uv).

Exercises the REAL ``archive_audit_log`` + a REAL boto3 S3 client against the
proof MinIO bucket: serializes a couple of AuditLog rows to gzipped JSONL,
uploads, then downloads the object back and verifies the line count. The DB read
is unit-tested separately (tests/audit/test_archival_service.py); this proves the
boto3 -> S3 upload hop lands a real object in the bucket.

Run: cd backend && uv run python ../infra/observability/proof/archival_proof.py
Env: MINIO at http://localhost:19000 (proofkey/proofsecret123), bucket loki-archive.
"""

from __future__ import annotations

import asyncio
import gzip
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import boto3

from src.audit.models import AuditLog
from src.audit.services.archival_service import archive_audit_log


class _Result:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[AuditLog]:
        return self._rows


class _Session:
    def __init__(self, rows: list[AuditLog]) -> None:
        self._rows = rows

    async def execute(self, _stmt: Any) -> _Result:
        return _Result(self._rows)


async def _main() -> int:
    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:19000",
        region_name="us-east-1",
        aws_access_key_id="proofkey",
        aws_secret_access_key="proofsecret123",
    )
    rows = [
        AuditLog(id=uuid4(), ts=datetime(2026, 1, 1, tzinfo=UTC), actor_type="user", action="login"),
        AuditLog(id=uuid4(), ts=datetime(2026, 1, 2, tzinfo=UTC), actor_type="system", action="rotate"),
    ]
    before = datetime(2026, 6, 1, tzinfo=UTC)
    result = await archive_audit_log(_Session(rows), s3, bucket="loki-archive", before=before)
    print(f"UPLOADED s3://loki-archive/{result.object_key} rows={result.row_count} bytes={result.byte_size}")

    obj = s3.get_object(Bucket="loki-archive", Key=result.object_key)
    body = obj["Body"].read()
    lines = gzip.decompress(body).decode("utf-8").splitlines()
    print(f"DOWNLOADED bytes={len(body)} lines={len(lines)}")
    ok = result.row_count == 2 and len(lines) == 2
    print("ARCHIVAL_PROOF", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
