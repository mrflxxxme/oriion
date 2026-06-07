#!/usr/bin/env bash
# Phase 00.6 PR-B — roll the staging stack back to a previous image tag.
#
# Runs from an operator machine (SSHes into the VM). AC: rollback <= 2 min.
# Usage:
#   scripts/deploy/rollback.sh --to-sha <git-sha> --host <vm-ip> [--user deploy]
#   scripts/deploy/rollback.sh --self-test
#
# The target SHA must already exist in the YC Container Registry (it does if it
# was deployed before — images are tagged by commit SHA and never GC'd in Wave-0).

set -euo pipefail

TO_SHA=""
HOST=""
USER_NAME="deploy"

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --to-sha) TO_SHA="$2"; shift 2 ;;
      --host) HOST="$2"; shift 2 ;;
      --user) USER_NAME="$2"; shift 2 ;;
      --self-test) self_test; exit $? ;;
      -h|--help) usage 0 ;;
      *) echo "unknown arg: $1" >&2; usage 1 ;;
    esac
  done
}

remote_script() {
  # Printed (not executed) so --self-test can assert its shape offline.
  cat <<REMOTE
set -euo pipefail
cd /opt/oriion
export IMAGE_TAG="${TO_SHA}"
echo "\$IMAGE_TAG" > .deployed_tag
docker compose -f infra/docker-compose.staging.yml --env-file .env pull
docker compose -f infra/docker-compose.staging.yml --env-file .env up -d
bash scripts/deploy/wait_healthy.sh 120
REMOTE
}

self_test() {
  TO_SHA="abc1234"
  local out
  out="$(remote_script)"
  grep -q 'IMAGE_TAG="abc1234"' <<<"$out" || { echo "self-test FAIL: tag not threaded" >&2; return 1; }
  grep -q 'docker compose' <<<"$out" || { echo "self-test FAIL: no compose up" >&2; return 1; }
  grep -q 'wait_healthy.sh' <<<"$out" || { echo "self-test FAIL: no health wait" >&2; return 1; }
  echo "self-test: PASS"
}

main() {
  parse_args "$@"
  [ -n "$TO_SHA" ] || { echo "ERROR: --to-sha required" >&2; usage 1; }
  [ -n "$HOST" ] || { echo "ERROR: --host required" >&2; usage 1; }
  echo "rolling staging back to ${TO_SHA} on ${USER_NAME}@${HOST}..."
  remote_script | ssh "${USER_NAME}@${HOST}" 'bash -s'
  echo "rollback to ${TO_SHA} complete"
}

main "$@"
