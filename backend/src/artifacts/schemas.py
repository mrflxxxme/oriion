"""Pydantic v2 DTOs for the artifacts API (ADR-038, Phase 01.5).

Request models forbid extras (``extra='forbid'``); response models read from
ORM attributes (``from_attributes=True``). Binary CRDT payloads travel as
base64 strings (REST-only Wave 1); raw bytes never appear in JSON.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ArtifactType = Literal["document", "code", "asset"]

_MAX_UPDATE_B64_CHARS = 4 * 1024 * 1024  # ~3 MiB of raw update bytes


class ArtifactCreate(BaseModel):
    """Create an artifact envelope."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: ArtifactType
    title: str = Field(min_length=1, max_length=300)
    tags: list[str] = Field(default_factory=list, max_length=32)
    created_by_agent_id: UUID | None = None

    @field_validator("tags")
    @classmethod
    def _tag_length(cls, tags: list[str]) -> list[str]:
        if any(len(tag) < 1 or len(tag) > 100 for tag in tags):
            raise ValueError("each tag must be 1..100 characters")
        return tags


class ArtifactOut(BaseModel):
    """Envelope as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    artifact_type: str
    title: str
    tags: list[str]
    owner_user_id: UUID | None
    created_by_agent_id: UUID | None
    current_version_num: int
    created_at: datetime
    updated_at: datetime


class InlineVersionCreate(BaseModel):
    """Commit an inline (jsonb) content version."""

    model_config = ConfigDict(extra="forbid")

    content: dict[str, object]
    text_export: str | None = Field(default=None, max_length=100_000)


class ArtifactVersionOut(BaseModel):
    """Immutable version row (``artifact://.../vN`` target)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_id: UUID
    version_num: int
    storage_kind: str
    content_inline: dict[str, object] | None
    s3_object_id: UUID | None
    yjs_snapshot_id: UUID | None
    byte_size: int
    content_hash_sha256: str
    created_at: datetime


# ── Yjs ─────────────────────────────────────────────────────────────────── #


class YjsDocumentOut(BaseModel):
    """Live CRDT head — state/state_vector as base64 (REST-only Wave 1)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    artifact_id: UUID
    state_base64: str
    state_vector_base64: str
    update_count: int
    last_compacted_at: datetime | None


class YjsUpdateIn(BaseModel):
    """One client-side Yjs update (base64-encoded binary)."""

    model_config = ConfigDict(extra="forbid")

    update_base64: str = Field(min_length=1, max_length=_MAX_UPDATE_B64_CHARS)

    def decoded(self) -> bytes:
        try:
            return base64.b64decode(self.update_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"invalid base64: {exc}") from exc

    @field_validator("update_base64")
    @classmethod
    def _valid_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("update_base64 is not valid base64") from exc
        return value


class YjsCommitOut(BaseModel):
    """Explicit version commit result."""

    model_config = ConfigDict(extra="forbid")

    version: ArtifactVersionOut
    snapshot_id: UUID
    artifact_url: str


# ── S3 uploads ──────────────────────────────────────────────────────────── #


class UploadCreate(BaseModel):
    """Request a presigned POST for a new asset version."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=255)


class UploadOut(BaseModel):
    """Presigned POST + the reserved lifecycle row id."""

    model_config = ConfigDict(extra="forbid")

    s3_object_id: UUID
    bucket: str
    s3_key: str
    upload_url: str
    upload_fields: dict[str, object]
    expires_in_seconds: int


class S3ObjectOut(BaseModel):
    """Lifecycle row as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_id: UUID
    bucket: str
    s3_key: str
    mime_type: str | None
    byte_size: int | None
    content_hash_sha256: str | None
    status: str


class UploadCompleteOut(BaseModel):
    """Server-side verified upload → version row."""

    model_config = ConfigDict(extra="forbid")

    version: ArtifactVersionOut
    s3_object: S3ObjectOut
    artifact_url: str


class DownloadUrlOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    expires_in_seconds: int


# ── usage + resolve ─────────────────────────────────────────────────────── #


class UsageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cell_id: UUID
    bytes_total: int


class ResolveOut(BaseModel):
    """artifact:// resolution result — exactly one payload field is non-null."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID
    cell_id: UUID
    artifact_type: str
    title: str
    version_num: int
    storage_kind: str
    byte_size: int
    content_hash_sha256: str
    content_inline: dict[str, object] | None
    download_url: str | None
    yjs_state_base64: str | None
    artifact_url: str
