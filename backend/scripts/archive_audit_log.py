"""Archive audit_log rows older than the retention window to YC Object Storage.

AC-W1-14 ops job. Scheduled (cron / a YC Cloud Function on a timer) to ship the
append-only audit ledger to the RU-zone S3-compatible bucket for the 3-year cold
archive. The serialization + query are in ``src.audit.archival`` (unit-tested);
this script is only the boto3 + DB-session wiring.

Env vars (all but the first have sensible defaults):
    DATABASE_URL                     — async PG DSN (from Settings)
    AUDIT_ARCHIVE_BUCKET             — target bucket (e.g. oriion-staging-audit-archive)
    AUDIT_ARCHIVE_S3_ENDPOINT        — default https://storage.yandexcloud.net
    AUDIT_ARCHIVE_S3_REGION          — default ru-central1
    AUDIT_ARCHIVE_S3_ACCESS_KEY_ID   — storage SA static key id (from Lockbox)
    AUDIT_ARCHIVE_S3_SECRET_ACCESS_KEY — storage SA static key secret (from Lockbox)
    AUDIT_RETENTION_DAYS             — default 1095 (3 years)

Usage:
    uv run python scripts/archive_audit_log.py
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import boto3
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src._shared.config import get_settings
from src._shared.logging import configure_structlog
from src.audit.archival import DEFAULT_RETENTION_DAYS, Uploader, archive_audit_log

logger = structlog.get_logger(__name__)


def _make_s3_uploader() -> Uploader:
    endpoint = os.environ.get("AUDIT_ARCHIVE_S3_ENDPOINT", "https://storage.yandexcloud.net")
    region = os.environ.get("AUDIT_ARCHIVE_S3_REGION", "ru-central1")
    bucket = os.environ["AUDIT_ARCHIVE_BUCKET"]
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=os.environ["AUDIT_ARCHIVE_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AUDIT_ARCHIVE_S3_SECRET_ACCESS_KEY"],
    )

    async def _upload(key: str, data: bytes) -> None:
        # boto3 is sync — keep the event loop responsive.
        await asyncio.to_thread(
            client.put_object,
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="application/gzip",
        )

    return _upload


async def _run() -> None:
    settings = get_settings()
    retention_days = int(os.environ.get("AUDIT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
    uploader = _make_s3_uploader()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with maker() as session:
            result = await archive_audit_log(
                session,
                uploader=uploader,
                now=datetime.now(UTC),
                retention_days=retention_days,
            )
        logger.info(
            "audit.archival.done",
            object_key=result.object_key,
            row_count=result.row_count,
            byte_size=result.byte_size,
        )
    finally:
        await engine.dispose()


def main() -> None:
    configure_structlog()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
