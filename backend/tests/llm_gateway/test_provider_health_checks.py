"""Unit: provider health_check branches via respx.

Lifts the llm_gateway coverage margin above the 85% gate by covering the
reachable + ConnectError paths in yandex + gigachat (the deepseek pair
lives in test_provider_deepseek_mock.py).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from src.llm_gateway.providers.gigachat import GigaChatProvider
from src.llm_gateway.providers.yandex import YandexGPTProvider

# ── Yandex health_check ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_yandex_health_check_reachable() -> None:
    async with respx.mock(base_url="https://llm.api.cloud.yandex.net") as router:
        router.get("/").mock(return_value=httpx.Response(404))
        provider = YandexGPTProvider(iam_token="x", catalog_id="f")
        assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_yandex_health_check_unreachable_returns_false() -> None:
    async with respx.mock(base_url="https://llm.api.cloud.yandex.net") as router:
        router.get("/").mock(side_effect=httpx.ConnectError("DNS failure (mock)"))
        provider = YandexGPTProvider(iam_token="x", catalog_id="f")
        assert await provider.health_check() is False


# ── GigaChat health_check ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gigachat_health_check_reachable() -> None:
    """Health check passes when oauth + models endpoints return success."""
    oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    async with respx.mock() as router:
        router.post(oauth_url).mock(
            return_value=httpx.Response(
                200, json={"access_token": "tok123", "expires_at": 9999999999999}
            )
        )
        provider = GigaChatProvider(auth_key="fake-base64-key")
        result = await provider.health_check()
        # Reachable upstream → True after _ensure_token returns
        assert result is True


@pytest.mark.asyncio
async def test_gigachat_health_check_unreachable_returns_false() -> None:
    """ConnectError on oauth → health_check returns False."""
    oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    async with respx.mock() as router:
        router.post(oauth_url).mock(side_effect=httpx.ConnectError("DNS failure (mock)"))
        provider = GigaChatProvider(auth_key="fake-base64-key")
        assert await provider.health_check() is False
