# Runbook — audit_log archival to Object Storage (AC-W1-14)

`audit.audit_log` is an append-only, RANGE-partitioned ledger (ADR-014, ФЗ-152
3-year retention). UPDATE/DELETE are denied by trigger, so "archival" here means
**exporting** aged rows to RU-zone cold storage for durability — never purging.

## What runs

`backend/scripts/archive_audit_log.py`:

1. Selects `audit_log` rows with `ts < now() - AUDIT_RETENTION_DAYS` (default
   1095 days), oldest first.
2. Serializes them to gzipped JSONL (`src/audit/archival.py::serialize_audit_rows`,
   one row per line, non-ASCII preserved).
3. `PUT`s the object to the S3-compatible bucket under
   `audit_log/<YYYY>/<MM>/audit-before-<cutoff>-<generated>.jsonl.gz`.

An empty window is a clean no-op (nothing uploaded).

## Storage target

Yandex Object Storage (S3-compatible, RU-zone). Provision a dedicated bucket +
storage SA static key the same way as the Loki archive bucket
(`infra/terraform/object_storage.tf`). The bucket should carry a lifecycle rule
matching the regulatory retention (≥3 years) — note this is LONGER than the Loki
90d window; audit and logs have different retentions.

## Env vars

| Var | Default | Source |
|---|---|---|
| `DATABASE_URL` | — | Settings / Lockbox |
| `AUDIT_ARCHIVE_BUCKET` | — | Terraform output |
| `AUDIT_ARCHIVE_S3_ENDPOINT` | `https://storage.yandexcloud.net` | — |
| `AUDIT_ARCHIVE_S3_REGION` | `ru-central1` | — |
| `AUDIT_ARCHIVE_S3_ACCESS_KEY_ID` | — | Lockbox (storage SA key) |
| `AUDIT_ARCHIVE_S3_SECRET_ACCESS_KEY` | — | Lockbox (storage SA key) |
| `AUDIT_RETENTION_DAYS` | `1095` | — |

## Schedule

Run daily (low-traffic window). Options:

```bash
# cron on the VM (after `uv sync`):
15 3 * * *  cd /opt/oriion/backend && uv run python scripts/archive_audit_log.py
```

or a YC Cloud Function on a timer trigger invoking the same entrypoint. In Claude
Code, `/schedule` (or CronCreate) can register the recurring run.

## Verify

```bash
uv run python scripts/archive_audit_log.py            # logs audit.archival.done {object_key,row_count,byte_size}
aws --endpoint-url https://storage.yandexcloud.net s3 ls s3://$AUDIT_ARCHIVE_BUCKET/audit_log/ --recursive
```

The export logic (serialization, key derivation, run control flow) is covered by
`tests/audit/test_archival.py`.
