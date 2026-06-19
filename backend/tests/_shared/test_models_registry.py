"""Regression: the models registry fully populates Base.metadata.

Live golden (2026-06-19) found that the Dramatiq worker imported only the
dispatch path, so the shared ``Base.metadata`` was missing the cross-context
tables that ``tasks.tasks``' string FKs reference — every orchestration flush in
the worker raised ``NoReferencedTableError: ... 'agents.agent_instances'`` and
dead-lettered. ``_shared.db.models_registry`` imports every model module; the
worker entrypoint imports it. This test guards that contract: if a model module
is dropped from the registry, the cross-context FK targets disappear and a real
worker deployment breaks.
"""

from __future__ import annotations


def test_registry_populates_cross_context_fk_targets() -> None:
    import src._shared.db.models_registry  # noqa: F401 — side-effect import registers tables
    from src._shared.db.base import Base

    tables = set(Base.metadata.tables.keys())

    # The exact FK targets the worker flush needs (the ones that broke it live).
    for required in (
        "agents.agent_instances",
        "agents.agent_archetypes",
        "multitenancy.cells",
        "tasks.tasks",
        "tasks.task_artifacts",
    ):
        assert (
            required in tables
        ), f"{required} missing from Base.metadata — worker flush will break"
