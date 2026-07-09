"""Application settings loaded from environment.

Single source of truth for runtime config across all bounded contexts. Read
once at process start; never mutated. Env-vars documented in `.env.example`.

Phase 00.2 introduces auth-related settings (JWT, refresh TTL, rate-limit,
email-verification gate). Production secrets are sourced from YC Lockbox in
Wave 1+; Wave 0 uses literal env-vars.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from src._shared.lockbox import fetch_lockbox_secrets

# Known dev-only defaults — referenced by the field defaults AND the
# staging/prod guard (_guard_no_dev_secrets) so the cutover to Lockbox-only
# secrets fails fast if a real secret didn't land (AC-W1-9).
_DEV_JWT_DEFAULT = "changeme-dev-only-please-replace-in-prod-min-32-chars"
_DEV_DATABASE_URL = "postgresql+asyncpg://oriion:oriion-dev@localhost:5432/oriion_dev"


class LockboxSettingsSource(PydanticBaseSettingsSource):
    """pydantic-settings source that loads secrets from YC Lockbox (AC-W1-9).

    No-op unless ``LOCKBOX_SECRET_ID`` is set in the environment, so dev / test /
    CI (which never set it) construct ``Settings`` with no network call. When it
    IS set, the Lockbox payload keys (case-insensitive) populate matching
    ``Settings`` fields. It sits BELOW the env source, so an explicit env-var
    still wins (break-glass override); above it, secrets come from Lockbox so
    nothing has to be written to the VM disk.
    """

    def get_field_value(self, _field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Required abstract override but unused — __call__ returns the whole
        # Lockbox payload in one shot, bypassing per-field resolution.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        secret_id = os.environ.get("LOCKBOX_SECRET_ID", "").strip()
        if not secret_id:
            return {}
        iam_token = os.environ.get("LOCKBOX_IAM_TOKEN", "").strip() or None
        endpoint = os.environ.get("LOCKBOX_ENDPOINT", "").strip() or None
        secrets = fetch_lockbox_secrets(secret_id, iam_token=iam_token, endpoint=endpoint)
        # Lower-case keys so they map to Settings fields (case_sensitive=False).
        return {key.lower(): value for key, value in secrets.items()}


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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Insert the YC Lockbox source below env/dotenv (AC-W1-9): explicit
        env-vars override (break-glass), otherwise prod secrets come from Lockbox
        with nothing written to disk. No-op unless LOCKBOX_SECRET_ID is set."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            LockboxSettingsSource(settings_cls),
            file_secret_settings,
        )

    # ── Runtime mode ────────────────────────────────────────────────────
    app_env: Literal["dev", "test", "staging", "prod"] = Field(
        default="dev",
        description="Active deployment environment. Affects log renderer and dev-stub behaviour.",
    )

    # ── Secrets backend (AC-W1-9 — YC Lockbox direct-read) ──────────────
    lockbox_secret_id: str = Field(
        default="",
        description=(
            "YC Lockbox secret id. When set, the backend reads its secrets "
            "DIRECTLY from Lockbox at startup (no on-disk .env) via the payload "
            "REST API — see _shared/lockbox.py. Empty = pure env/.env (dev/test)."
        ),
    )
    lockbox_endpoint: str = Field(
        default="",
        description="Override the Lockbox payload API base URL (empty = YC default).",
    )

    # ── Storage ──────────────────────────────────────────────────────────
    database_url: SecretStr = Field(
        default=SecretStr(_DEV_DATABASE_URL),
        description=(
            "Async DSN consumed by SQLAlchemy AsyncEngine + alembic env.py. SecretStr "
            "so the embedded password can't leak via repr/logs; call .get_secret_value() "
            "only at the engine call site."
        ),
    )
    redis_url: SecretStr = Field(
        default=SecretStr("redis://localhost:6379/0"),
        description=(
            "Redis DSN (SecretStr — may embed a password). Used for rate-limit + JWT "
            "blacklist + (future) event streams."
        ),
    )
    sse_backend: Literal["inprocess", "redis"] = Field(
        default="inprocess",
        description=(
            "SSE publisher backing store. 'inprocess' (default) keeps the Wave-0 "
            "asyncio.Queue publisher — required for deterministic CI + single-worker "
            "dev. 'redis' selects the Redis-Streams publisher so events survive a "
            "multi-worker / out-of-process Dramatiq dispatch (AC-W1-1 / AC-W1-16a); "
            "docker + staging set SSE_BACKEND=redis on both the web and worker "
            "services so they share per-task streams."
        ),
    )
    sse_redis_poll_fallback: bool = Field(
        default=False,
        description=(
            "When True, RedisSSEPublisher.subscribe uses non-blocking XREAD + "
            "asyncio.sleep polling instead of XREAD BLOCK. Needed where the Redis "
            "implementation lacks BLOCK support (e.g. fakeredis in tests); "
            "production uses real BLOCK for low latency."
        ),
    )

    # ── JWT (Phase 00.2) ────────────────────────────────────────────────
    jwt_secret_access_v1: SecretStr = Field(
        default=SecretStr(_DEV_JWT_DEFAULT),
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

    # ── SMTP outbound email (Phase 01.8 — Yandex 360 SMTP, ADR-007) ──────
    # Real transactional email for the mandatory email-verification gate
    # (ADR-007: "email verification mandatory before first task"). Prod today
    # is NoOpEmailSender; the YandexSmtpEmailSender activates ONLY when
    # smtp_user AND smtp_password are configured (see is_smtp_configured), so a
    # credential-less prod boot keeps the NoOp fallback and does NOT crash. The
    # deferred-live-send contract holds: creds are NOT in the canonical .env yet.
    smtp_host: str = Field(
        default="smtp.yandex.ru",
        description="SMTP server host. Yandex 360 = smtp.yandex.ru.",
    )
    smtp_port: int = Field(
        default=465,
        description=(
            "SMTP server port. 465 = implicit TLS (SSL-on-connect, the "
            "smtp_use_tls default); 587 = STARTTLS (set smtp_use_tls=False)."
        ),
    )
    smtp_use_tls: bool = Field(
        default=True,
        description=(
            "True → implicit TLS (SSL on connect, port 465). False → STARTTLS "
            "upgrade on a cleartext port (587). Auth NEVER travels unencrypted: "
            "with STARTTLS the sender REQUIRES a successful TLS upgrade before "
            "AUTH (aiosmtplib start_tls) — no plaintext-auth fallback."
        ),
    )
    smtp_user: str = Field(
        default="",
        description=(
            "SMTP auth username (full Yandex 360 mailbox, e.g. no-reply@profiki.online). "
            "Empty = SMTP not configured → sender selection falls back to NoOp."
        ),
    )
    smtp_password: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "SMTP app-password (SecretStr — never logged/repr'd). Yandex 360 "
            "requires a per-application password, NOT the account password. "
            "Provisioned via YC Lockbox (prod) / .env (dev); NOT present now. "
            "Empty = SMTP not configured → sender selection falls back to NoOp."
        ),
    )
    smtp_from: str = Field(
        default="",
        description=(
            "RFC-5322 From address for outbound mail. Empty → falls back to "
            "smtp_user. Yandex rejects a From that doesn't match an owned mailbox."
        ),
    )
    smtp_timeout_seconds: float = Field(
        default=30.0,
        description="Per-send socket timeout (seconds) for the aiosmtplib client.",
    )
    email_verify_url_base: str = Field(
        default="",
        description=(
            "Optional public base URL for the verification/reset flow (e.g. "
            "https://app.profiki.online). When set, the email body includes a full "
            "clickable link (<base>/auth/verify-email?token=…); when empty the "
            "body carries the bare token + the API path, matching "
            "ConsoleEmailSender semantics."
        ),
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

    # ── LLM providers (Phase 00.5b — DeepSeek/YandexGPT/GigaChat DI) ─────
    # All credentials default to empty SecretStr so app boot does NOT require
    # them — providers are constructed regardless and fail at request-time if
    # the credential is missing. The router_service failover chain skips
    # providers whose circuit is OPEN, so an empty key simply means that
    # provider is permanently failed-over until a key is supplied.
    deepseek_api_key: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "DeepSeek Bearer API key. Provisioned per environment via "
            "YC Lockbox (Wave 1+) or .env (Wave 0 dev/staging). Empty in test."
        ),
    )
    yandex_api_key: str | None = Field(
        default=None,
        description=(
            "Yandex Cloud API key (Api-Key auth scheme). PREFERRED over the "
            "IAM token: a static API key does not expire, whereas IAM tokens "
            "have a ~12h TTL and need `yc iam create-token` rotation. When set, "
            "YandexGPTProvider sends `Authorization: Api-Key <key>`."
        ),
    )
    yandex_iam_token: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Yandex Cloud IAM token (Bearer) — LEGACY / failover when "
            "yandex_api_key is unset. ~12h TTL; rotate via `yc iam create-token`. "
            "Prefer yandex_api_key (Api-Key scheme, non-expiring)."
        ),
    )
    yandex_catalog_id: str = Field(
        default="TBD_YANDEX_CATALOG_ID",
        description=(
            "Yandex Cloud catalog (folder) id used in the modelUri scheme: "
            "`gpt://<catalog_id>/<model>/latest`. Required when "
            "yandex_iam_token is set."
        ),
    )
    gigachat_auth_key: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Sber GigaChat Basic auth key (base64-encoded `client_id:client_secret`). "
            "Used by GigaChatProvider to obtain OAuth tokens on demand."
        ),
    )
    gigachat_verify_ssl: bool = Field(
        default=True,
        description=(
            "TLS verification for GigaChat's httpx clients. Keep True in all real "
            "environments. False is a dev-only escape hatch for hosts missing the "
            "Russian Trusted Root CA (AC-W1-21) — prefer GIGACHAT_CA_BUNDLE instead."
        ),
    )
    gigachat_ca_bundle: str = Field(
        default="",
        description=(
            "Path to a CA bundle that includes the Russian Trusted Root CA, which "
            "signs *.sberbank.ru. httpx/certifi does NOT read the system store, so "
            "the prod image sets this to /etc/ssl/certs/ca-certificates.crt (where "
            "the Dockerfile installs the RU CA via update-ca-certificates). Empty = "
            "fall back to gigachat_verify_ssl (certifi default bundle). AC-W1-21."
        ),
    )
    llm_provider_timeout_seconds: float = Field(
        default=120.0,
        description=(
            "Per-call httpx timeout (seconds) shared by all LLM providers "
            "(DeepSeek / YandexGPT / GigaChat). Raised from the 30s provider "
            "default because long-form writer generation (≥1500-word brief, "
            "AC-W1-22) exceeds 30s and tripped a ReadTimeout that cascaded into "
            "spurious failover. Aligned with AC8 cohort p95 ≤120s. Surfaced by "
            "Phase 01.1 Track A live validation."
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

    # ── Security guardrails (Phase 01.6 — ADR-039; activated 01.9a, ADR-040 D10) ──
    security_injection_scan_enabled: bool = Field(
        default=True,
        description=(
            "When True, external content (web_search / read_url results) is run "
            "through the heuristic prompt-injection scanner and flagged fragments "
            "are B1-neutralized before reaching an agent. Default True since 01.9a: "
            "the scanner is a conservative no-op on benign content (the trimmed "
            "high-confidence heuristics passed the adversarial audit) and it guards "
            "the only external channel (web results) that becomes live-facing as "
            "connectors open in 01.9b. See ADR-039 §4 + ADR-040 D10."
        ),
    )
    security_dlp_enabled: bool = Field(
        default=True,
        description=(
            "When True, the output-DLP guard A3-hard-blocks a task whose final "
            "deliverable contains RU-PDN (INN/SNILS/passport/phone/email). Default "
            "True since 01.9a: the INN-10 detector is precision-tuned to context "
            "(FP ≤1% on the golden corpus, DV-04/DV-05) so activation no longer "
            "carries false-positive friction, and DLP must be live before the first "
            "outward connector surface (01.9b). See ADR-039 §4 + ADR-040 D10."
        ),
    )

    # ── Observability (Phase 00.6) ──────────────────────────────────────
    otel_service_name: str = Field(
        default="oriion-backend",
        description="OpenTelemetry service.name resource attribute. Surfaces in Tempo trace UI.",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://otel-collector:4317",
        description=(
            "OTLP gRPC endpoint of the collector. Staging value points at the "
            "in-stack otel-collector container (docker-compose.staging.yml). "
            "Empty string DISABLES exporter (unit/integration tests run with "
            "in-memory span exporter via setup_otel's no-op branch)."
        ),
    )
    otel_traces_enabled: bool = Field(
        default=True,
        description=(
            "Master kill-switch для OpenTelemetry instrumentation. Set False "
            "to short-circuit setup_otel() — useful in unit-test contexts that "
            "don't need an exporter and want fastest startup."
        ),
    )
    worker_metrics_port: int = Field(
        default=9191,
        description=(
            "TCP port the Dramatiq dispatch worker exposes Prometheus /metrics on "
            "(AC-W1-13). Under async dispatch the orchestration runs in the worker "
            "process, so its llm_*/task_* counters live in a SEPARATE registry from "
            "the web tier — Prometheus scrapes worker:9191 in addition to "
            "backend:8000/metrics. Set to 0 to disable the worker exporter (e.g. "
            "a constrained dev box); the actor still runs, just unscraped."
        ),
    )
    log_format: Literal["auto", "json", "console"] = Field(
        default="auto",
        description=(
            "structlog renderer selection. 'auto' = JSON в staging/prod, "
            "ConsoleRenderer в dev/test (legacy behaviour). 'json' force-overrides "
            "так что docker-compose-staging-local stack can emit Loki-parseable "
            "JSON even with app_env=dev. 'console' force-overrides для local "
            "human-debug runs."
        ),
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

    @property
    def is_smtp_configured(self) -> bool:
        """True when real SMTP creds are present (Phase 01.8).

        Both the username AND app-password must be non-empty. Sender selection
        (iam/deps.py::get_email_sender) uses this to pick YandexSmtpEmailSender
        over NoOpEmailSender — so a credential-less prod boot keeps the NoOp
        fallback and the deferred-live-send contract (ADR-007) holds without a
        crash.
        """
        return bool(self.smtp_user) and bool(self.smtp_password.get_secret_value())

    @property
    def smtp_sender_address(self) -> str:
        """Effective From address — smtp_from if set, else the auth user."""
        return self.smtp_from or self.smtp_user

    @model_validator(mode="after")
    def _guard_no_dev_secrets(self) -> Settings:
        """Fail fast if staging/prod boots on a known dev-default secret (AC-W1-9).

        This makes retiring the on-disk ``.env`` safe: if the YC Lockbox payload
        is missing a critical secret it would otherwise fall back to the Settings
        dev-default and boot *healthy-but-insecure* (e.g. the dev JWT secret). The
        deploy's wait_healthy/smoke then surfaces this as a failed deploy instead.
        Dev/test are exempt (they intentionally run on the defaults)."""
        if self.app_env not in ("staging", "prod"):
            return self
        problems: list[str] = []
        if self.jwt_secret_access_v1.get_secret_value() == _DEV_JWT_DEFAULT:
            problems.append("JWT_SECRET_ACCESS_V1 is the dev default")
        if not self.byok_master_key_b64.get_secret_value():
            problems.append("BYOK_MASTER_KEY_B64 is empty")
        if self.database_url.get_secret_value() == _DEV_DATABASE_URL:
            problems.append("DATABASE_URL is the dev default")
        if problems:
            raise ValueError(
                f"insecure config in app_env={self.app_env!r}: {'; '.join(problems)}. "
                "Provide real secrets via YC Lockbox (LOCKBOX_SECRET_ID) or env. AC-W1-9."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor — Settings is immutable across the process lifetime."""
    return Settings()


def reload_settings() -> Settings:
    """Drop the cached Settings and rebuild from all sources, re-reading YC
    Lockbox (AC-W1-9 no-redeploy refresh). Returns the fresh instance — callers
    that hold secret-derived state (LLM provider clients, KMS) must rebuild it
    from the returned Settings. NOTE: this re-runs the LockboxSettingsSource, so
    it performs a network fetch when LOCKBOX_SECRET_ID is set."""
    get_settings.cache_clear()
    return get_settings()
