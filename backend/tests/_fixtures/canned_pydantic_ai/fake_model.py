"""FakeLLMGatewayModel — canned-response Pydantic-AI Model for agent tests.

Drop-in replacement for ``src.llm_gateway.pydantic_ai_model.LLMGatewayModel``
that returns pre-registered ``ModelResponse`` lists keyed by
``(role_key, scenario_id)`` instead of hitting any real provider.

Fail-loud contract (T3 founder-resolved 2026-05-20):
    * Unknown ``(role_key, scenario_id)`` key on lookup → ``KeyError``
    * Canned response list exhausted → ``IndexError``
    * Scenario not set before first call → ``RuntimeError``

This forces test authors to register every code-path they exercise rather
than silently fall back to a heuristic LLM mock.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai.models import Model

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelRequest, ModelResponse
    from pydantic_ai.models import ModelRequestParameters
    from pydantic_ai.settings import ModelSettings


_SYSTEM_TAG = "oriion-llm-gateway-fake"


class FakeLLMGatewayModel(Model):
    """Canned-response Model. NEVER make a network call.

    The same instance can fulfil multiple roles by switching scenarios at
    runtime (e.g. coordinator + 3 specialists in one demo run all share
    one model instance — they differ only by ``role_key`` on the agent
    construction side, and the fake routes lookups via that key).
    """

    def __init__(self, role_key: str) -> None:
        super().__init__()
        self._role_key = role_key
        self._responses: dict[tuple[str, str], list[ModelResponse]] = {}
        self._scenario_id: str | None = None
        # Per-key cursor so two scenarios don't interfere when interleaved.
        self._cursors: dict[tuple[str, str], int] = {}
        self.calls: list[tuple[str, str]] = []  # audit trail for assertions

    # ── public registration API ──────────────────────────────────────────

    def set_response(
        self,
        role_key: str,
        scenario_id: str,
        responses: list[ModelResponse],
    ) -> None:
        """Register a canned response list for one ``(role_key, scenario_id)``."""
        self._responses[(role_key, scenario_id)] = list(responses)
        self._cursors[(role_key, scenario_id)] = 0

    def set_scenario(self, scenario_id: str) -> None:
        """Switch the active scenario. Subsequent ``request()`` calls pull
        from the matching ``(role_key, scenario_id)`` bucket."""
        self._scenario_id = scenario_id

    # ── abstract Model interface ─────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return f"{_SYSTEM_TAG}/{self._role_key}"

    @property
    def system(self) -> str:
        return _SYSTEM_TAG

    async def request(
        self,
        messages: list[ModelRequest | ModelResponse],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Return the next canned response for the active scenario.

        Errors are loud + actionable so the test author sees them at
        assertion time, not buried inside agent loops.
        """
        if self._scenario_id is None:
            raise RuntimeError(
                "FakeLLMGatewayModel: set_scenario() must be called before "
                "the first request(). Pass scenario_id via the fixture."
            )
        key = (self._role_key, self._scenario_id)
        if key not in self._responses:
            raise KeyError(
                f"FakeLLMGatewayModel: no canned responses registered for "
                f"{key!r}. Register via set_response(role_key, scenario_id, ...). "
                f"Known scenarios: {sorted({s for (_r, s) in self._responses})}"
            )
        bucket = self._responses[key]
        cursor = self._cursors[key]
        if cursor >= len(bucket):
            raise IndexError(
                f"FakeLLMGatewayModel: canned responses exhausted for {key!r} "
                f"(registered {len(bucket)}, this is call #{cursor + 1}). "
                "Register more responses or check the agent loop for unintended "
                "re-entry."
            )
        self._cursors[key] = cursor + 1
        self.calls.append(key)

        # Stamp timestamp at call-time so transit ordering is observable.
        resp = bucket[cursor]
        if resp.timestamp.replace(tzinfo=UTC) == datetime.min.replace(tzinfo=UTC):
            # Caller passed a sentinel — refresh.
            resp.timestamp = datetime.now(UTC)
        return resp
