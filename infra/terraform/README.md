# Terraform — Yandex Cloud staging baseline (Phase 00.6 PR-B)

Infra-as-code for the single-VM `oriion` staging stack in `ru-central1`.
Founder runs this manually in Wave-0 (Stage B of Phase 00.6).

## What it provisions

| Resource | File | Notes |
|---|---|---|
| VPC network + subnet + security group | `network.tf` | 80/443/22 ingress; intra-SG for managed DBs |
| Compute VM (4 vCPU / 8 GiB / 50 GiB SSD) | `compute.tf` | Ubuntu 24.04 + cloud-init (Docker + `/opt/oriion` + RU CA) |
| Managed PostgreSQL 16 (`s2.medium` / 100 GiB) | `managed_pg.tf` | pgvector + pg_stat_statements; no public IP |
| Managed Redis 7 (TLS) | `managed_redis.tf` | Dramatiq broker + JWT blacklist + SSE |
| Lockbox secret | `lockbox.tf` | DB/Redis DSNs (computed) + LLM keys + JWT + Grafana |
| Object Storage bucket | `object_storage.tf` | Loki 90d archival (Wave-1 AC-W1-14 target) |
| DNS A-record (conditional) | `dns.tf` | only if `manage_dns=true`; else create manually |

**ФЗ-152:** `var.yc_zone` has a validation block forcing `ru-central1-*`. All
personal data stays in the РФ region. Managed PG/Redis have no public IP.

## Prerequisites

- Terraform ≥ 1.9 (`winget install Hashicorp.Terraform`).
- `yc` CLI authenticated; service-account key JSON at `~/.yc/sa-key.json`
  (or set `yc_sa_key_file`). SA needs: `compute.admin`, `vpc.admin`,
  `mdb.admin`, `lockbox.admin`, `storage.admin`, `iam.serviceAccounts.user`,
  and (if `manage_dns`) `dns.admin`.
- Deploy SSH keypair: `ssh-keygen -t ed25519 -f ~/.ssh/oriion-deploy`.

## State backend bootstrap (one-time)

The state bucket can't be managed by the state it backs. Create it once:

```bash
yc storage bucket create --name oriion-tfstate
# create an SA static key with storage.editor; then export:
export AWS_ACCESS_KEY_ID=<key_id>
export AWS_SECRET_ACCESS_KEY=<secret>
```

## Run

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # then fill secrets
terraform init \
  -backend-config="access_key=$AWS_ACCESS_KEY_ID" \
  -backend-config="secret_key=$AWS_SECRET_ACCESS_KEY"
terraform plan
terraform apply
```

Offline syntax/schema check (no creds/bucket needed):

```bash
terraform fmt -check
terraform init -backend=false && terraform validate
```

## After apply

1. Note outputs: `terraform output vm_public_ip`, `lockbox_secret_id`, `staging_fqdn`.
2. **DNS:** if `manage_dns=false`, create an `A` record at your registrar:
   `staging.oriion.dev → <vm_public_ip>`. Wait for propagation (Caddy needs it
   resolving for the ACME HTTP-01 challenge).
3. Set the GitHub Actions secrets/vars the deploy workflow needs
   (see `docs/runbooks/staging-bootstrap.md`):
   - secrets: `YC_SA_JSON`, `STAGING_SSH_KEY`, `STAGING_VM_HOST` (= vm_public_ip),
     `GRAFANA_API_KEY`
   - vars: `YC_CR_FOLDER`, `STAGING_DOMAIN` (= staging.oriion.dev), `GRAFANA_URL`
4. Trigger the first deploy: `gh workflow run deploy-staging.yml` (or push to `main`).
5. Bootstrap the demo user + run the 10× demo per `docs/runbooks/staging-bootstrap.md`.

## Teardown

```bash
terraform destroy
```

> ⚠️ `terraform apply` provisions billable resources (VM + managed PG + Redis).
> Estimated staging cost is modest but non-zero — `terraform destroy` when the
> demo evidence is captured if you don't need staging running continuously.

## Wave-1 hardening pins

- **AC-W1-9** — backend reads Lockbox directly via SDK at startup (drop the
  `.env` materialization on the VM done by the deploy workflow).
- **AC-W1-14** — wire Loki chunk shipping to `loki_archive` bucket (90d).
- Tighten SSH ingress (`network.tf`) from `0.0.0.0/0` to known IPs.
