"""Password hashing service.

argon2id (contracts/iam/schema.sql invariant 2 + ADR-024 authoritative).
argon2-cffi PasswordHasher defaults match OWASP 2024 baseline:
    time_cost=3, memory_cost=64 MB, parallelism=4, hash_len=32, salt_len=16.

Tests inject a faster hasher (memory_cost=1024) via DI to keep the suite
under a second; production uses the default values.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

DEFAULT_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


class PasswordService:
    """Hash + verify + needs-rehash check for user passwords."""

    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self._hasher = hasher or DEFAULT_HASHER

    def hash(self, plaintext: str) -> str:
        """Return an argon2id PHC-format hash."""
        return self._hasher.hash(plaintext)

    def verify(self, stored_hash: str, plaintext: str) -> bool:
        """Constant-time compare. Returns False on mismatch; raises on
        malformed hash (caller treated as InvalidCredentials)."""
        try:
            return self._hasher.verify(stored_hash, plaintext)
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, stored_hash: str) -> bool:
        """True when the hash uses older argon2 params than the current
        hasher — caller should re-hash on next successful login."""
        return self._hasher.check_needs_rehash(stored_hash)
