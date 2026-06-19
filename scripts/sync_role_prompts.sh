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

# Mirror canonical EXACTLY, including the masters/ subdir (AC-W1-3). Wipe then
# recursive-copy so a removed/renamed prompt never lingers in the packaged copy
# and the CI `diff -rq` (recursive) matches.
rm -rf "$DST"
mkdir -p "$DST"
cp -R "$SRC"/. "$DST"/
echo "Synced $(find "$SRC" -name '*.md' | wc -l | tr -d ' ') role-prompts -> backend/role_prompts/"
