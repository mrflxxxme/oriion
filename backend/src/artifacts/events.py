"""CloudEvents emitters for the artifacts bounded context.

Each function wraps ``src._shared.cloudevents.emit_cloudevent`` with the
canonical ce_type per ``contracts/artifacts/events.yaml`` — the same house
mechanism every non-tasks context uses (multitenancy/iam/agents/llm_gateway).
Wave 0/1 transport is structlog; the Redis Streams swap will not change
call-sites.
"""

from __future__ import annotations

from uuid import UUID

from src._shared.cloudevents import emit_cloudevent

_SOURCE = "oriion://contexts/artifacts"


async def emit_artifact_created(
    artifact_id: UUID,
    cell_id: UUID,
    artifact_type: str,
    title: str,
    owner_user_id: UUID | None = None,
    created_by_agent_id: UUID | None = None,
    correlation_id: str | None = None,
) -> None:
    """oriion.artifacts.created.v1."""
    await emit_cloudevent(
        ce_type="oriion.artifacts.created.v1",
        source=_SOURCE,
        data={
            "artifact_id": str(artifact_id),
            "cell_id": str(cell_id),
            "artifact_type": artifact_type,
            "title": title,
            "owner_user_id": str(owner_user_id) if owner_user_id else None,
            "created_by_agent_id": str(created_by_agent_id) if created_by_agent_id else None,
        },
        correlation_id=correlation_id,
    )


async def emit_artifact_version_created(
    artifact_id: UUID,
    cell_id: UUID,
    version_num: int,
    storage_kind: str,
    byte_size: int,
    correlation_id: str | None = None,
) -> None:
    """oriion.artifacts.version_created.v1."""
    await emit_cloudevent(
        ce_type="oriion.artifacts.version_created.v1",
        source=_SOURCE,
        data={
            "artifact_id": str(artifact_id),
            "cell_id": str(cell_id),
            "version_num": version_num,
            "storage_kind": storage_kind,
            "byte_size": byte_size,
            "artifact_url": f"artifact://{cell_id}/{artifact_id}/v{version_num}",
        },
        correlation_id=correlation_id,
    )


async def emit_artifact_deleted(
    artifact_id: UUID,
    cell_id: UUID,
    bytes_freed: int,
) -> None:
    """oriion.artifacts.deleted.v1 (soft-delete of the envelope)."""
    await emit_cloudevent(
        ce_type="oriion.artifacts.deleted.v1",
        source=_SOURCE,
        data={
            "artifact_id": str(artifact_id),
            "cell_id": str(cell_id),
            "bytes_freed": bytes_freed,
        },
    )


async def emit_yjs_snapshot_committed(
    artifact_id: UUID,
    cell_id: UUID,
    yjs_document_id: UUID,
    snapshot_id: UUID,
    version_num: int,
    byte_size: int,
) -> None:
    """oriion.artifacts.yjs.snapshot_committed.v1 (explicit version commit)."""
    await emit_cloudevent(
        ce_type="oriion.artifacts.yjs.snapshot_committed.v1",
        source=_SOURCE,
        data={
            "artifact_id": str(artifact_id),
            "cell_id": str(cell_id),
            "yjs_document_id": str(yjs_document_id),
            "snapshot_id": str(snapshot_id),
            "version_num": version_num,
            "byte_size": byte_size,
        },
    )


async def emit_s3_asset_uploaded(
    artifact_id: UUID,
    cell_id: UUID,
    s3_object_id: UUID,
    s3_key: str,
    byte_size: int,
    version_num: int,
) -> None:
    """oriion.artifacts.s3.asset_uploaded.v1 (verified `complete`)."""
    await emit_cloudevent(
        ce_type="oriion.artifacts.s3.asset_uploaded.v1",
        source=_SOURCE,
        data={
            "artifact_id": str(artifact_id),
            "cell_id": str(cell_id),
            "s3_object_id": str(s3_object_id),
            "s3_key": s3_key,
            "byte_size": byte_size,
            "version_num": version_num,
        },
    )
