"""Domain exceptions for tasks bounded context."""

from __future__ import annotations


class TasksError(Exception):
    """Base domain exception."""

    code: str = "tasks.error"
    status_code: int = 500
    title: str = "Tasks error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(detail or self.title)


class TaskNotFound(TasksError):
    code = "tasks.not_found"
    status_code = 404
    title = "Task not found"


class TaskCancelled(TasksError):
    """Raised at runtime when a task transitioned to 'cancelled' mid-execution."""

    code = "tasks.cancelled"
    status_code = 409
    title = "Task cancelled"


class BudgetExceeded(TasksError):
    """Per-task 50 T-credit cap exceeded (AC10 anchor, F-P5-2)."""

    code = "tasks.budget_exceeded"
    status_code = 402
    title = "Task budget exceeded"


class DelegationDepthExceeded(TasksError):
    """parent_task chain went deeper than max_delegation_depth (default 5)."""

    code = "tasks.delegation_depth_exceeded"
    status_code = 422
    title = "Task delegation depth exceeded"
