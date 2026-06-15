#!/usr/bin/env sh
# AC-W1-20 — single-source role-prompts.
#
# Canonical role-prompts live in .planning/contracts/role-prompts/, which sits
# OUTSIDE the backend Docker build context (`backend/`). The prod image COPYs
# backend/role_prompts/, so we populate that directory from the canonical source
# at build time. backend/role_prompts/ is gitignored — never commit it; run this
# script before `docker build` / `docker compose build` (CI does so in a drift
# check; deploy-staging runs it before the image build).
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/.planning/contracts/role-prompts"
DST="$ROOT/backend/role_prompts"

mkdir -p "$DST"
# Mirror canonical exactly: drop stale .md first, then copy.
rm -f "$DST"/*.md
cp "$SRC"/*.md "$DST"/
echo "Synced $(ls "$SRC"/*.md | wc -l | tr -d ' ') role-prompts -> backend/role_prompts/"
