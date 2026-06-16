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

# Russian Trusted Root CA (Минцифры) — signs the *.sberbank.ru chain that
# GigaChat serves; the stock python:slim trust store lacks it, which broke the
# GigaChat failover with SSL CERTIFICATE_VERIFY_FAILED in the container (AC-W1-21).
# httpx/certifi ignores the OS trust store, so we install it system-wide AND point
# GIGACHAT_CA_BUNDLE at the resulting bundle (the provider passes it to httpx
# verify=). Done in the shared base so both dev + prod containers verify GigaChat.
# Tolerant: if the CA host is unreachable at build time the GigaChat leg degrades
# and GIGACHAT_VERIFY_SSL=false is the documented dev-only escape hatch.
ARG RU_TRUSTED_CA_URL=https://gu-st.ru/content/Other/doc/russiantrustedca.pem
RUN curl -fsSL "$RU_TRUSTED_CA_URL" \
        -o /usr/local/share/ca-certificates/russian-trusted-root-ca.crt \
    && update-ca-certificates \
    || echo "WARN: RU Trusted Root CA install failed — GigaChat TLS will fail unless GIGACHAT_VERIFY_SSL=false"
ENV GIGACHAT_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

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
FROM base AS prod
# Prod target — Phase 00.6 Commit 7 deliverable. Single-worker Gunicorn +
# UvicornWorker per ADR F-ARC-H2 (multi-worker SSE-pub swap = Wave-1
# AC-W1-1). Frozen lockfile so prod build is reproducible.
#
# Build order matters: COPY src/ ДО `uv sync --frozen` — hatchling treats
# `teamly-backend` as a local editable install, and the sync resolves
# package metadata from src/ (pyproject.toml `[tool.hatch.build.targets.
# wheel] packages = ["src"]`).

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
# Role-prompt markdown is a runtime asset the agent factories load. Canonical
# source is .planning/contracts/role-prompts/ (outside this build context), so
# backend/role_prompts/ is BUILD-POPULATED from it by scripts/sync_role_prompts.*
# (gitignored — never committed; AC-W1-20 single-source). Run the sync before
# `docker build`; ROLE_PROMPTS_DIR points the loader at the packaged copy.
COPY role_prompts ./role_prompts
ENV ROLE_PROMPTS_DIR=/app/role_prompts

RUN uv sync --frozen --no-dev --compile-bytecode

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000

# Gunicorn process supervisor + single uvicorn worker (workers=1 per
# Phase 00.6 spec F-ARC-H2 Wave-0 invariant). --access-logfile + --error-
# logfile к stdout so Docker logging driver routes к Loki tail.
CMD ["gunicorn", "src.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "1", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--graceful-timeout", "30"]
