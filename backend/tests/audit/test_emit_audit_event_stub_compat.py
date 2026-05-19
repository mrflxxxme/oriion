"""Unit: emit_audit_event must be a strict superset of the Phase 00.2 stub.

Phase 00.2.5 swaps the stub via a pure import replacement, so every call
that worked against ``src._stubs.audit.emit_audit_event`` must continue
to type-check (and run) against ``src.audit.services.audit_service``.
"""

from __future__ import annotations

import inspect
from inspect import Parameter

from src._stubs.audit import emit_audit_event as stub
from src.audit.services.audit_service import emit_audit_event as real


def test_real_impl_includes_every_stub_parameter() -> None:
    """Every named parameter of the stub appears in the real impl."""
    stub_params = inspect.signature(stub).parameters
    real_params = inspect.signature(real).parameters
    for name in stub_params:
        assert name in real_params, f"stub parameter {name!r} missing from real emit_audit_event"


def test_real_impl_preserves_stub_parameter_order_prefix() -> None:
    """The first N positional parameters match the stub's order.

    Phase 00.2.5 callers use positional binding (e.g.
    ``emit_audit_event("user", uid, "x", "y")``); if we re-order, they
    break silently. Real impl may APPEND new params but must not reorder.
    """
    stub_order = [
        p.name
        for p in inspect.signature(stub).parameters.values()
        if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]
    real_order = [
        p.name
        for p in inspect.signature(real).parameters.values()
        if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]
    assert real_order[: len(stub_order)] == stub_order


def test_real_impl_stub_param_defaults_compatible() -> None:
    """Real impl must not make any optional stub param required.

    Adding a default where the stub had none is a backward-compatible
    relaxation (resource_type str -> str | None = None); removing a
    default is a contract break.
    """
    stub_sig = inspect.signature(stub)
    real_sig = inspect.signature(real)
    for name, stub_p in stub_sig.parameters.items():
        real_p = real_sig.parameters[name]
        if stub_p.default is not Parameter.empty:
            assert (
                real_p.default is not Parameter.empty
            ), f"real impl made stub-optional param {name!r} required"


def test_real_impl_adds_optional_session_kwarg() -> None:
    """The new keyword-only ``session`` parameter exists and defaults to None."""
    sig = inspect.signature(real)
    assert "session" in sig.parameters
    sp = sig.parameters["session"]
    assert sp.kind == Parameter.KEYWORD_ONLY
    assert sp.default is None


def test_real_impl_adds_workspace_and_cell_kwargs() -> None:
    """workspace_id and cell_id were added as optional keyword-only kwargs."""
    sig = inspect.signature(real)
    for name in ("workspace_id", "cell_id"):
        assert name in sig.parameters, f"missing kwarg {name}"
        assert sig.parameters[name].kind == Parameter.KEYWORD_ONLY
        assert sig.parameters[name].default is None


def test_real_impl_return_type_is_none_like_stub() -> None:
    """Return annotation must remain ``None`` (callers don't await a value).

    Use ``inspect.signature`` instead of ``typing.get_type_hints`` because
    the real impl's signature references ``AsyncSession`` from a
    ``TYPE_CHECKING`` block — ``get_type_hints`` would try to resolve that
    at runtime and NameError. The string form is sufficient for the
    return-type contract.
    """
    assert str(inspect.signature(stub).return_annotation) == "None"
    assert str(inspect.signature(real).return_annotation) == "None"
