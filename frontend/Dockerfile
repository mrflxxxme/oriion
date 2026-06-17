# syntax=docker/dockerfile:1.7
# frontend/Dockerfile — Phase 00.1 dev-only build target.
# Prod target (Vite build → Caddy static serve) returns в Phase 00.6 deliverable
# когда `infra/caddy/Caddyfile.prod` materialized + правильный build context
# scope установлен (потребует подъёма build context на repo root level).

# Digest-pinned for reproducible/supply-chain-safe builds (ADR-014-security).
# Tag for humans: node:20-alpine. Re-pin via:
#   docker manifest inspect node:20-alpine --verbose | grep -m1 digest
FROM node:20-alpine@sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb AS base
WORKDIR /app
ENV CI=true \
    npm_config_audit=false \
    npm_config_fund=false

RUN apk add --no-cache wget

# ─────────────────────────────────────────────────────────────
FROM base AS dev
# Dev target: код mount-ится через volume в docker-compose.dev.yml.
# npm ci делается в container command (см. compose `command:`).
COPY package.json ./
EXPOSE 5173
CMD ["sh", "-c", "npm ci --no-audit --no-fund && npm run dev -- --host 0.0.0.0 --port 5173"]
