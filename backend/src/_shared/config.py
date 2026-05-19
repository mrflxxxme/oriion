"""Application settings loaded from environment.

Single source of truth for runtime config across all bounded contexts. Read
once at process start; never mutated. Env-vars documented in `.env.example`.

Phase 00.2 introduces auth-related settings (JWT, refresh TTL, rate-limit,
email-verification gate). Production secrets are sourced from YC Lockbox in
Wave 1+; Wave 0 uses literal env-vars.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide configuration.

    Loaded from environment (and `.env` file in dev). `case_sensitive=False`
    so `DATABASE_URL`, `Database_URL`, and `database_url` all resolve.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Runtime mode ────────────────────────────────────────────────────
    app_env: Literal["dev", "test", "staging", "prod"] = Field(
        default="dev",
        description="Active deployment environment. Affects log renderer and dev-stub behaviour.",
    )

    # ── Storage ──────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://oriion:oriion-dev@localhost:5432/oriion_dev",
        description="Async DSN consumed by SQLAlchemy AsyncEngine + alembic env.py.",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis DSN. Used for rate-limit + JWT blacklist + (future) event streams.",
    )

    # ── JWT (Phase 00.2) ────────────────────────────────────────────────
    jwt_secret_access_v1: SecretStr = Field(
        default=SecretStr("changeme-dev-only-please-replace-in-prod-min-32-chars"),
        description="HS256 signing secret for access tokens. Rotate quarterly via _V2 alongside _V1.",
    )
    jwt_iss: str = Field(default="oriion-iam", description="JWT iss claim literal.")
    jwt_aud: str = Field(default="oriion-app", description="JWT aud claim literal.")
    jwt_access_ttl_seconds: int = Field(
        default=900, description="Access token TTL (default 15 min per ADR-014)."
    )
    refresh_ttl_seconds: int = Field(
        default=604800, description="Refresh token TTL (default 7 days per ADR-014)."
    )

    # ── Email verification gate (Phase 00.2) ────────────────────────────
    require_email_verification: bool = Field(
        default=False,
        description=(
            "Gate flag: True in prod (login blocks until email verified); "
            "False in dev (login allowed; console email-sender writes token to log)."
        ),
    )
    consent_version_current: str = Field(
        default="2026-05-17",
        description="Privacy-policy version pinned at consent grant (FZ-152 invariant 6).",
    )

    # ── Rate-limit (Phase 00.2) ─────────────────────────────────────────
    rate_limit_window_seconds: int = Field(
        default=900,
        description="Default sliding-window length (15 min) for (ip,email)-keyed limits.",
    )

    # ── BYOK + KMS (Phase 00.4) ─────────────────────────────────────────
    kms_backend: Literal["local", "yandex"] = Field(
        default="local",
        description=(
            "KMS provider for BYOK envelope encryption. Wave 0: 'local' "
            "(LocalAESKMS using BYOK_MASTER_KEY_B64). Phase 00.6+: 'yandex' "
            "(Yandex Cloud KMS managed key). See ADR-014 amendment 2026-05-19."
        ),
    )
    byok_master_key_b64: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Base64-encoded 32-byte AES-256 master key for LocalAESKMS. "
            "Required when kms_backend='local'. Generate via "
            "`openssl rand -base64 32`. NEVER commit. Replaced by Yandex KMS "
            "managed key (TBD_YANDEX_CLOUD_KMS_KEY_ID) in Phase 00.6."
        ),
    )
    yandex_cloud_kms_key_id: str = Field(
        default="TBD_YANDEX_CLOUD_KMS_KEY_ID",
        description="Yandex Cloud KMS master key id (used when kms_backend='yandex').",
    )

    # ── FX rate (Phase 00.4 — RU-currency billing per ADR-018 amendment) ─
    fx_rate_usd_to_rub: float = Field(
        default=100.0,
        description=(
            "Pinned FX rate USD→RUB for Wave 0 LLM cost ledger. "
            "Phase 00.6 deploy may override per environment. "
            "Wave 1+ replaces with live CBR feed cached 1h."
        ),
    )

    # ── MCP tools (Phase 00.4 — web_search + read_url) ──────────────────
    web_search_mock_mode: bool = Field(
        default=True,
        description=(
            "When True, web_search tool returns canned results without "
            "calling Brave / Yandex Search. Default True in dev for "
            "deterministic tests; set False once provider keys provisioned."
        ),
    )
    brave_search_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Brave Search API key. Used by mcp.tools.web_search when mock_mode=false.",
    )
    yandex_search_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Yandex Search API key. Fallback backend for mcp.tools.web_search.",
    )

    # ── Helpers ─────────────────────────────────────────────────────────
    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor — Settings is immutable across the process lifetime."""
    return Settings()
