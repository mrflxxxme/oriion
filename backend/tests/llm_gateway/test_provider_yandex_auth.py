"""YandexGPT hybrid auth-scheme tests.

Api-Key (static, non-expiring) is preferred; IAM Bearer is the legacy/failover
scheme; no credential → LLMProviderUnavailable (caught by the router failover).
"""

from __future__ import annotations

import pytest
from src.llm_gateway.exceptions import LLMProviderUnavailable
from src.llm_gateway.providers.yandex import YandexGPTProvider


def test_auth_header_prefers_api_key_over_iam() -> None:
    provider = YandexGPTProvider(
        catalog_id="f",
        api_key="AQVN-test-key",
        iam_token="t1.iam-should-be-ignored",
    )
    assert provider._auth_header() == "Api-Key AQVN-test-key"


def test_auth_header_falls_back_to_iam_bearer() -> None:
    provider = YandexGPTProvider(catalog_id="f", iam_token="t1.iam-token")
    assert provider._auth_header() == "Bearer t1.iam-token"


def test_auth_header_without_credential_raises() -> None:
    provider = YandexGPTProvider(catalog_id="f")
    with pytest.raises(LLMProviderUnavailable):
        provider._auth_header()


@pytest.mark.asyncio
async def test_client_sets_api_key_authorization_header() -> None:
    provider = YandexGPTProvider(catalog_id="f", api_key="AQVN-test-key")
    async with provider._client() as client:
        assert client.headers["authorization"] == "Api-Key AQVN-test-key"
        assert client.headers["x-folder-id"] == "f"


@pytest.mark.asyncio
async def test_client_sets_iam_bearer_authorization_header() -> None:
    provider = YandexGPTProvider(catalog_id="f", iam_token="t1.iam-token")
    async with provider._client() as client:
        assert client.headers["authorization"] == "Bearer t1.iam-token"
