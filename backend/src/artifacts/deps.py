"""FastAPI DI for the artifacts API — RLS session + repositories + services."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import get_tenant_db_session
from src.artifacts.config import ArtifactsSettings, get_artifacts_settings
from src.artifacts.ports import ObjectStoragePort
from src.artifacts.repositories.artifact_repository import ArtifactRepository, UsageRepository
from src.artifacts.repositories.s3_repository import S3ObjectRepository
from src.artifacts.repositories.yjs_repository import YjsRepository
from src.artifacts.services.artifacts import ArtifactService
from src.artifacts.services.resolver import ArtifactResolver
from src.artifacts.services.s3 import Boto3ObjectStorage, S3AssetService
from src.artifacts.services.yjs import YjsService


@lru_cache(maxsize=1)
def get_object_storage() -> ObjectStoragePort:
    """Process-wide boto3 adapter (client is created lazily on first call)."""
    settings = get_artifacts_settings()
    return Boto3ObjectStorage(
        endpoint_url=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key.get_secret_value(),
        region_name=settings.minio_region,
    )


def get_artifact_service(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> ArtifactService:
    return ArtifactService(ArtifactRepository(db), UsageRepository(db), S3ObjectRepository(db))


def get_yjs_service(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> YjsService:
    return YjsService(YjsRepository(db), ArtifactRepository(db), UsageRepository(db))


def _build_s3_service(db: AsyncSession, settings: ArtifactsSettings) -> S3AssetService:
    return S3AssetService(
        S3ObjectRepository(db),
        ArtifactRepository(db),
        UsageRepository(db),
        get_object_storage(),
        bucket=settings.artifacts_s3_bucket,
        env_prefix=settings.artifacts_s3_env,
        max_upload_bytes=settings.artifacts_max_upload_bytes,
    )


def get_s3_asset_service(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> S3AssetService:
    return _build_s3_service(db, get_artifacts_settings())


def get_artifact_resolver(
    db: AsyncSession = Depends(get_tenant_db_session),
) -> ArtifactResolver:
    return ArtifactResolver(
        ArtifactRepository(db),
        YjsRepository(db),
        _build_s3_service(db, get_artifacts_settings()),
    )
