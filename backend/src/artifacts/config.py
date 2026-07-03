"""Artifacts context settings — S3/MinIO endpoint + bucket + key prefix.

Env-var names match ``infra/docker-compose.dev.yml`` (MINIO_ENDPOINT /
MINIO_ACCESS_KEY / MINIO_SECRET_KEY). Defaults are the dev-compose values —
staging/prod MUST override via env (Yandex Object Storage endpoint + real
keys); they carry no production secret.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ArtifactsSettings(BaseSettings):
    """S3-compatible object storage wiring for the artifacts context."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    minio_endpoint: str = Field(
        default="http://localhost:9000",
        description="S3-compatible endpoint (dev: MinIO; prod: Yandex Object Storage).",
    )
    minio_access_key: str = Field(default="oriion")
    # Dev-compose default, NOT a production secret (mirrors infra/docker-compose.dev.yml).
    minio_secret_key: SecretStr = Field(default=SecretStr("oriion-dev-s3"))
    minio_region: str = Field(
        default="ru-central1",
        description="Region for SigV4 signing (MinIO accepts any; YOS wants ru-central1).",
    )
    artifacts_s3_bucket: str = Field(
        default="oriion-artifacts-dev",
        description="Bucket for artifact assets (per-env bucket, never public).",
    )
    artifacts_s3_env: str = Field(
        default="dev",
        description="Key prefix env segment: <env>/<cell_id>/<artifact_id>/<vN>/<filename>.",
    )
    artifacts_max_upload_bytes: int = Field(
        default=100 * 1024 * 1024,
        description="content-length-range cap embedded in the presigned POST policy.",
    )


@lru_cache(maxsize=1)
def get_artifacts_settings() -> ArtifactsSettings:
    """Process-wide cached settings (read once, never mutated)."""
    return ArtifactsSettings()
