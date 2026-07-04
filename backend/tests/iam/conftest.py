"""iam-specific pytest fixtures.

In-memory fakes for Redis + the EmailSender + a fast Argon2 hasher so the
unit suite runs under a second without docker.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import pytest
from argon2 import PasswordHasher
from src._shared.config import Settings
from src.iam.services.email_service import InMemoryEmailSender
from src.iam.services.password_service import PasswordService
from src.iam.services.rate_limit_service import RateLimitService
from src.iam.services.token_service import TokenService
from src.llm_gateway.services.kms_provider import LocalAESKMS

# ── Fake Redis ────────────────────────────────────────────────────────────


class FakeRedis:
    """Minimal in-process Redis stand-in covering the calls iam uses:
    SET ex, EXISTS, EVAL (with the Lua script in rate_limit_service)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expiry: dict[str, float] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [k for k, t in self._expiry.items() if t <= now]
        for k in expired:
            self._store.pop(k, None)
            self._expiry.pop(k, None)

    async def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self._purge()
        self._store[name] = value
        if ex is not None:
            self._expiry[name] = time.monotonic() + ex
        return True

    async def exists(self, *keys: str) -> int:
        self._purge()
        return sum(1 for k in keys if k in self._store)

    async def eval(self, script: str, numkeys: int, *args: Any) -> Any:
        """Emulate the INCR+EXPIRE-on-first-hit Lua script used by RateLimitService."""
        self._purge()
        key = args[0]
        window_seconds = int(args[1])
        current = int(self._store.get(key, "0")) + 1
        self._store[key] = str(current)
        if current == 1:
            self._expiry[key] = time.monotonic() + window_seconds
        ttl = max(int(self._expiry.get(key, 0) - time.monotonic()), 0)
        return [current, ttl]


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


# ── Fast Argon2 hasher (for sub-second test suites) ──────────────────────


@pytest.fixture(scope="session")
def fast_password_hasher() -> PasswordHasher:
    return PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


@pytest.fixture
def password_service(fast_password_hasher: PasswordHasher) -> PasswordService:
    return PasswordService(hasher=fast_password_hasher)


# ── Settings (deterministic, dev-mode) ───────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        # Fake test secret — not a real credential. gitleaks:allow
        jwt_secret_access_v1=("test-" + "fake-" * 8).rstrip("-"),  # type: ignore[arg-type]
        jwt_iss="oriion-iam",
        jwt_aud="oriion-app",
        jwt_access_ttl_seconds=900,
        refresh_ttl_seconds=604800,
        require_email_verification=False,
        consent_version_current="test-2026-05",
        rate_limit_window_seconds=900,
    )


# ── Token + rate-limit services using fake redis ──────────────────────────


@pytest.fixture
def token_service(settings: Settings, fake_redis: FakeRedis) -> TokenService:
    return TokenService(settings=settings, redis=fake_redis)  # type: ignore[arg-type]


@pytest.fixture
def rate_limit_service(fake_redis: FakeRedis) -> RateLimitService:
    return RateLimitService(redis=fake_redis)  # type: ignore[arg-type]


# ── Email sender ─────────────────────────────────────────────────────────


@pytest.fixture
def email_sender() -> Iterator[InMemoryEmailSender]:
    sender = InMemoryEmailSender()
    yield sender
    sender.clear()


# ── KMS (deterministic local AES for TOTP at-rest encryption tests) ────────


@pytest.fixture
def local_kms() -> LocalAESKMS:
    """LocalAESKMS with a fixed 32-byte master key — no env var needed.

    Encrypts the TOTP secret at rest exactly like production (AES-256-GCM),
    so unit tests exercise the real encrypt/decrypt round-trip.
    """
    return LocalAESKMS(master_key=b"unit-test-totp-master-key-32bytes"[:32].ljust(32, b"0"))
