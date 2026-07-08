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

# ─────────────────────────────────────────────────────────────
# Build target: reproducible SPA build → /app/dist.
# The SPA calls the API same-origin (frontend/src/api/client.ts:
# API_BASE = "/api/v1"), so NO build-time API URL / build-arg is needed.
FROM base AS build
# Deterministic install from the committed lockfile (npm ci).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
# Rest of the sources (vite.config, tsconfig, index.html, src/, public/…).
COPY . .
# build = "tsc -b --noEmit && vite build" (package.json) → dist/ (vite outDir).
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Prod target (LAST stage → default when no `target` is given).
# Tiny one-shot "publisher": carries the built dist and, on run, copies it into
# the /srv/frontend volume Caddy serves from (Caddyfile.staging root */srv/
# frontend + try_files {path} /index.html). Then exits 0. Caddy waits on this
# via depends_on: condition: service_completed_successfully.
# Tag for humans: alpine:3.20. Re-pin via `docker manifest inspect alpine:3.20`
# if supply-chain digest pinning is desired later (not mandatory for the pilot).
FROM alpine:3.20 AS prod
WORKDIR /opt
# Built assets baked into the image; copied out to the shared volume at runtime.
COPY --from=build /app/dist /opt/frontend-dist
# One-shot: replace the volume contents with the freshly built dist, then exit.
# `cp -a .../.` copies the directory *contents* (incl. dotfiles) into /srv/frontend.
CMD ["sh", "-c", "rm -rf /srv/frontend/* 2>/dev/null; cp -a /opt/frontend-dist/. /srv/frontend/ && echo published"]
