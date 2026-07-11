# ADR-007: Auth — Custom JWT (Wave 0-1) → Logto (Wave 2-3) → Keycloak (Enterprise)

- **Status:** Accepted

> **Amendment 2026-07-11 (founder-grill D-16, Wave-2 planning):** миграция на Logto в W2–3 **снята**. Auth упрощён до email-only (RW-02 снята, 01.8b descoped), кастомный стек вырос в полноценный (2FA TOTP + magic-link + session-management, 01.8) — миграция не даёт продуктовой ценности. Остаёмся на custom JWT через W2–W3; **триггер пересмотра — enterprise-спрос на SSO/SAML/OIDC** (тогда решение Logto-vs-Keycloak заново). OAuth-провайдеры (Yandex ID / VK ID) из «Wave 1 extensions» ниже — descoped тем же решением.

## Decision

### Wave 0-1: Custom JWT-auth на FastAPI

**Module:** `backend/src/iam/`

**Endpoints (Wave 0):**
- `POST /api/auth/register` — email + password + consent_pdn → user + verification-email
- `POST /api/auth/verify` — email-token → email_verified=true
- `POST /api/auth/login` — email + password → JWT + refresh_token
- `POST /api/auth/refresh` — refresh → new JWT
- `POST /api/auth/logout` — blacklist current JWT (Redis)
- `GET /api/auth/me` — current user info
- `POST /api/auth/forgot-password` → reset email
- `POST /api/auth/reset-password` — token + new password

**Wave 1 extensions:**
- `POST /api/auth/magic-link` — passwordless email-link login
- `POST /api/auth/2fa/setup` + `verify` — TOTP via `pyotp`
- `POST /api/auth/oauth/{provider}/start` + callback — Yandex ID, VK ID OAuth-flow

### Wave 2-3: Logto self-hosted

**Триггеры миграции:**
- Multi-IdP federation (enterprise SSO)
- Custom OAuth-server (мы выступаем как IdP для partner-приложений)
- Advanced device management / session-list UI
- Расширение social-logins за пределы Yandex/VK

**Migration approach:**
- Logto deployment в k8s (одновременно с k8s migration в Wave 4)
- Bcrypt-hashes совместимы
- Users экспортируются через Logto Admin API
- Cutover window ~2 часа maintenance

### Wave 4+: Keycloak параллельно

Только для Enterprise-клиентов с SAML/AD/LDAP/SSO в обязательном чек-листе закупки:
- Keycloak self-hosted в отдельном k8s namespace
- Federate Logto ↔ Keycloak (Logto для self-serve, Keycloak для enterprise SSO)
- Custom IdP-mapping per tenant

## Technical implementation (Wave 0-1)

### Tech stack

| Слой | Решение |
|---|---|
| JWT generation | `pyjwt` library |
| Password hash | `bcrypt` (cost factor 12+) |
| Refresh tokens | Stored в Postgres `iam.refresh_tokens` с FK на user |
| JWT blacklist | Redis (TTL = refresh-token TTL) |
| OAuth2 (Wave 1) | `httpx-oauth` library |
| 2FA TOTP | `pyotp` library |
| Email | SMTP (Wave 0-1: Yandex 360 / Mail.ru Pro), notisend (Wave 2+) |
| Rate-limit | Redis-based (5 login/15min per IP+email) |
| HIBP-check | hibp.io API при register (опц., Wave 1) |

### Database schema

```sql
-- iam.users
id uuid PK
email varchar UNIQUE NOT NULL
email_verified boolean DEFAULT false
password_hash varchar NOT NULL
created_at timestamptz
updated_at timestamptz
last_login_at timestamptz

-- iam.consents (ФЗ-152)
id uuid PK
user_id uuid FK
consent_type varchar  -- 'pdn_processing', 'marketing', 'cross_border_transfer'
granted boolean
granted_at timestamptz
ip_address inet
user_agent text

-- iam.refresh_tokens
id uuid PK
user_id uuid FK
token_hash varchar UNIQUE
issued_at timestamptz
expires_at timestamptz
revoked_at timestamptz NULL
device_label varchar  -- для session-list UI

-- iam.email_verification_tokens, iam.password_reset_tokens — similar

-- iam.totp_secrets (Wave 1)
user_id uuid FK
secret varchar  -- encrypted с APP_KEY
backup_codes varchar[]
enabled_at timestamptz
```

### JWT structure

```
{
  "sub": "<user_uuid>",
  "email": "user@example.com",
  "exp": <ts>,
  "iat": <ts>,
  "jti": "<unique-jwt-id>",
  "type": "access" | "refresh",
  "consents": ["pdn_processing"]
}
```

- Access JWT TTL: **15 минут**
- Refresh token TTL: **7 дней**
- Refresh rotation: при каждом refresh → новый refresh + revoke предыдущий

### Email provider

- **Wave 0-1:** Yandex 360 SMTP (smtp.yandex.ru:587 TLS), bесплатно до 200/день
- **Wave 2+:** Notisend / UniSender для >500 писем/день

### Security checklist

- JWT короткий TTL + refresh rotation
- Bcrypt cost 12+
- Email verification mandatory before first task
- Rate-limit на login + register (5/15min per IP+email)
- HIBP-check при register (опц., Wave 1)
- 2FA mandatory для Owner/Admin (Wave 1)
- Session-list UI («где я залогинен») — Wave 2
- Refresh-tokens revocable из БД + Redis blacklist
- Audit log всех auth-событий → `audit.audit_log`
- HTTPS only (Caddy auto-TLS)
- Cookies: HttpOnly, Secure, SameSite=Lax
- CSRF-protection via SameSite + Origin-check для mutations
- Pen-test перед public-launch (Wave 2)

### Wave 1 OAuth

- **Yandex ID** — официальная OAuth2, доступен из РФ
- **VK ID** — официальная OAuth2 + VK Pay integration
- Mapping: при первом OAuth-логине → создаётся local user; oauth_provider/oauth_subject_id заполняются
- Linking: если email уже есть — merge с подтверждением через email

## Ownership и pipeline

Implementation owner — `backend-implementer` (см. [ADR-023](./ADR-023-ai-team-runtime.md)). Quality gate — `reviewer-backend` + `reviewer-security` (tier 4 per [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md): architecture + security + billing + migrations требуют 3 AI reviewers + explicit founder approve + ADR-link). Deployment секреты — per [ADR-015](./ADR-015-ai-dev-process.md) isolation policy (никаких production credentials в AI-context'е).

Schema `iam.*` фиксируется в [`contracts/iam/schema.sql`](../contracts/iam/) per [ADR-024](./ADR-024-bounded-context-contracts.md) — Alembic migrations лежат в `backend/alembic/versions/iam/`.

## Links

- Risks: [R-05](../risks/REGISTER.md), [R-21](../risks/REGISTER.md), [R-22](../risks/REGISTER.md)
- Phase: 00.2 (custom auth), 04.12 (Logto migration)
- Related ADRs: ADR-014 (security), ADR-009 (multitenancy), [ADR-023](./ADR-023-ai-team-runtime.md) (AI-team runtime), [ADR-024](./ADR-024-bounded-context-contracts.md) (`iam` bounded context), [ADR-027](./ADR-027-solo-ai-git-pr-workflow.md) (tier-table)
