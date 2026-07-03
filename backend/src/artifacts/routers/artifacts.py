"""Artifacts API — envelope CRUD, versions, Yjs REST persistence, S3 uploads,
usage and the artifact:// resolver (ADR-038, Phase 01.5).

Cell scope comes from the RLS tenant context (``get_current_cell_id``) — not
a path param (Wave-0 single-cell, mirrors memory/billing). Route ordering:
literal paths (``/usage``, ``/resolve``, ``/uploads/...``) are declared BEFORE
``/{artifact_id}`` so they never get captured as a UUID path param.
"""

from __future__ import annotations

import base64
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src._shared.middleware.tenant_context import get_current_cell_id
from src.artifacts.deps import (
    get_artifact_resolver,
    get_artifact_service,
    get_s3_asset_service,
    get_yjs_service,
)
from src.artifacts.exceptions import InvalidYjsUpdate
from src.artifacts.models import (
    PRESIGN_POST_TTL_SECONDS,
    SIGNED_GET_TTL_SECONDS,
    YjsDocument,
)
from src.artifacts.schemas import (
    ArtifactCreate,
    ArtifactOut,
    ArtifactType,
    ArtifactVersionOut,
    DownloadUrlOut,
    InlineVersionCreate,
    ResolveOut,
    S3ObjectOut,
    UploadCompleteOut,
    UploadCreate,
    UploadOut,
    UsageOut,
    YjsCommitOut,
    YjsDocumentOut,
    YjsUpdateIn,
)
from src.artifacts.services.artifacts import ArtifactService
from src.artifacts.services.resolver import ArtifactResolver
from src.artifacts.services.s3 import S3AssetService
from src.artifacts.services.yjs import YjsService
from src.iam.middleware import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _yjs_out(row: YjsDocument) -> YjsDocumentOut:
    return YjsDocumentOut(
        id=row.id,
        artifact_id=row.artifact_id,
        state_base64=base64.b64encode(row.state).decode("ascii"),
        state_vector_base64=base64.b64encode(row.state_vector).decode("ascii"),
        update_count=row.update_count,
        last_compacted_at=row.last_compacted_at,
    )


def _artifact_url(cell_id: UUID, artifact_id: UUID, version_num: int) -> str:
    return f"artifact://{cell_id}/{artifact_id}/v{version_num}"


# ── literal routes FIRST (must not be captured by /{artifact_id}) ────────── #


