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
    """Mock LLMRouter whose acomplete() returns a canned (response, model, slug)."""
    router = AsyncMock()
    canned = LLMResponse(
        content="Hello, this is a canned chat response.",
        finish_reason="stop",
        usage=LLMUsage(tokens_input=12, tokens_output=8, cached_input_tokens=0),
        raw_provider_metadata={"provider": "deepseek"},
    )
    router.acomplete = AsyncMock(return_value=(canned, "deepseek-chat", "deepseek"))
    return router


@pytest.fixture
def model_request_params():
    # pydantic-ai 1.56+ renamed `builtin_tools=` to `native_tools=` and removed
    # `allow_image_output`. Use minimal field set so the fixture survives
    # incremental pydantic-ai upgrades (only Wave-0-relevant fields).
    return ModelRequestParameters(
        function_tools=[],
        output_mode="text",
        output_object=None,
        output_tools=[],
        prompted_output_template=None,
        allow_text_output=True,
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

    # Router.acomplete was called with the role_key + OpenAI-shaped messages.
    fake_router.acomplete.assert_awaited_once()
    call_kwargs = fake_router.acomplete.await_args.kwargs
    assert call_kwargs["role_key"] == "coordinator"
    assert call_kwargs["messages"] == [
        {"role": "system", "content": "You are a coordinator."},
        {"role": "user", "content": "Make me a market brief."},
    ]
    # Metadata is propagated for downstream billing/audit attribution.
    assert call_kwargs["metadata"]["role_key"] == "coordinator"

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

    call_kwargs = fake_router.acomplete.await_args.kwargs
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

    call_kwargs = fake_router.acomplete.await_args.kwargs
    assert call_kwargs["model_hint"] == "byok-openai/gpt-4o"


async def test_llm_gateway_model_injects_prompted_output_schema(fake_router):
    """AC-W1-16b: a PromptedOutput-configured Agent over the gateway model gets its
    JSON schema injected as a system message, and a fenced-JSON response round-trips
    into the Pydantic output model — no function-calling, no tool-forwarding."""
    from pydantic import BaseModel
    from pydantic_ai import Agent, PromptedOutput

    class _Plan(BaseModel):
        summary: str
        steps: list[str]

    fenced = '```json\n{"summary": "ok", "steps": ["research", "write"]}\n```'
    fake_router.acomplete = AsyncMock(
        return_value=(
            LLMResponse(
                content=fenced,
                finish_reason="stop",
                usage=LLMUsage(tokens_input=20, tokens_output=15),
                raw_provider_metadata={"provider": "deepseek"},
            ),
            "deepseek-chat",
            "deepseek",
        )
    )
    model = LLMGatewayModel(role_key="coordinator", llm_router=fake_router)
    agent = Agent(model=model, output_type=PromptedOutput(_Plan))

    result = await agent.run("Plan a market brief.")

    # The fenced JSON round-tripped into the typed output.
    assert isinstance(result.output, _Plan)
    assert result.output.steps == ["research", "write"]
    # The schema directive reached the provider as a system message.
    sent_messages = fake_router.acomplete.await_args.kwargs["messages"]
    system_blobs = [m["content"] for m in sent_messages if m["role"] == "system"]
    assert any("JSON" in blob for blob in system_blobs)


@pytest.mark.parametrize(
    ("role", "expected"),
    [("writer", 8192), ("coordinator", 2048), ("researcher", 4096), ("unknown-role", 4096)],
)
async def test_llm_gateway_model_resolves_per_role_max_tokens(
    fake_router, model_request_params, role, expected
):
    """AC-W1-23a: the adapter resolves a per-role output budget and forwards it to acomplete()."""
    model = LLMGatewayModel(role_key=role, llm_router=fake_router)
    await model.request(
        messages=[ModelRequest(parts=[UserPromptPart(content="hi")])],
        model_settings=None,
        model_request_parameters=model_request_params,
    )
    assert fake_router.acomplete.await_args.kwargs["max_tokens"] == expected


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
    """A request returns the registered canned response for (role, scenario)."""
    model = FakeLLMGatewayModel(role_key="coordinator")
    for (role_key, scenario_id), responses in RESPONSES.items():
        model.set_response(role_key, scenario_id, responses)
    model.set_scenario(SCENARIO_ID)

    resp = await model.request(messages=[], model_settings=None, model_request_parameters=None)  # type: ignore[arg-type]

    # The Coordinator now emits a single fenced-JSON plan (AC-W1-16b) — no more
    # decompose-then-synthesize two-call shape.
    assert "delegation_plan" in resp.parts[0].content
    assert model.calls == [("coordinator", SCENARIO_ID)]


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
