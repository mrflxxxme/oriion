"""Object-storage port for the artifacts context.

The service layer depends on this Protocol only; the boto3 adapter
(``services/s3.py::Boto3ObjectStorage``) is wired in ``deps.py`` and unit
tests inject ``tests/artifacts/_fakes.py::FakeObjectStorage`` (no network).
"""

from __future__ import annotations

from typing import Protocol


class ObjectStoragePort(Protocol):
    """The slice of S3-compatible storage the artifacts context needs."""

    async def presign_post(
        self, *, bucket: str, key: str, expires_in: int, max_bytes: int
    ) -> dict[str, object]:
        """Presigned POST policy: ``{"url": ..., "fields": {...}}`` (5-min TTL)."""
        ...

    async def head_object(self, *, bucket: str, key: str) -> int | None:
        """Object size in bytes, or None when the object does not exist."""
        ...

    async def get_object(self, *, bucket: str, key: str) -> bytes | None:
        """Full object body (server-side sha256 verification), or None."""
        ...

    async def presign_get(self, *, bucket: str, key: str, expires_in: int) -> str:
        """Signed GET URL (1-hour TTL per ADR-012 — bucket is never public)."""
        ...

    async def delete_object(self, *, bucket: str, key: str) -> None:
        """Best-effort delete (janitor / lifecycle cleanup)."""
        ...
