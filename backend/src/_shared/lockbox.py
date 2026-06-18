"""Yandex Cloud Lockbox secret reader (AC-W1-9).

Reads the backend's secrets DIRECTLY from YC Lockbox at process start via the
Lockbox **payload REST API** (httpx — no heavy gRPC SDK is pulled in), so
secrets never have to land on the VM disk: the deploy stops materializing
``/opt/oriion/.env`` and instead sets ``LOCKBOX_SECRET_ID``; the backend reads
the payload itself (wired as a pydantic-settings source — see
``_shared/config.py``).

Auth — a short-lived IAM token:
* On a YC VM the instance service account's token is fetched from the metadata
  endpoint (nothing stored on disk).
* An explicit ``LOCKBOX_IAM_TOKEN`` env overrides (CI / local / non-YC hosts).

Rotation: secrets are read once at startup, so a NEW Lockbox version is picked
up on the next process restart (zero-downtime via a rolling restart). A live,
no-redeploy in-process refresh is the AC-W1-9 follow-up (PARTIAL) — see the
chip + docs/runbooks.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# A URL, not a credential — bandit's S105 trips on the "token" path segment.
_METADATA_TOKEN_URL = (
    "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"  # noqa: S105
)
_DEFAULT_LOCKBOX_ENDPOINT = "https://payload.lockbox.api.cloud.yandex.net"
_DEFAULT_TIMEOUT = 5.0


class LockboxError(RuntimeError):
    """Raised when the Lockbox payload (or its IAM token) can't be fetched."""


def fetch_iam_token_from_metadata(*, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """Fetch the instance service-account IAM token from the YC metadata endpoint.

    No credential is stored on disk — the VM's bound service account is resolved
    by the metadata server. Raises ``LockboxError`` if unreachable / malformed.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(_METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"})
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        raise LockboxError(f"metadata IAM token fetch failed: {exc!s}") from exc
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise LockboxError("metadata response missing access_token")
    return token


def fetch_lockbox_secrets(
    secret_id: str,
    *,
    iam_token: str | None = None,
    endpoint: str | None = None,
    version_id: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, str]:
    """Return the latest (or pinned ``version_id``) Lockbox payload as a flat
    ``{key: value}`` map. ``iam_token`` defaults to the instance metadata token.

    Raises ``LockboxError`` on any transport / shape failure so the caller can
    fail fast at startup rather than booting with missing secrets.
    """
    token = iam_token or fetch_iam_token_from_metadata(timeout=timeout)
    base = (endpoint or _DEFAULT_LOCKBOX_ENDPOINT).rstrip("/")
    url = f"{base}/lockbox/v1/secrets/{secret_id}/payload"
    params = {"versionId": version_id} if version_id else None
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPError as exc:
        raise LockboxError(f"lockbox payload fetch failed for {secret_id}: {exc!s}") from exc

    secrets = _parse_payload(payload)
    logger.info(
        "shared.lockbox.loaded",
        secret_id=secret_id,
        version_id=payload.get("versionId"),
        keys=len(secrets),
    )
    return secrets


def _parse_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Map Lockbox ``entries`` (text or base64 binary) → ``{key: value}``."""
    out: dict[str, str] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if not key:
            continue
        text_value = entry.get("textValue")
        binary_value = entry.get("binaryValue")
        if text_value is not None:
            out[str(key)] = str(text_value)
        elif binary_value is not None:
            out[str(key)] = base64.b64decode(binary_value).decode("utf-8", errors="replace")
    return out
