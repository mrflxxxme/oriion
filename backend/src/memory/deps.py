"""FastAPI DI for the memory API — RLS session + gateway embedder + services."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src._shared.middleware.tenant_context import (
    get_current_workspace_id,
    get_tenant_db_session,
)
from src.llm_gateway.services.router_service import LLMRouter
from src.memory.repositories.memory_repository import CellMemoryRepository
from src.memory.repositories.role_memory_repository import RoleMemoryRepository
from src.memory.services.embedder import GatewayEmbedder, build_gateway_embedder
from src.memory.services.memory_service import CellMemoryService
from src.memory.services.role_memory_service import RoleMemoryService


def get_llm_router(request: Request) -> LLMRouter:
    """The process-wide LLMRouter stashed on ``app.state`` at lifespan startup."""
    return cast(LLMRouter, request.app.state.llm_router)


def get_gateway_embedder(
    workspace_id: UUID = Depends(get_current_workspace_id),
    router: LLMRouter = Depends(get_llm_router),
) -> GatewayEmbedder:
    return build_gateway_embedder(router, workspace_id=workspace_id)


def get_cell_memory_service(
    db: AsyncSession = Depends(get_tenant_db_session),
    embedder: GatewayEmbedder = Depends(get_gateway_embedder),
) -> CellMemoryService:
    return CellMemoryService(CellMemoryRepository(db), embedder)


def get_role_memory_service(
    db: AsyncSession = Depends(get_tenant_db_session),
    embedder: GatewayEmbedder = Depends(get_gateway_embedder),
) -> RoleMemoryService:
    return RoleMemoryService(RoleMemoryRepository(db), embedder)
