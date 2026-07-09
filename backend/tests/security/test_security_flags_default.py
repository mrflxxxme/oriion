"""Both security guardrail flags default ON since 01.9a (AC-01.9a.4).

DV-04 closure evidence: the DLP hard-block + injection sanitize are active by
default (dev/test), not opt-in. Uses ``app_env="dev"`` so the staging/prod
dev-secret guard does not fire.
"""

from __future__ import annotations

import pytest
from src._shared.config import Settings


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    # Clear any host env override so we assert the field DEFAULTS, not the env.
    monkeypatch.delenv("SECURITY_DLP_ENABLED", raising=False)
    monkeypatch.delenv("SECURITY_INJECTION_SCAN_ENABLED", raising=False)
    return Settings(_env_file=None, app_env="dev")  # type: ignore[call-arg]


def test_dlp_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch).security_dlp_enabled is True


def test_injection_scan_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch).security_injection_scan_enabled is True
