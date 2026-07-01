"""S3 asset flow — presign (transactional key reservation) → complete (verify).

ADR-038 lifecycle: presign inserts a ``pending`` s3_objects row (the
``UNIQUE(bucket, s3_key)`` constraint IS the reservation — a duplicate key is
rejected at presign time, AC-01.5.4); the client uploads via presigned POST
(5-min TTL); ``complete`` re-reads the object server-side, computes
sha256/byte_size (the client is never trusted), flips pending → stored and
allocates the immutable version row. Signed GET is 1-hour TTL (ADR-012 — the
bucket is never public).

``Boto3ObjectStorage`` is the production adapter for the ``ObjectStoragePort``
protocol; boto3 is sync, so every network call is pushed to a worker thread.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError

from src.artifacts.events import emit_s3_asset_uploaded
from src.artifacts.exceptions import (
    ArtifactNotFound,
    InvalidFilename,
    S3KeyAlreadyReserved,
    S3ObjectNotFound,
    UploadNotVerified,
)
from src.artifacts.models import (
    PRESIGN_POST_TTL_SECONDS,
    SIGNED_GET_TTL_SECONDS,
    ArtifactVersion,
    S3Object,
)
from src.artifacts.ports import ObjectStoragePort
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.s3_repository import S3ObjectRepository
from src.artifacts.services.versioning import allocate_version

logger = structlog.get_logger(__name__)

# Conservative filename charset — blocks path traversal / key injection.
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")


def sanitize_filename(filename: str) -> str:
    """Validate the client-supplied filename for use as the last key segment.

    Rejects separators, traversal sequences and exotic characters outright
    (422) instead of trying to rewrite them — предсказуемый ключ важнее UX.
    """
    if not _FILENAME_RE.match(filename) or ".." in filename:
        raise InvalidFilename(filename)
    return filename


class Boto3ObjectStorage:
    """boto3-backed ObjectStoragePort (MinIO dev / Yandex Object Storage prod)."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region_name: str = "ru-central1",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._region_name = region_name
        self._client: Any | None = None

    def _client_lazy(self) -> Any:
        """Build the boto3 client on first use (cheap to keep per-process)."""
        if self._client is None:
            import boto3
            from botocore.config import Config as BotoConfig

            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region_name,
                # path-style + SigV4: required by MinIO, accepted by YOS.
                config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._client

    async def presign_post(
        self, *, bucket: str, key: str, expires_in: int, max_bytes: int
    ) -> dict[str, object]:
        client = self._client_lazy()
        # Presigned POST generation is pure local crypto — still threaded for
        # uniformity (botocore may lazily load service models from disk).
        result: dict[str, Any] = await asyncio.to_thread(
            client.generate_presigned_post,
            Bucket=bucket,
            Key=key,
            Conditions=[["content-length-range", 1, max_bytes]],
            ExpiresIn=expires_in,
        )
        return {"url": result["url"], "fields": result["fields"]}

    async def head_object(self, *, bucket: str, key: str) -> int | None:
        from botocore.exceptions import ClientError

        client = self._client_lazy()
        try:
            head: dict[str, Any] = await asyncio.to_thread(
                client.head_object, Bucket=bucket, Key=key
            )
        except ClientError:
            return None
        return int(head["ContentLength"])

    async def get_object(self, *, bucket: str, key: str) -> bytes | None:
        from botocore.exceptions import ClientError

        client = self._client_lazy()

        def _read() -> bytes:
            obj = client.get_object(Bucket=bucket, Key=key)
            body: bytes = obj["Body"].read()
            return body

        try:
            return await asyncio.to_thread(_read)
        except ClientError:
            return None

    async def presign_get(self, *, bucket: str, key: str, expires_in: int) -> str:
        client = self._client_lazy()
        url: str = await asyncio.to_thread(
            client.generate_presigned_url,
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_object(self, *, bucket: str, key: str) -> None:
        client = self._client_lazy()
        await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key)


