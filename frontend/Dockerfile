# syntax=docker/dockerfile:1.7
# frontend/Dockerfile — multi-stage build с dev + prod targets.
# Dev: hot-reload via Vite dev server + volume mount.
# Prod: static build → served by Caddy (Phase 00.6).

FROM node:20-alpine AS base
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
FROM base AS build
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2-alpine AS prod
COPY --from=build /app/dist /srv
COPY infra/caddy/Caddyfile.prod /etc/caddy/Caddyfile
