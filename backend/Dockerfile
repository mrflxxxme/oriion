# syntax=docker/dockerfile:1.7
# backend/Dockerfile — multi-stage build с dev + prod targets.
# Dev target: hot-reload via volume mount + uv sync at container start.
# Prod target: frozen lockfile, no dev deps, gunicorn worker pool (Phase 00.6).

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

WORKDIR /app

# ─────────────────────────────────────────────────────────────
FROM base AS dev
# Dev target: код mount-ится через volume в docker-compose.dev.yml.
# uv sync выполняется в container command (см. compose `command:`).
# Этот target нужен для compose build context; runtime инструкции
# дают command в compose.
COPY pyproject.toml ./
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─────────────────────────────────────────────────────────────
# Prod target — returns Phase 00.6 deliverable. Удалён из Phase 00.1 потому
# что (а) compose targets только `dev`, (b) prod stage требует переноса COPY
# src ДО `uv sync` (иначе hatchling fails build local project), (c) prod
# entrypoint должен использовать gunicorn worker pool а не --reload uvicorn.
# Все эти решения принимает Phase 00.6 owner.
