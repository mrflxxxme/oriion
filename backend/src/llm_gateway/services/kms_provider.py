"""Pluggable KMS abstraction for BYOK custody.

Per ADR-014 amendment 2026-05-19 (KMSProvider local→Yandex transition):

    Wave 0:  LocalAESKMS (AES-256-GCM with env-supplied master key)
    Wave 1+: YandexKMS   (envelope encryption via Yandex KMS API)

The factory ``get_kms_provider()`` reads ``KMS_BACKEND`` from env (default
'local') so the rest of the codebase depends only on the Protocol.

Ciphertext format (LocalAESKMS):
    nonce(12 bytes) || ciphertext || gcm_tag(16 bytes)

This is the canonical AES-GCM packing — both nonce and tag are required for
decryption. Any tampering with any byte triggers `InvalidTag` (mapped to
KMSError) on decrypt.
"""

from __future__ import annotations

import base64
import os
import secrets
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.llm_gateway.exceptions import KMSError

_NONCE_BYTES = 12  # AES-GCM standard nonce length


class KMSProvider(Protocol):
    """KMS abstraction. Async to keep Wave 1+ Yandex KMS API swap painless."""

    async def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext to opaque ciphertext blob.

        Implementations MUST embed any IV/nonce/auth-tag inside the returned
        bytes — the caller stores a single column ``key_encrypted bytea``.
        """
        ...

    async def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt blob produced by ``encrypt``. Raise KMSError on tamper."""
        ...


class LocalAESKMS:
    """AES-256-GCM with a single env-provided master key.

    NOT for production. Used Wave 0 for fast local dev + CI; replaced by
    YandexKMS in Wave 1+ (envelope encryption).

    Master key sourcing precedence:
        1. constructor `master_key` arg (tests)
        2. env BYOK_MASTER_KEY_B64 (base64-encoded 32 bytes)
        3. ValueError if neither — explicit-failure rather than silent insecure.
    """

    def __init__(self, master_key: bytes | None = None) -> None:
        if master_key is None:
            b64 = os.environ.get("BYOK_MASTER_KEY_B64")
            if not b64:
                raise ValueError(
                    "LocalAESKMS requires BYOK_MASTER_KEY_B64 env (32 bytes b64) "
                    "or explicit master_key constructor arg."
                )
            master_key = base64.b64decode(b64)
        if len(master_key) != 32:
            raise ValueError(
                f"AES-256-GCM master key must be exactly 32 bytes; got {len(master_key)}."
            )
        self._aesgcm = AESGCM(master_key)

    async def encrypt(self, plaintext: bytes) -> bytes:
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ct_and_tag = self._aesgcm.encrypt(nonce, plaintext, associated_data=None)
        return nonce + ct_and_tag

    async def decrypt(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) < _NONCE_BYTES + 16:
            raise KMSError("ciphertext too short — missing nonce or auth tag")
        nonce = ciphertext[:_NONCE_BYTES]
        ct_and_tag = ciphertext[_NONCE_BYTES:]
        try:
            return self._aesgcm.decrypt(nonce, ct_and_tag, associated_data=None)
        except InvalidTag as exc:
            raise KMSError("AES-GCM authentication failed — ciphertext tampered") from exc


class YandexKMS:
    """Wave 1+ stub. Raises NotImplementedError until envelope encryption lands."""

    async def encrypt(self, plaintext: bytes) -> bytes:
        raise NotImplementedError("YandexKMS lands Wave 1+ (Phase 00.6 deploy task).")

    async def decrypt(self, ciphertext: bytes) -> bytes:
        raise NotImplementedError("YandexKMS lands Wave 1+ (Phase 00.6 deploy task).")


def get_kms_provider() -> KMSProvider:
    """Factory — selects KMS backend via ``KMS_BACKEND`` env (default 'local')."""
    backend = os.environ.get("KMS_BACKEND", "local").lower()
    if backend == "yandex":
        return YandexKMS()
    if backend == "local":
        return LocalAESKMS()
    raise ValueError(f"Unknown KMS_BACKEND={backend!r}; expected 'local' or 'yandex'.")
