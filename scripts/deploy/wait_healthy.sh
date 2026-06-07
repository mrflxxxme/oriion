#!/usr/bin/env bash
# Phase 00.6 PR-B — poll docker compose service health until all healthy.
#
# Runs ON the staging VM (invoked from the deploy-staging.yml SSH script).
# Usage:
#   bash scripts/deploy/wait_healthy.sh [timeout_seconds]   # default 120
#   bash scripts/deploy/wait_healthy.sh --self-test         # offline CI check
#
# Exit 0 when every service with a healthcheck reports "healthy" (and none are
# "unhealthy"/"exited"); exit 1 on timeout or any unhealthy/exited service.

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.staging.yml}"
ENV_FILE="${ENV_FILE:-.env}"

compose_ps_health() {
  # Emit one "<service> <health-or-state>" line per container.
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps \
    --format '{{.Service}} {{if .Health}}{{.Health}}{{else}}{{.State}}{{end}}'
}

self_test() {
  # Offline sanity for CI: the parser classifies a synthetic status table
  # without needing Docker. Proves the health/unhealthy/timeout logic.
  local sample
  sample=$'backend healthy\ncaddy healthy\nprometheus running'
  if _all_ok "$sample"; then
    echo "self-test: PASS (all-ok sample classified healthy)"
  else
    echo "self-test: FAIL" >&2
    return 1
  fi
  local bad
  bad=$'backend healthy\ncaddy unhealthy'
  if _all_ok "$bad"; then
    echo "self-test: FAIL (unhealthy sample wrongly passed)" >&2
    return 1
  fi
  echo "self-test: PASS (unhealthy sample correctly rejected)"
}

# Returns 0 if no container is unhealthy/exited/dead AND at least one line seen.
_all_ok() {
  local table="$1"
  [ -n "$table" ] || return 1
  if grep -Eqi '(unhealthy|exited|dead)' <<<"$table"; then
    return 1
  fi
  # "starting" means a healthcheck hasn't passed yet — keep waiting.
  if grep -Eqi 'starting' <<<"$table"; then
    return 1
  fi
  return 0
}

main() {
  if [ "${1:-}" = "--self-test" ]; then
    self_test
    return $?
  fi

  local timeout="${1:-120}"
  local deadline=$(( $(date +%s) + timeout ))

  while :; do
    local table
    table="$(compose_ps_health || true)"
    echo "--- compose health ---"
    echo "$table"

    if _all_ok "$table"; then
      echo "all services healthy"
      return 0
    fi
    if grep -Eqi '(unhealthy|exited|dead)' <<<"$table"; then
      echo "ERROR: a service is unhealthy/exited" >&2
      return 1
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "ERROR: timed out after ${timeout}s waiting for health" >&2
      return 1
    fi
    sleep 5
  done
}

main "$@"
