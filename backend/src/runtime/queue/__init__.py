"""Dramatiq async-dispatch queue (Phase 01.1 infra-PR, AC-W1-16a).

``broker``  — broker selection (Redis in real processes, Stub in tests).
``actor``   — the ``dispatch_task_actor`` that runs an orchestration off-request.
``worker``  — the ``dramatiq src.runtime.queue.worker`` entrypoint.
"""
