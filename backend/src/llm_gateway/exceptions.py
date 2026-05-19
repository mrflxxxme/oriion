"""Domain exceptions for llm_gateway.

Exception class names follow phase-spec naming (no `Error` suffix) — exposed
as `code` strings, not class names, in API error responses. See
pyproject.toml `[tool.ruff.lint.per-file-ignores]` for N818 exemption.
"""

from __future__ import annotations


class LLMGatewayException(Exception):
    """Base class for all llm_gateway domain exceptions."""

    code: str = "llm_gateway.unknown"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code


class LLMProviderUnavailable(LLMGatewayException):
    """All providers in the failover chain are unavailable (circuit OPEN)."""

    code = "llm_gateway.provider_unavailable"


class BudgetExceeded(LLMGatewayException):
    """Per-task or per-cell cost cap exceeded (AC10)."""

    code = "llm_gateway.budget_exceeded"


class BYOKKeyInvalid(LLMGatewayException):
    """BYOK key validation failed (e.g. provider returned 401 on probe)."""

    code = "llm_gateway.byok_key_invalid"


class BYOKKeyNotFound(LLMGatewayException):
    """BYOK key id not found for the current workspace."""

    code = "llm_gateway.byok_key_not_found"


class KMSError(LLMGatewayException):
    """KMS encrypt/decrypt operation failed (tamper detection or backend error)."""

    code = "llm_gateway.kms_error"


class CircuitOpen(LLMGatewayException):
    """Provider circuit is OPEN — fast-fail before HTTP call."""

    code = "llm_gateway.circuit_open"
