"""Cross-context FastAPI middleware + DI helpers shared across bounded contexts.

Members:
  * tenant_context — get_tenant_db_session() dependency that wraps get_db
    with the 3-GUC RLS context (workspace_id, cell_id, user_id) per request.
"""

from src._shared.middleware.tenant_context import get_tenant_db_session

__all__ = ["get_tenant_db_session"]
