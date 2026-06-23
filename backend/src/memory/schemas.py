"""Pydantic v2 DTOs for the memory API (ADR-011 Wave-1).

Request models forbid extras (``extra='forbid'``); response models read from
ORM attributes (``from_attributes=True``). Embedding vectors are NEVER exposed
in API responses — only the human-readable entry fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Manual-API kinds are a subset of the DB CHECK — 'conversation_summary' is
# system-generated (summarizer), never created through the manual endpoints.
CellMemoryKind = Literal["fact", "note", "glossary"]
RoleMemoryKind = Literal["preference", "style", "process", "fact", "note"]


class MemoryEntryCreate(BaseModel):
    """Manual «запомни» payload for cell memory."""

    model_config = ConfigDict(extra="forbid")

    kind: CellMemoryKind = "fact"
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=8000)
    tags: list[str] = Field(default_factory=list)
    contains_pii: bool = False


class RoleMemoryEntryCreate(BaseModel):
    """Manual «запомни» payload for a specific agent's role memory."""

    model_config = ConfigDict(extra="forbid")

    kind: RoleMemoryKind = "preference"
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=8000)
    tags: list[str] = Field(default_factory=list)
    contains_pii: bool = False


class MemoryEntryOut(BaseModel):
    """Cell memory entry as returned by the API (no embedding vector)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    kind: str
    title: str | None
    content: str
    tags: list[str]
    source: str
    contains_pii: bool
    created_at: datetime
    updated_at: datetime


class RoleMemoryEntryOut(BaseModel):
    """Role memory entry as returned by the API (no embedding vector)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cell_id: UUID
    agent_id: UUID
    kind: str
    title: str | None
    content: str
    tags: list[str]
    source: str
    contains_pii: bool
    created_at: datetime
    updated_at: datetime


class MemorySearchHit(BaseModel):
    """A similarity-search result: the entry plus its cosine similarity score."""

    model_config = ConfigDict(from_attributes=False)

    entry: MemoryEntryOut
    score: float = Field(description="Cosine similarity in [-1, 1] (1.0 = identical).")


class RoleMemorySearchHit(BaseModel):
    """A role-memory similarity-search result."""

    model_config = ConfigDict(from_attributes=False)

    entry: RoleMemoryEntryOut
    score: float = Field(description="Cosine similarity in [-1, 1] (1.0 = identical).")
