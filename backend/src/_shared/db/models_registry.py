"""Import every bounded-context model module so the shared ``Base.metadata`` is
fully populated before any ORM flush.

Cross-context foreign keys (e.g. ``tasks.tasks.agent_instance_id`` ->
``agents.agent_instances.id``, ``tasks.tasks.cell_id`` ->
``multitenancy.cells.id``) are declared as string targets; SQLAlchemy resolves
them lazily at mapper-configure / flush time, which requires the *referenced*
tables to already be registered on the shared ``Base.metadata``. The web tier
loads all of them transitively via its routers, but an out-of-process
entrypoint (the Dramatiq worker, which runs the task orchestration) imports
only the dispatch path — so a ``Task`` flush there raised
``NoReferencedTableError: ... could not find table 'agents.agent_instances'``
and every dispatch dead-lettered.

Importing this module registers the full set. Import it from any standalone
entrypoint that performs ORM writes outside the FastAPI app (the worker does).
"""

from __future__ import annotations

import src.agents.models
import src.audit.models
import src.billing.models
import src.iam.models
import src.llm_gateway.models
import src.mcp.models
import src.multitenancy.models
import src.rbac.models
import src.tasks.models  # noqa: F401
