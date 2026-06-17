"""Just-enough async SQLAlchemy session stub for agents service/router unit tests.

The per-module coverage gate runs ``-m "not integration"``, so real testcontainers
PG is off-limits here. This stub plays back a queue of ``Result`` objects on
successive ``execute()`` calls and auto-assigns ids on ``flush()`` so insert paths
exercise end-to-end without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class Scalars:
    items: list[Any] = field(default_factory=list)

    def all(self) -> list[Any]:
        return list(self.items)


@dataclass
class Result:
    """sqlalchemy.Result-shaped stub.

    * ``scalars().all()`` → ``scalar_list``
    * ``scalar_one_or_none()`` / ``scalar_one()`` → ``scalar``
    * ``all()`` (row tuples, e.g. archetype slug-map) → ``rows``
    """

    scalar_list: list[Any] = field(default_factory=list)
    scalar: Any = None
    rows: list[Any] = field(default_factory=list)

    def scalars(self) -> Scalars:
        return Scalars(self.scalar_list)

    def scalar_one_or_none(self) -> Any:
        return self.scalar

    def scalar_one(self) -> Any:
        if self.scalar is None:
            raise AssertionError("scalar_one(): no row prepared")
        return self.scalar

    def all(self) -> list[Any]:
        return list(self.rows)


class StubSession:
    """Minimal AsyncSession surface used by the agents services/routers."""

    def __init__(
        self,
        results: list[Result] | None = None,
        get_map: dict[UUID, Any] | None = None,
    ) -> None:
        self._results = list(results or [])
        self._get_map = get_map or {}
        self.added: list[Any] = []
        self.flush_calls = 0

    async def execute(self, _stmt: Any) -> Result:
        return self._results.pop(0) if self._results else Result()

    async def get(self, _model: Any, id_: UUID) -> Any:
        return self._get_map.get(id_)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
