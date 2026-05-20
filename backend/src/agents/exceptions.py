"""Domain exceptions for agents bounded context.

Same envelope shape as iam/multitenancy/mcp — code + status_code + title +
optional detail. Exception handler installed in src.main.

ADR-024 §2: class names mirror error codes (no `Error` suffix). The N818
ruff exemption for **/exceptions.py covers this convention.
"""

from __future__ import annotations


class AgentsError(Exception):
    """Base domain exception for agents bounded context."""

    code: str = "agents.error"
    status_code: int = 500
    title: str = "Agents bounded-context error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


# ── 4xx: client errors ────────────────────────────────────────────────────


class AgentArchetypeNotFound(AgentsError):
    code = "agents.archetype.not_found"
    status_code = 404
    title = "Agent archetype not found"


class TeamPresetNotFound(AgentsError):
    code = "agents.team_preset.not_found"
    status_code = 404
    title = "Team preset not found"


class TeamAlreadyProvisioned(AgentsError):
    """Cell already has an agent_instances row for this archetype — re-provisioning
    is a no-op rather than an error, but tools/services that explicitly expect
    a fresh provision should raise this for the caller to handle."""

    code = "agents.team.already_provisioned"
    status_code = 409
    title = "Cell already has this team preset provisioned"


class RolePromptParseError(AgentsError):
    """Frontmatter missing, malformed, or 9-section structure invalid."""

    code = "agents.role_prompt.parse_failed"
    status_code = 500
    title = "Role prompt parse failed"


# ── Runtime delegation guards ─────────────────────────────────────────────


class DelegationDepthExceeded(AgentsError):
    """Coordinator → leaf chain went deeper than the per-task limit (default 5)."""

    code = "agents.delegation.depth_exceeded"
    status_code = 422
    title = "Delegation depth exceeded"


class DelegationTargetInvalid(AgentsError):
    """target_agent_id not in the caller's available_agents set."""

    code = "agents.delegation.target_invalid"
    status_code = 422
    title = "Delegation target not in team"
