"""Unit: leaf-specialist agent factories build a real Pydantic-AI Agent.

Covers the analyst / writer / researcher factory functions (incl. the AC-W1-18
read_url tool branch) against the canned FakeLLMGatewayModel — no live keys.
"""

from __future__ import annotations

from pydantic_ai import Agent
from src.agents.analyst import AnalystDeps, build_analyst_agent
from src.agents.analyst import get_role_prompt as analyst_prompt
from src.agents.researcher import build_researcher_agent
from src.agents.writer import WriterDeps, build_writer_agent

from tests._fixtures.canned_pydantic_ai import FakeLLMGatewayModel


def test_build_analyst_agent() -> None:
    agent = build_analyst_agent(model=FakeLLMGatewayModel(role_key="analyst"))
    assert isinstance(agent, Agent)
    # role-prompt loads + composes without error
    assert analyst_prompt().composed_system_prompt()


def test_build_writer_agent() -> None:
    agent = build_writer_agent(model=FakeLLMGatewayModel(role_key="writer"))
    assert isinstance(agent, Agent)


def test_build_researcher_agent_toolless() -> None:
    agent = build_researcher_agent(model=FakeLLMGatewayModel(role_key="researcher"))
    assert isinstance(agent, Agent)


def test_build_researcher_agent_with_web_search_and_read_url() -> None:
    async def web_search(query: str) -> str:
        return ""

    async def read_url(url: str) -> str:
        return ""

    agent = build_researcher_agent(
        model=FakeLLMGatewayModel(role_key="researcher"),
        web_search=web_search,
        read_url=read_url,
    )
    assert isinstance(agent, Agent)


def test_deps_classes_instantiate() -> None:
    assert AnalystDeps() is not None
    assert WriterDeps() is not None
