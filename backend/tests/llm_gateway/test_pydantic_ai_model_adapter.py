"""Unit tests for the LLMGatewayModel + FakeLLMGatewayModel adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import ModelRequestParameters
from src.llm_gateway.providers.base import LLMResponse, LLMUsage
from src.llm_gateway.pydantic_ai_model import LLMGatewayModel

from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel
from tests._fixtures.canned_pydantic_ai.market_brief_demo import (
    RESPONSES,
    SCENARIO_ID,
    researcher_matrix_row_count,
    writer_brief_word_count,
    writer_content_plan_post_count,
)

# ── LLMGatewayModel (real adapter) ──────────────────────────────────────


@pytest.fixture
def fake_provider():
    """Mock LLMProvider returning a fixed LLMResponse."""
    provider = AsyncMock()
    provider.name = "deepseek"
    provider.chat = AsyncMock(
        return_value=LLMResponse(
            content="Hello, this is a canned chat response.",
            finish_reason="stop",
            usage=LLMUsage(tokens_input=12, tokens_output=8, cached_input_tokens=0),
            raw_provider_metadata={"provider": "deepseek"},
        )
    )
    return provider


@pytest.fixture
def fake_router(fake_provider):
    """Mock LLMRouter that returns the fake_provider for any role."""
    router = AsyncMock()
    router.route = AsyncMock(return_value=(fake_provider, "deepseek-chat"))
    return router


@pytest.fixture
def model_request_params():
    return ModelRequestParameters(
        function_tools=[],
        builtin_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        prompted_output_template=None,
        allow_text_output=True,
        allow_image_output=False,
    )


async def test_llm_gateway_model_translates_request_to_router_call(
    fake_router, fake_provider, model_request_params
):
    """LLMGatewayModel.request() routes through LLMRouter and normalizes
    the LLMResponse into a Pydantic-AI ModelResponse with TextPart."""
    model = LLMGatewayModel(role_key="coordinator", llm_router=fake_router)

    messages = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="You are a coordinator."),
                UserPromptPart(content="Make me a market brief."),
            ]
        )
    ]

    response = await model.request(
        messages=messages,
        model_settings=None,
        model_request_parameters=model_request_params,
    )

    # Router was called with the role_key + zero-workspace-id (Wave 0 default).
    fake_router.route.assert_awaited_once()
    call_kwargs = fake_router.route.await_args.kwargs
    assert call_kwargs["role_key"] == "coordinator"

    # Provider chat received OpenAI-shaped messages — system + user.
    fake_provider.chat.assert_awaited_once()
    llm_req = fake_provider.chat.await_args.args[0]
    assert llm_req.model == "deepseek-chat"
    assert llm_req.messages == [
        {"role": "system", "content": "You are a coordinator."},
        {"role": "user", "content": "Make me a market brief."},
    ]
    # Metadata is propagated for downstream billing/audit attribution.
    assert llm_req.metadata["role_key"] == "coordinator"

    # ModelResponse shape: TextPart with provider content, usage normalized.
    assert isinstance(response, ModelResponse)
    assert len(response.parts) == 1
    part = response.parts[0]
    assert isinstance(part, TextPart)
    assert part.content == "Hello, this is a canned chat response."
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 8
    assert response.provider_name == "deepseek"
    assert response.model_name == "oriion-llm-gateway/deepseek-chat"


async def test_llm_gateway_model_passes_workspace_id_to_router(fake_router, model_request_params):
    """Explicit workspace_id propagates to LLMRouter.route()."""
    workspace_id = uuid4()
    model = LLMGatewayModel(
        role_key="researcher",
        llm_router=fake_router,
        workspace_id=workspace_id,
    )

    await model.request(
        messages=[ModelRequest(parts=[UserPromptPart(content="Research foo.")])],
        model_settings=None,
        model_request_parameters=model_request_params,
    )

    call_kwargs = fake_router.route.await_args.kwargs
    assert call_kwargs["workspace_id"] == workspace_id


async def test_llm_gateway_model_forwards_model_hint(fake_router, model_request_params):
    """model_hint reaches LLMRouter.route() unchanged (BYOK + override path)."""
    model = LLMGatewayModel(
        role_key="coordinator",
        llm_router=fake_router,
        model_hint="byok-openai/gpt-4o",
    )

    await model.request(
        messages=[ModelRequest(parts=[UserPromptPart(content="hi")])],
        model_settings=None,
        model_request_parameters=model_request_params,
    )

    call_kwargs = fake_router.route.await_args.kwargs
    assert call_kwargs["model_hint"] == "byok-openai/gpt-4o"


def test_llm_gateway_model_name_property(fake_router):
    """model_name + system properties surface the role-key for usage logs."""
    model = LLMGatewayModel(role_key="writer", llm_router=fake_router)
    assert model.model_name == "oriion-llm-gateway/writer"
    assert model.system == "oriion-llm-gateway"


# ── FakeLLMGatewayModel (canned-response test stub) ─────────────────────


async def test_fake_model_unknown_scenario_raises():
    """T3 fail-loud invariant: scenario not set → RuntimeError on request()."""
    model = FakeLLMGatewayModel(role_key="coordinator")
    with pytest.raises(RuntimeError, match="set_scenario"):
        await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]


async def test_fake_model_unknown_key_raises():
    """T3 fail-loud invariant: (role_key, scenario_id) not registered → KeyError."""
    model = FakeLLMGatewayModel(role_key="coordinator")
    model.set_scenario("nonexistent_scenario")
    with pytest.raises(KeyError, match="no canned responses registered"):
        await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]


async def test_fake_model_exhaustion_raises():
    """T3 fail-loud invariant: canned list exhausted → IndexError."""
    from datetime import UTC, datetime

    from pydantic_ai.usage import RequestUsage

    model = FakeLLMGatewayModel(role_key="coordinator")
    model.set_response(
        "coordinator",
        "tiny",
        [
            ModelResponse(
                parts=[TextPart(content="only one")],
                usage=RequestUsage(input_tokens=1, output_tokens=1, details={}),
                model_name="x",
                timestamp=datetime.now(UTC),
                finish_reason="stop",
            )
        ],
    )
    model.set_scenario("tiny")
    # First call exhausts the bucket.
    await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]
    with pytest.raises(IndexError, match="exhausted"):
        await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]


async def test_fake_model_returns_canned_in_order():
    """Successive calls walk the registered list in order."""
    model = FakeLLMGatewayModel(role_key="coordinator")
    for (role_key, scenario_id), responses in RESPONSES.items():
        model.set_response(role_key, scenario_id, responses)
    model.set_scenario(SCENARIO_ID)

    resp_1 = await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]
    resp_2 = await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]

    # Coordinator has 2 canned responses in market_brief_demo — first is
    # the decompose plan, second is the synthesize summary.
    assert "План декомпозиции" in resp_1.parts[0].content
    assert "Финальный синтез" in resp_2.parts[0].content
    assert model.calls == [
        ("coordinator", SCENARIO_ID),
        ("coordinator", SCENARIO_ID),
    ]


def test_pydantic_ai_test_model_fixture_seeded(pydantic_ai_test_model):
    """The conftest fixture pre-loads all 4 roles for market_brief_demo."""
    # set_scenario already called on the fixture; the model knows about all
    # 4 (role_key, scenario_id) combinations.
    keys = sorted(pydantic_ai_test_model._responses.keys())
    assert keys == sorted(
        [
            ("coordinator", SCENARIO_ID),
            ("researcher", SCENARIO_ID),
            ("writer", SCENARIO_ID),
            ("analyst", SCENARIO_ID),
        ]
    )


# ── AC9 invariants (artifact shape ledger) ──────────────────────────────


def test_canned_brief_word_count_meets_ac9():
    """AC9: brief.md must be ≥1500 RU words."""
    assert writer_brief_word_count() >= 1500


def test_canned_matrix_row_count_meets_ac9():
    """AC9: competitive-matrix.md must be 5+ data rows by 4+ columns."""
    assert researcher_matrix_row_count() >= 5


def test_canned_content_plan_post_count_meets_ac9():
    """AC9: content-plan.md must be exactly 10 posts."""
    assert writer_content_plan_post_count() == 10
