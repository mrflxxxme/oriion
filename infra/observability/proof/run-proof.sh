#!/usr/bin/env bash
# AC-W1-14 / AC-W1-15 live proof driver.
#
# Proves, against real local containers:
#   1. Loki ships chunks to the S3 bucket (AC-W1-14) — pushes logs through the
#      REAL loki.yaml (S3 + 90d + compactor), forces a flush via graceful
#      shutdown, then lists the MinIO bucket for chunk objects.
#   2. Alertmanager routes a fired alert (AC-W1-15) — posts a severity=critical
#      alert and confirms it was DELIVERED to the `pager-and-telegram` receiver
#      (the critical route), observed in the webhook sink log.
#
# Usage:  bash run-proof.sh
# Cleanup happens automatically on exit. Requires Docker.
#
# NOTE: do NOT set MSYS_NO_PATHCONV here — on Git-Bash the host paths ($DIR) must
# convert to Windows paths for `docker compose -f` and `uv run python`; the only
# in-container args we pass (mc alias `m/loki-archive`, URLs) don't start with '/'
# so they are never mangled.
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE=(docker compose -f "$DIR/docker-compose.proof.yml" -p obsproof)
NET=obsproof_default
PASS=1

cleanup() { "${COMPOSE[@]}" down -v >/dev/null 2>&1 || true; }
trap cleanup EXIT

retry() { # retry <secs> <cmd...>
  local n=$1; shift
  for _ in $(seq 1 "$n"); do "$@" >/dev/null 2>&1 && return 0; sleep 1; done
  return 1
}

echo "### clean slate (fresh alertmanager state + minio bucket) ..."
"${COMPOSE[@]}" down -v >/dev/null 2>&1
echo "### bringing up minio + loki + alertmanager + sink ..."
"${COMPOSE[@]}" up -d >/dev/null 2>&1

echo "### waiting for loki + alertmanager ready ..."
retry 60 curl -fs http://localhost:13100/ready             || { echo "FAIL: loki not ready"; PASS=0; }
retry 60 curl -fs http://localhost:19093/-/ready            || { echo "FAIL: alertmanager not ready"; PASS=0; }
retry 60 curl -fs http://localhost:19000/minio/health/live  || { echo "FAIL: minio not ready"; PASS=0; }

# ── Proof 1: Loki chunks land in the S3 bucket ────────────────────────────
echo "### [AC-W1-14] pushing logs to Loki ..."
NS=$(date +%s)000000000
for i in 1 2 3 4 5; do
  curl -fs -H "Content-Type: application/json" -XPOST http://localhost:13100/loki/api/v1/push \
    -d "{\"streams\":[{\"stream\":{\"job\":\"obs-proof\",\"n\":\"$i\"},\"values\":[[\"$NS\",\"proof log line $i — chunk-archival evidence\"]]}]}" \
    >/dev/null 2>&1
  NS=$((NS+1))
done
echo "### forcing an ingester flush to the S3 store ..."
retry 10 curl -fs -XPOST http://localhost:13100/flush
sleep 5
echo "### listing MinIO bucket loki-archive ..."
LISTING=$(docker run --rm --network "$NET" --entrypoint sh minio/mc:RELEASE.2025-04-16T18-13-26Z -c \
  "mc alias set m http://minio:9000 proofkey proofsecret123 >/dev/null 2>&1 && mc ls --recursive m/loki-archive" 2>&1)
echo "$LISTING"
if echo "$LISTING" | grep -qiE "fake/"; then
  echo "PASS: AC-W1-14 — Loki chunks landed in the S3 bucket (fake/ tenant prefix)"
else
  echo "FAIL: AC-W1-14 — no chunk objects found in loki-archive bucket"; PASS=0
fi

# ── Proof 1b: audit_log archival uploads a real object to the bucket ──────
echo "### [AC-W1-14] audit_log archival -> S3 (real boto3 upload) ..."
ARCHOUT=$(cd "$DIR/../../../backend" && uv run python "$DIR/archival_proof.py" 2>&1)
if echo "$ARCHOUT" | grep -q "ARCHIVAL_PROOF PASS"; then
  echo "$ARCHOUT" | grep -E "UPLOADED|DOWNLOADED"
  echo "PASS: AC-W1-14 — audit_log archival object uploaded + round-tripped from the bucket"
else
  echo "FAIL: AC-W1-14 — audit_log archival upload proof failed"; PASS=0
  echo "$ARCHOUT" | tail -15
fi

# ── Proof 2: Alertmanager routes a critical alert to the pager receiver ────
echo "### [AC-W1-15] firing a severity=critical alert ..."
curl -fs -H "Content-Type: application/json" -XPOST http://localhost:19093/api/v2/alerts \
  -d '[{"labels":{"alertname":"ProofCostRunaway","severity":"critical","service":"proof"},"annotations":{"summary":"R-04 cost runaway (proof)"}}]' \
  >/dev/null 2>&1
sleep 9
SINKLOG=$("${COMPOSE[@]}" logs sink 2>&1)
if echo "$SINKLOG" | grep -q "/pager-and-telegram"; then
  echo "PASS: AC-W1-15 — critical alert routed + delivered to the pager-and-telegram receiver"
  echo "$SINKLOG" | grep -iE "ProofCostRunaway|/pager-and-telegram|/telegram-default" | head -5
else
  echo "FAIL: AC-W1-15 — alert not observed at the sink"; PASS=0
  echo "--- alertmanager logs ---"; "${COMPOSE[@]}" logs --tail 15 alertmanager 2>&1 | tail -15
  echo "--- sink logs ---"; echo "$SINKLOG" | tail -10
fi

echo "============================================================"
[ "$PASS" = 1 ] && echo "PROOF RESULT: ALL PASS" || echo "PROOF RESULT: FAIL"
exit $((1 - PASS))