class S3AssetService:
    """Presign → upload → complete → signed-GET, with lifecycle accounting."""

    def __init__(
        self,
        s3_repo: S3ObjectRepository,
        artifact_repo: ArtifactRepository,
        usage_repo: UsageRepository,
        storage: ObjectStoragePort,
        *,
        bucket: str,
        env_prefix: str,
        max_upload_bytes: int,
    ) -> None:
        self._s3_repo = s3_repo
        self._artifact_repo = artifact_repo
        self._usage_repo = usage_repo
        self._storage = storage
        self._bucket = bucket
        self._env_prefix = env_prefix
        self._max_upload_bytes = max_upload_bytes

    def build_key(
        self, *, cell_id: UUID, artifact_id: UUID, version_num: int, filename: str
    ) -> str:
        """ADR-012 key structure: <env>/<cell_id>/<artifact_id>/<version_num>/<filename>."""
        return f"{self._env_prefix}/{cell_id}/{artifact_id}/{version_num}/{filename}"

    async def presign_upload(
        self,
        *,
        cell_id: UUID,
        artifact_id: UUID,
        filename: str,
        mime_type: str | None = None,
    ) -> tuple[S3Object, dict[str, object]]:
        """Reserve the key transactionally + hand back the presigned POST."""
        safe_name = sanitize_filename(filename)
        envelope = await self._artifact_repo.get(artifact_id, cell_id=cell_id)
        if envelope is None:
            raise ArtifactNotFound(str(artifact_id))

        key = self.build_key(
            cell_id=cell_id,
            artifact_id=artifact_id,
            version_num=envelope.current_version_num + 1,
            filename=safe_name,
        )
        try:
            row = await self._s3_repo.insert_pending(
                cell_id=cell_id,
                artifact_id=artifact_id,
                bucket=self._bucket,
                s3_key=key,
                mime_type=mime_type,
            )
        except IntegrityError as exc:
            raise S3KeyAlreadyReserved(key) from exc

        presigned = await self._storage.presign_post(
            bucket=self._bucket,
            key=key,
            expires_in=PRESIGN_POST_TTL_SECONDS,
            max_bytes=self._max_upload_bytes,
        )
        return row, presigned

    async def complete_upload(
        self,
        *,
        cell_id: UUID,
        s3_object_id: UUID,
        created_by_user_id: UUID | None = None,
        created_by_agent_id: UUID | None = None,
    ) -> tuple[ArtifactVersion, S3Object]:
        """Verify server-side (never trust the client) + create the version row."""
        row = await self._s3_repo.get(s3_object_id, cell_id=cell_id)
        if row is None:
            raise S3ObjectNotFound(str(s3_object_id))
        if row.status != "pending":
            raise UploadNotVerified(f"s3 object is '{row.status}', expected 'pending'")

        body = await self._storage.get_object(bucket=row.bucket, key=row.s3_key)
        if body is None:
            raise UploadNotVerified("uploaded object not found in the bucket")

        byte_size = len(body)
        content_hash = hashlib.sha256(body).hexdigest()
        await self._s3_repo.mark_stored(
            row.id, byte_size=byte_size, content_hash_sha256=content_hash
        )
        version = await allocate_version(
            self._artifact_repo,
            self._usage_repo,
            cell_id=cell_id,
            artifact_id=row.artifact_id,
            storage_kind="s3",
            s3_object_id=row.id,
            byte_size=byte_size,
            content_hash_sha256=content_hash,
            created_by_user_id=created_by_user_id,
            created_by_agent_id=created_by_agent_id,
        )
        await emit_s3_asset_uploaded(
            artifact_id=row.artifact_id,
            cell_id=cell_id,
            s3_object_id=row.id,
            s3_key=row.s3_key,
            byte_size=byte_size,
            version_num=version.version_num,
        )
        return version, row

    async def download_url(self, *, cell_id: UUID, s3_object_id: UUID) -> str:
        """Signed GET (1h TTL) for a ``stored`` object — never a public URL."""
        row = await self._s3_repo.get(s3_object_id, cell_id=cell_id)
        if row is None or row.status != "stored":
            raise S3ObjectNotFound(str(s3_object_id))
        return await self._storage.presign_get(
            bucket=row.bucket, key=row.s3_key, expires_in=SIGNED_GET_TTL_SECONDS
        )

    async def purge_stale_pending(self, *, cell_id: UUID) -> int:
        """Janitor: drop ``pending`` reservations whose presign window lapsed.

        Wave-1 exposes this as a service call (invoked opportunistically);
        a scheduled worker can wrap it later without an interface change.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=PRESIGN_POST_TTL_SECONDS)
        pruned = await self._s3_repo.delete_stale_pending(cell_id=cell_id, older_than=cutoff)
        if pruned:
            logger.info(
                "artifacts.s3.stale_pending_pruned",
                context="artifacts",
                action="purge_stale_pending",
                cell_id=str(cell_id),
                pruned=pruned,
            )
        return pruned