@router.get("/usage", response_model=UsageOut)
async def get_storage_usage(
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> UsageOut:
    return UsageOut(cell_id=cell_id, bytes_total=await svc.usage_bytes(cell_id=cell_id))


@router.get("/resolve", response_model=ResolveOut)
async def resolve_artifact_url(
    url: str = Query(min_length=1, max_length=512),
    resolver: ArtifactResolver = Depends(get_artifact_resolver),
    cell_id: UUID = Depends(get_current_cell_id),
) -> ResolveOut:
    resolved = await resolver.resolve(url, current_cell_id=cell_id)
    return ResolveOut(
        artifact_id=resolved.artifact_id,
        cell_id=resolved.cell_id,
        artifact_type=resolved.artifact_type,
        title=resolved.title,
        version_num=resolved.version_num,
        storage_kind=resolved.storage_kind,
        byte_size=resolved.byte_size,
        content_hash_sha256=resolved.content_hash_sha256,
        content_inline=resolved.content_inline,
        download_url=resolved.download_url,
        yjs_state_base64=resolved.yjs_state_base64,
        artifact_url=_artifact_url(resolved.cell_id, resolved.artifact_id, resolved.version_num),
    )


@router.post(
    "/uploads/{s3_object_id}/complete",
    response_model=UploadCompleteOut,
    status_code=status.HTTP_201_CREATED,
)
async def complete_upload(
    s3_object_id: UUID,
    svc: S3AssetService = Depends(get_s3_asset_service),
    cell_id: UUID = Depends(get_current_cell_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> UploadCompleteOut:
    version, s3_object = await svc.complete_upload(
        cell_id=cell_id, s3_object_id=s3_object_id, created_by_user_id=auth.user.id
    )
    return UploadCompleteOut(
        version=ArtifactVersionOut.model_validate(version),
        s3_object=S3ObjectOut.model_validate(s3_object),
        artifact_url=_artifact_url(cell_id, version.artifact_id, version.version_num),
    )


@router.get("/uploads/{s3_object_id}/download-url", response_model=DownloadUrlOut)
async def get_download_url(
    s3_object_id: UUID,
    svc: S3AssetService = Depends(get_s3_asset_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> DownloadUrlOut:
    url = await svc.download_url(cell_id=cell_id, s3_object_id=s3_object_id)
    return DownloadUrlOut(url=url, expires_in_seconds=SIGNED_GET_TTL_SECONDS)


# ── envelope ────────────────────────────────────────────────────────────── #


@router.post("", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    payload: ArtifactCreate,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> ArtifactOut:
    artifact = await svc.create(
        cell_id=cell_id,
        artifact_type=payload.artifact_type,
        title=payload.title,
        tags=payload.tags,
        owner_user_id=auth.user.id,
        created_by_agent_id=payload.created_by_agent_id,
    )
    return ArtifactOut.model_validate(artifact)


@router.get("", response_model=list[ArtifactOut])
async def list_artifacts(
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
    artifact_type: ArtifactType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ArtifactOut]:
    rows = await svc.list(cell_id=cell_id, artifact_type=artifact_type, limit=limit, offset=offset)
    return [ArtifactOut.model_validate(row) for row in rows]


@router.get("/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(
    artifact_id: UUID,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> ArtifactOut:
    return ArtifactOut.model_validate(await svc.get(cell_id=cell_id, artifact_id=artifact_id))


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> None:
    await svc.soft_delete(cell_id=cell_id, artifact_id=artifact_id)


# ── versions ────────────────────────────────────────────────────────────── #


@router.post(
    "/{artifact_id}/versions",
    response_model=ArtifactVersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_inline_version(
    artifact_id: UUID,
    payload: InlineVersionCreate,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> ArtifactVersionOut:
    version = await svc.create_inline_version(
        cell_id=cell_id,
        artifact_id=artifact_id,
        content=payload.content,
        text_export=payload.text_export,
        created_by_user_id=auth.user.id,
    )
    return ArtifactVersionOut.model_validate(version)


@router.get("/{artifact_id}/versions", response_model=list[ArtifactVersionOut])
async def list_versions(
    artifact_id: UUID,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> list[ArtifactVersionOut]:
    rows = await svc.list_versions(cell_id=cell_id, artifact_id=artifact_id)
    return [ArtifactVersionOut.model_validate(row) for row in rows]


@router.get("/{artifact_id}/versions/{version_num}", response_model=ArtifactVersionOut)
async def get_version(
    artifact_id: UUID,
    version_num: int,
    svc: ArtifactService = Depends(get_artifact_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> ArtifactVersionOut:
    version = await svc.get_version(
        cell_id=cell_id, artifact_id=artifact_id, version_num=version_num
    )
    return ArtifactVersionOut.model_validate(version)


# ── Yjs (REST-only persistence, Wave 1) ─────────────────────────────────── #


@router.post(
    "/{artifact_id}/yjs", response_model=YjsDocumentOut, status_code=status.HTTP_201_CREATED
)
async def create_yjs_document(
    artifact_id: UUID,
    svc: YjsService = Depends(get_yjs_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> YjsDocumentOut:
    return _yjs_out(await svc.create_document(cell_id=cell_id, artifact_id=artifact_id))


@router.get("/{artifact_id}/yjs", response_model=YjsDocumentOut)
async def get_yjs_document(
    artifact_id: UUID,
    svc: YjsService = Depends(get_yjs_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> YjsDocumentOut:
    return _yjs_out(await svc.get_document(cell_id=cell_id, artifact_id=artifact_id))


@router.post("/{artifact_id}/yjs/updates", response_model=YjsDocumentOut)
async def apply_yjs_update(
    artifact_id: UUID,
    payload: YjsUpdateIn,
    svc: YjsService = Depends(get_yjs_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> YjsDocumentOut:
    try:
        update_data = payload.decoded()
    except ValueError as exc:  # pydantic validated once; defensive re-check
        raise InvalidYjsUpdate(str(exc)) from exc
    row = await svc.apply_update(cell_id=cell_id, artifact_id=artifact_id, update_data=update_data)
    return _yjs_out(row)


@router.post(
    "/{artifact_id}/yjs/commit",
    response_model=YjsCommitOut,
    status_code=status.HTTP_201_CREATED,
)
async def commit_yjs_version(
    artifact_id: UUID,
    svc: YjsService = Depends(get_yjs_service),
    cell_id: UUID = Depends(get_current_cell_id),
    auth: AuthenticatedUser = Depends(get_current_user),
) -> YjsCommitOut:
    version, snapshot = await svc.commit_version(
        cell_id=cell_id, artifact_id=artifact_id, created_by_user_id=auth.user.id
    )
    return YjsCommitOut(
        version=ArtifactVersionOut.model_validate(version),
        snapshot_id=snapshot.id,
        artifact_url=_artifact_url(cell_id, artifact_id, version.version_num),
    )


# ── S3 uploads (presign) ────────────────────────────────────────────────── #


@router.post(
    "/{artifact_id}/uploads", response_model=UploadOut, status_code=status.HTTP_201_CREATED
)
async def presign_upload(
    artifact_id: UUID,
    payload: UploadCreate,
    svc: S3AssetService = Depends(get_s3_asset_service),
    cell_id: UUID = Depends(get_current_cell_id),
) -> UploadOut:
    row, presigned = await svc.presign_upload(
        cell_id=cell_id,
        artifact_id=artifact_id,
        filename=payload.filename,
        mime_type=payload.mime_type,
    )
    fields = presigned.get("fields")
    return UploadOut(
        s3_object_id=row.id,
        bucket=row.bucket,
        s3_key=row.s3_key,
        upload_url=str(presigned.get("url", "")),
        upload_fields=dict(fields) if isinstance(fields, dict) else {},
        expires_in_seconds=PRESIGN_POST_TTL_SECONDS,
    )
