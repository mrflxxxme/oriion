"""Audit-log archival to RU Object Storage (AC-W1-14).

``audit.audit_log`` is append-only (UPDATE/DELETE denied by trigger) and holds a
3-year ledger (ADR-014). This module exports rows older than the retention window
to gzipped JSONL and hands the bytes to an ``Uploader`` callable — the boto3 / S3
wiring lives in ``scripts/archive_audit_log.py`` (Yandex Object Storage,
``oriion-staging-loki-archive``-sibling bucket). Keeping serialization + the query
here (boto3-free) makes it unit-testable and mypy-strict clean.

The job EXPORTS for cold storage / durability; it does NOT delete (the trigger
forbids it and ФЗ-152 mandates the 3-year ledger). Re-runs are idempotent at the
object level only by their distinct timestamped keys — the operator schedules it
(cron/CronCreate) so each window is archived once.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.audit.models import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# An uploader persists ``(object_key, gzip_bytes)`` to cold storage.
Uploader = Callable[[str, bytes], Awaitable[None]]

# 3-year ledger (ADR-014). Rows older than this are eligible for cold archival.
DEFAULT_RETENTION_DAYS = 1095


@dataclass(frozen=True)
class ArchiveResult:
    """Outcome of one archival run."""

    object_key: str | None
    row_count: int
    byte_size: int


def _row_to_dict(row: AuditLog) -> dict[str, Any]:
    """JSON-safe projection of an audit row (UUID/INET/datetime → str)."""
    return {
        "id": str(row.id),
        "ts": row.ts.isoformat(),
        "actor_type": row.actor_type,
        "actor_id": str(row.actor_id) if row.actor_id is not None else None,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": str(row.resource_id) if row.resource_id is not None else None,
        "cell_id": str(row.cell_id) if row.cell_id is not None else None,
        "workspace_id": str(row.workspace_id) if row.workspace_id is not None else None,
        "payload": row.payload,
        "ip": str(row.ip) if row.ip is not None else None,
        "user_agent": row.user_agent,
    }


def serialize_audit_rows(rows: list[AuditLog]) -> bytes:
    """Gzip-compressed JSONL — one audit row per line, stable key order."""
    body = "\n".join(json.dumps(_row_to_dict(r), ensure_ascii=False, sort_keys=True) for r in rows)
    if body:
        body += "\n"
    return gzip.compress(body.encode("utf-8"))


def build_archive_key(*, cutoff: datetime, generated_at: datetime) -> str:
    """Object key partitioned by the run month: ``audit_log/YYYY/MM/...jsonl.gz``."""
    return (
        f"audit_log/{generated_at:%Y}/{generated_at:%m}/"
        f"audit-before-{cutoff:%Y%m%dT%H%M%SZ}-{generated_at:%Y%m%dT%H%M%SZ}.jsonl.gz"
    )


async def fetch_archivable_rows(session: AsyncSession, *, cutoff: datetime) -> list[AuditLog]:
    """All audit rows with ``ts < cutoff``, oldest first."""
    stmt = select(AuditLog).where(AuditLog.ts < cutoff).order_by(AuditLog.ts)
    return list((await session.execute(stmt)).scalars().all())


async def archive_audit_log(
    session: AsyncSession,
    *,
    uploader: Uploader,
    now: datetime,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> ArchiveResult:
    """Export audit rows older than ``now - retention_days`` to ``uploader``.

    Returns an empty result (no upload) when nothing is eligible, so the
    scheduled job is a clean no-op on quiet windows.
    """
    cutoff = now - timedelta(days=retention_days)
    rows = await fetch_archivable_rows(session, cutoff=cutoff)
    if not rows:
        return ArchiveResult(object_key=None, row_count=0, byte_size=0)
    data = serialize_audit_rows(rows)
    key = build_archive_key(cutoff=cutoff, generated_at=now)
    await uploader(key, data)
    return ArchiveResult(object_key=key, row_count=len(rows), byte_size=len(data))
