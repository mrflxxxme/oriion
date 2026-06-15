# AC-W1-20 — single-source role-prompts (PowerShell mirror of sync_role_prompts.sh).
#
# Canonical .planning/contracts/role-prompts/ -> backend/role_prompts/ (gitignored,
# build-populated). Run before `docker build` / `docker compose build` on Windows.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root '.planning/contracts/role-prompts'
$dst = Join-Path $root 'backend/role_prompts'

New-Item -ItemType Directory -Force -Path $dst | Out-Null
# Mirror canonical exactly: drop stale .md first, then copy.
Get-ChildItem -Path $dst -Filter '*.md' -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item -Path (Join-Path $src '*.md') -Destination $dst -Force
Write-Host 'Synced role-prompts -> backend/role_prompts/'
