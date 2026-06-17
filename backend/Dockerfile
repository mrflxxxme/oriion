# syntax=docker/dockerfile:1.7
# backend/Dockerfile — multi-stage build с dev + prod targets.
# Dev target: hot-reload via volume mount + uv sync at container start.
# Prod target: frozen lockfile, no dev deps, gunicorn worker pool (Phase 00.6).

# Digest-pinned for reproducible/supply-chain-safe builds (ADR-014-security).
# Tag for humans: python:3.12-slim. Re-pin via:
#   docker pull python:3.12-slim && docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9 AS base

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
# Fail the build LOUDLY if the CA fetch/install fails (ADR-014-security): a
# silently-missing root CA shipped a container that fails GigaChat TLS at runtime
# with no build signal. `curl -f` already errors on HTTP>=400; we no longer
# swallow it with `|| echo`. GIGACHAT_VERIFY_SSL=false remains the documented
# dev-only escape hatch when the CA is genuinely unavailable.
ARG RU_TRUSTED_CA_URL=https://gu-st.ru/content/Other/doc/russiantrustedca.pem
# Supply-chain integrity: pin the expected sha256 of the fetched PEM so a
# tampered/MITM'd CA fails the build. PLACEHOLDER below — replace with the real
# digest before merge (download the PEM and run `sha256sum russiantrustedca.pem`),
# or pass --build-arg RU_TRUSTED_CA_SHA256=<hash>. Empty value skips the check
# (kept non-empty-by-default so the verification path is exercised once pinned).
ARG RU_TRUSTED_CA_SHA256=REPLACE_WITH_REAL_SHA256_BEFORE_MERGE
RUN curl -fsSL "$RU_TRUSTED_CA_URL" \
        -o /usr/local/share/ca-certificates/russian-trusted-root-ca.crt \
    && if [ "$RU_TRUSTED_CA_SHA256" != "REPLACE_WITH_REAL_SHA256_BEFORE_MERGE" ] && [ -n "$RU_TRUSTED_CA_SHA256" ]; then \
           echo "${RU_TRUSTED_CA_SHA256}  /usr/local/share/ca-certificates/russian-trusted-root-ca.crt" | sha256sum -c -; \
       else \
           echo "WARN: RU_TRUSTED_CA_SHA256 not pinned — skipping checksum verification (pin before prod)"; \
       fi \
    && update-ca-certificates
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

# Non-root runtime user (ADR-014-security): gunicorn must NOT run as uid 0.
# Created in the prod stage; app files + the uv-synced venv are chowned to it.
RUN useradd -m -u 10001 app

COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app src ./src
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app alembic.ini ./
# Role-prompt markdown is a runtime asset the agent factories load. Canonical
# source is .planning/contracts/role-prompts/ (outside this build context), so
# backend/role_prompts/ is BUILD-POPULATED from it by scripts/sync_role_prompts.*
# (gitignored — never committed; AC-W1-20 single-source). Run the sync before
# `docker build`; ROLE_PROMPTS_DIR points the loader at the packaged copy.
COPY --chown=app:app role_prompts ./role_prompts
ENV ROLE_PROMPTS_DIR=/app/role_prompts

RUN uv sync --frozen --no-dev --compile-bytecode \
    && chown -R app:app /app

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000

# Drop root before the runtime CMD (ADR-014-security). /app and its venv are
# owned by `app`; gunicorn binds 8000 (>1024) so no extra capabilities needed.
USER 10001

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
