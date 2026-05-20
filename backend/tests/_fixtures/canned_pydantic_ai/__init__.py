"""Canned Pydantic-AI fixtures for agent integration tests.

T3 mock pattern (founder-resolved 2026-05-20): custom stub at
``LLMGatewayModel`` level, keyed by ``(role_key, scenario_id)`` tuple.
NOT pydantic_ai's ``TestModel`` (too heuristic). Fail-loud on unknown key.

Public surface:
    * ``FakeLLMGatewayModel`` — drop-in replacement for ``LLMGatewayModel``;
      returns canned ``ModelResponse`` lists from a registered scenario.
    * ``market_brief_demo`` module — canned responses for the Phase 00.5b
      demo scenario «Market & content brief». Artifact content already
      shape-correct for AC9 (brief ≥1500w RU, matrix ≥5×4, plan = 10 posts).

Usage in tests::

    from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel
    from tests._fixtures.canned_pydantic_ai.market_brief_demo import RESPONSES

    fake = FakeLLMGatewayModel(role_key="coordinator")
    for (role, scenario), responses in RESPONSES.items():
        fake.set_response(role, scenario, responses)
    fake.set_scenario("market_brief_demo")
    # Now `Agent(model=fake)` will pull canned responses per call.
"""

from tests._fixtures.canned_pydantic_ai.fake_model import FakeLLMGatewayModel

__all__ = ["FakeLLMGatewayModel"]
