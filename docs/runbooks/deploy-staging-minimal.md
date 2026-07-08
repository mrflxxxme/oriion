# Deploy — minimal single-box pilot (Timeweb Cloud)

Low-budget, always-on staging for a friends pilot: **one RU VPS**, all datastores
self-hosted, local KMS, free GHCR images. ~500–850 ₽/мес. Real e-mail via a free
personal Yandex app-password. Data stays in RU (152-ФЗ-friendly).

Artifacts this runbook uses:
- `infra/docker-compose.vps-minimal.yml` — standalone stack (no observability; inline pg/redis/minio).
- `infra/staging-minimal.env.example` — env template → copy to `infra/vps-minimal.env` (gitignored).
- `.github/workflows/build-images-ghcr.yml` — builds backend+frontend → GHCR (free).

> Cost/scope: this is a **pilot**. Local-KMS keeps the master key in the env file
> on the box; plain env instead of Lockbox. Fine behind a locked-down VPS. Before
> a real prod launch with third-party money/keys → move to Yandex KMS
> (`KMS_BACKEND=local→yandex`) + Lockbox. See "Upgrade path" at the bottom.

---

## 0. Prerequisites (once)
- A domain (e.g. `example.ru`) with DNS you control. *(Optional for a first test — you can run IP-only, see step 6.)*
- A **Yandex app-password** for SMTP: a personal `@yandex.ru` account → [id.yandex.ru](https://id.yandex.ru) → Security → **App passwords → Mail**. Free; best deliverability to RU inboxes.
- The funded LLM keys from `backend/.env` (DeepSeek / GigaChat / Yandex / Brave).
- GitHub access to this repo (for GHCR images).

---

## 1. Build the images (GHCR, free)
1. GitHub → **Actions → build-images-ghcr → Run workflow** (branch `main`).
2. It pushes `ghcr.io/<owner>/oriion-backend:latest` and `…/oriion-frontend:latest`.
3. Make the two packages **public** (repo → Packages → each → Package settings → Change visibility → Public) so the VPS can pull without a token. *(Or keep private and `docker login ghcr.io` on the VPS with a PAT that has `read:packages`.)*

---

## 2. Provision the VPS (Timeweb Cloud)
1. [timeweb.cloud](https://timeweb.cloud) → Cloud servers → **Create**.
2. **Ubuntu 24.04 LTS**, **2 vCPU / 4 GB RAM / 40–60 GB SSD**, region РФ (Москва/СПб).
3. Add your **SSH public key**. Create. Note the public IP.

---

## 3. Base setup + hardening (on the VPS, as root)
```bash
adduser deploy && usermod -aG sudo deploy
# harden SSH: set 'PasswordAuthentication no' in /etc/ssh/sshd_config, then: systemctl reload ssh
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```
Log back in as `deploy` for the rest.

---

## 4. DNS
Point a subdomain at the VPS:
```
A   staging.example.ru   ->   <VPS_IP>     (TTL 5 min)
```
*(No domain yet? Skip — use IP-only mode in step 6.)*

---

## 5. Get the code + fill the env (as `deploy`)
```bash
git clone https://github.com/<owner>/<repo>.git && cd <repo>
cp infra/staging-minimal.env.example infra/vps-minimal.env
```
Generate the three secrets and paste them into `infra/vps-minimal.env`:
```bash
echo "BYOK_MASTER_KEY_B64=$(openssl rand -base64 32)"
echo "JWT_SECRET_ACCESS_V1=$(openssl rand -hex 32)"
echo "PG_PASSWORD=$(openssl rand -hex 16)"
echo "MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)"
```
Then edit `infra/vps-minimal.env` and set:
- `YC_CR_REGISTRY=ghcr.io/<owner>` · `IMAGE_TAG=latest`
- the four secrets above
- `SMTP_USER` / `SMTP_PASSWORD` (Yandex app-password) / `SMTP_FROM`
- `EMAIL_VERIFY_URL_BASE=https://staging.example.ru/verify-email`
- the funded LLM keys
- `CADDY_SITE_ADDR=staging.example.ru` · `CADDY_ACME_EMAIL=you@example.ru` · leave `CADDY_GLOBAL_OPTS=` empty

`infra/vps-minimal.env` is gitignored — it never leaves the box.

---

## 6. Bring the stack up
Always run **from the repo root** with `--env-file`. Helper alias:
```bash
alias dc='docker compose --env-file infra/vps-minimal.env -f infra/docker-compose.vps-minimal.yml'
```
Apply DB migrations (first boot + after any release with new migrations):
```bash
dc run --rm backend alembic upgrade head
# if `alembic` isn't on PATH in the image, use:  dc run --rm backend uv run alembic upgrade head
```
Start everything:
```bash
dc pull            # get the GHCR images (skip + add `--build` to build on the VPS)
dc up -d
dc ps              # all services healthy?
```
**IP-only test without a domain:** in `infra/vps-minimal.env` set `CADDY_SITE_ADDR=:80`
and `CADDY_GLOBAL_OPTS=auto_https off`, open `http://<VPS_IP>/healthz` (no TLS).

---

## 7. TLS
With a real `CADDY_SITE_ADDR` FQDN and empty `CADDY_GLOBAL_OPTS`, Caddy obtains a
Let's Encrypt cert automatically on first request. Verify:
```bash
curl -fsS https://staging.example.ru/healthz     # -> 200
```
If it fails: check port 80/443 open (ufw), DNS resolves to the VPS, `dc logs caddy`.

---

## 8. Smoke test (this closes the deferred 01.8-mail live-send gate)
1. Open `https://staging.example.ru`, **register** with a real inbox.
2. **Verification e-mail arrives** → this is the live proof that `YandexSmtpEmailSender` works.
3. Log in → submit the demo **«Маркет-бриф»** → watch the 3-agent SSE progress → get the artifact.
4. Optional: enable 2FA (TOTP) and test the magic-link login.

Ping me after step 2 and I'll formally close the 01.8-mail live-send follow-up.

---

## 9. Backups (do this before real users)
```bash
# nightly pg dump (cron for the deploy user):
0 3 * * * cd ~/<repo> && docker compose --env-file infra/vps-minimal.env -f infra/docker-compose.vps-minimal.yml \
  exec -T postgres pg_dump -U oriion oriion | gzip > ~/backups/pg-$(date +\%F).sql.gz
```
Also enable **Timeweb server snapshots** (covers the `minio_data` / `pg_data` volumes).

---

## 10. Updates / redeploy
```bash
# after build-images-ghcr publishes a new :latest (or set IMAGE_TAG to a sha):
dc pull backend worker frontend
dc run --rm backend alembic upgrade head   # only if the release added migrations
dc up -d
```

---

## Troubleshooting
- **Boot fails "insecure config in app_env='staging'"** → a secret is still a dev default: set real `JWT_SECRET_ACCESS_V1`, `BYOK_MASTER_KEY_B64`, and a non-default `PG_PASSWORD`.
- **No e-mail** → `APP_ENV` must be `staging` (it is, in the compose) AND both `SMTP_USER`+`SMTP_PASSWORD` set; check `dc logs backend | grep -i smtp`. A wrong app-password → auth error in logs.
- **Caddy no cert** → DNS/ports; temporarily use IP-only mode to isolate.
- **`createbuckets` exited** → that's expected; it's a one-shot bucket creator.
- **Out of RAM** → the observability stack is intentionally NOT in this compose; if you added it, drop back to this file.

---

## Upgrade path (when the pilot graduates)
| Pilot (this runbook) | Production |
|---|---|
| Local-KMS (`BYOK_MASTER_KEY_B64` in env) | Yandex KMS (`KMS_BACKEND=yandex` + `YANDEX_CLOUD_KMS_KEY_ID`) |
| Plain `infra/vps-minimal.env` | YC Lockbox (`LOCKBOX_SECRET_ID`, nothing on disk) |
| Self-hosted pg/redis/minio on one box | Yandex Managed PG/Redis + Object Storage |
| Personal Yandex From | Domain + Yandex 360 / RU ESP branded sender |
| No РКН filing needed for a mock/low-data test | РКН оператора-ПДн notification before real-user PII |

The code already supports every right-hand column via env/config — the upgrade is
configuration, not a rewrite.
