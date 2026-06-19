"""audit.audit_log cold-storage archival (AC-W1-14, ФЗ-152 3-year ledger).

``audit.audit_log`` is the append-only, RANGE-partitioned compliance ledger. The
3-year retention обязательство (ФЗ-152) cannot live on the hot Postgres forever,
so this job streams aged rows to the RU-zone Object Storage bucket
(`oriion-staging-loki-archive`, provisioned in ``infra/terraform/object_storage.tf``)
as gzipped JSONL — one object per archival window, deterministic key so a re-run
overwrites idempotently rather than duplicating.

The core ``archive_audit_log`` takes an injected session + an S3 "putter" so it is
unit-testable without a live bucket; ``scripts/archive_audit_log.py`` wires the
real async engine + a boto3 S3 client (S3-compatible: Yandex Object Storage in
prod, MinIO in the local proof harness).
"""

from __future__ import annotations

import gzip
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.audit.models import AuditLog

# Columns serialized per row — explicit so the archive schema is stable even if
# the model gains columns later (a new column is a deliberate archive-format bump).
_ARCHIVED_FIELDS = (
    "id",
    "ts",
    "actor_type",
    "actor_id",
    "action",
    "resource_type",
    "resource_id",
    "cell_id",
    "workspace_id",
    "payload",
    "ip",
    "user_agent",
)


class S3Putter(Protocol):
    """The slice of a boto3 S3 client this job needs (so tests inject a fake).

    Typed with ``**kwargs`` because the call site passes boto3's PascalCase kwargs
    (``Bucket``/``Key``/``Body``/``ContentType``) verbatim — naming them in the
    Protocol would trip N803 for no benefit.
    """

    def put_object(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class ArchiveResult:
    object_key: str
    row_count: int
    byte_size: int


def _row_to_dict(row: AuditLog) -> dict[str, Any]:
    return {field: getattr(row, field) for field in _ARCHIVED_FIELDS}


def archive_key(before: datetime, *, key_prefix: str = "audit_log") -> str:
    """Deterministic object key for an archival window (idempotent re-runs)."""
    return f"{key_prefix}/{before:%Y/%m/%d}/audit_log_before_{before:%Y%m%dT%H%M%SZ}.jsonl.gz"


async def archive_audit_log(
    session: AsyncSession,
    s3: S3Putter,
    *,
    bucket: str,
    before: datetime,
    key_prefix: str = "audit_log",
) -> ArchiveResult:
    """Export ``audit.audit_log`` rows with ``ts < before`` to a gzipped JSONL
    object in the cold-storage bucket. Returns the key + row count + byte size.

    Rows are streamed oldest-first, one compact JSON object per line. ``mtime=0``
    keeps the gzip header deterministic so an unchanged window yields identical
    bytes (cheap dedupe + reproducible-archive audit).
    """
    rows = (
        (await session.execute(select(AuditLog).where(AuditLog.ts < before).order_by(AuditLog.ts)))
        .scalars()
        .all()
    )
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for row in rows:
            line = json.dumps(_row_to_dict(row), separators=(",", ":"), default=str)
            gz.write(f"{line}\n".encode())
    body = buf.getvalue()
    key = archive_key(before, key_prefix=key_prefix)
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/gzip")
    return ArchiveResult(object_key=key, row_count=len(rows), byte_size=len(body))
