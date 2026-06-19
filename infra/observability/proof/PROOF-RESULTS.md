# AC-W1-14 / AC-W1-15 — live proof results

Run locally on real containers (Docker) on 2026-06-19. Re-runnable:

```bash
cd infra/observability/proof && bash run-proof.sh
```

`run-proof.sh` stands up MinIO + Loki + Alertmanager + a webhook sink, exercises
each acceptance against real services, and tears the stack down on exit.

## AC-W1-14 — Loki 90d + S3 chunk archival

**Loki chunks land in the S3 bucket.** Loki runs the real
[`../loki.yaml`](../loki.yaml) (S3 backend + `retention_period: 2160h` + compactor)
pointed at MinIO. After pushing logs and forcing an ingester flush, the bucket
holds chunk objects under the `fake/` (default-tenant) prefix plus the compactor's
`index/delete_requests/` marker:

```
mc ls --recursive m/loki-archive
[...]  STANDARD fake/ebef7dfa35d83653/19edf73f0d0:19edf73f0d1:bb7fdbc9
[...]  STANDARD index/delete_requests/delete_requests.gz
[...]  STANDARD loki_cluster_seed.json
PASS: AC-W1-14 — Loki chunks landed in the S3 bucket (fake/ tenant prefix)
```

**audit_log archival uploads a real object.** The real `archive_audit_log` +
a real boto3 S3 client serialize rows to gzipped JSONL and upload to the bucket;
the object is then downloaded back and the line count verified:

```
UPLOADED s3://loki-archive/audit_log/2026/06/01/audit_log_before_20260601T000000Z.jsonl.gz rows=2 bytes=222
DOWNLOADED bytes=222 lines=2
PASS: AC-W1-14 — audit_log archival object uploaded + round-tripped from the bucket
```

## AC-W1-15 — Alertmanager Telegram + PagerDuty receivers

**Config validity (real receivers).** `amtool check-config` on the real
[`../alertmanager.yml`](../alertmanager.yml) (env-expanded with dummy secrets)
parses both receivers:

```
Checking '/cfg/am.expanded.yml'  SUCCESS
 - route
 - 1 inhibit rules
 - 2 receivers
```

**Routing pipeline (live).** A `severity=critical` alert posted to Alertmanager is
routed and DELIVERED to the `pager-and-telegram` receiver (the critical route),
observed at the webhook sink:

```
"path": "/pager-and-telegram",
"body": {"receiver":"pager-and-telegram","status":"firing","alerts":[{"labels":{"alertname":"ProofCostRunaway","severity":"critical","service":"proof"}, ...}]}
PASS: AC-W1-15 — critical alert routed + delivered to the pager-and-telegram receiver
```

## What remains a deploy-time action (not a code/config gap)

The real network hop to **your** Telegram chat + PagerDuty service needs the live
secrets (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` / `PAGERDUTY_ROUTING_KEY` from
YC Lockbox) and the real S3 credentials (`LOKI_S3_*`, `AUDIT_ARCHIVE_S3_*`). The
proof swaps those for a local MinIO + webhook sink; on staging the same configs
run with Lockbox-injected secrets. This is the same deploy-time boundary as the
AC-W1-9 staging cutover and the live golden run.
```
PROOF RESULT: ALL PASS
```
