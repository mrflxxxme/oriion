"""Smoke tests for backend package.

Phase 00.1 baseline — проверяет что package importable и version-string
правильный shape. Реальные tests появятся в Phase 00.2+ когда есть domain.
"""

from __future__ import annotations

import src


def test_package_importable() -> None:
    """Backend package импортируется без ошибок."""
    assert src is not None


def test_version_string_present() -> None:
    """``src.__version__`` exists и непустая string."""
    assert hasattr(src, "__version__")
    assert isinstance(src.__version__, str)
    assert len(src.__version__) > 0


def test_version_string_semver_shape() -> None:
    """``src.__version__`` соответствует semver-like shape (N.N.N)."""
    parts = src.__version__.split(".")
    assert len(parts) >= 2, f"Version must be at least N.N, got {src.__version__!r}"
    for part in parts[:3]:
        assert part.isdigit() or part.split("-")[0].isdigit(), (
            f"Version part {part!r} not numeric (allowed: '1.2.3' or '1.2.3-rc1')"
        )
