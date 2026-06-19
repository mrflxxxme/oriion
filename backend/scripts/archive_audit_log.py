"""CLI: archive aged ``audit.audit_log`` rows to RU Object Storage (AC-W1-14).

Streams rows with ``ts < --before`` to a gzipped-JSONL object in the cold-storage
bucket (Yandex Object Storage in prod; MinIO in the local proof harness). Intended
to run as a scheduled job (cron / YC Cloud Functions trigger) AFTER the Postgres
hot-retention window, so the ФЗ-152 3-year ledger lives in cheap object storage.

Environment:
    DATABASE_URL                          async PG DSN (read via Settings)
    AUDIT_ARCHIVE_S3_ENDPOINT             S3 endpoint (https://storage.yandexcloud.net | http://minio:9000)
    AUDIT_ARCHIVE_S3_REGION               ru-central1 (default)
    AUDIT_ARCHIVE_S3_BUCKET               oriion-staging-loki-archive (default)
    AUDIT_ARCHIVE_S3_ACCESS_KEY_ID        YC static access key
    AUDIT_ARCHIVE_S3_SECRET_ACCESS_KEY    YC static secret key

Usage::

    python -m scripts.archive_audit_log --before 2026-03-01T00:00:00+00:00
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime

import boto3
from src._shared.db.session import get_session_maker
from src.audit.services.archival_service import archive_audit_log


def _s3_client() -> object:
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("AUDIT_ARCHIVE_S3_ENDPOINT") or None,
        region_name=os.environ.get("AUDIT_ARCHIVE_S3_REGION", "ru-central1"),
        aws_access_key_id=os.environ["AUDIT_ARCHIVE_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AUDIT_ARCHIVE_S3_SECRET_ACCESS_KEY"],
    )


async def _run(*, before: datetime, bucket: str) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await archive_audit_log(session, _s3_client(), bucket=bucket, before=before)
    print(
        f"archived {result.row_count} rows "
        f"-> s3://{bucket}/{result.object_key} ({result.byte_size} bytes)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="archive_audit_log", description=__doc__)
    parser.add_argument(
        "--bucket",
        default=os.environ.get("AUDIT_ARCHIVE_S3_BUCKET", "oriion-staging-loki-archive"),
    )
    parser.add_argument(
        "--before",
        default=None,
        help="ISO-8601 timestamp; rows with ts < before are archived (default: now)",
    )
    args = parser.parse_args()
    before = datetime.fromisoformat(args.before) if args.before else datetime.now(UTC)
    asyncio.run(_run(before=before, bucket=args.bucket))


if __name__ == "__main__":
    main()
