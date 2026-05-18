-- =====================================================================
-- Bounded context: iam (Identity & Access Management)
-- Owner: Oriion backend / iam-implementer
-- Authoritative source per ADR-024. Phase-specs MUST NOT duplicate DDL —
-- import via cross-link instead.
--
-- Scope of this file:
--   * users           — canonical person record (email-first, soft-delete)
--   * sessions        — active login sessions per user
--   * refresh_tokens  — single-use refresh tokens with rotation chain
--   * oauth_links     — external IdP linkages (Yandex / Google / VK / GitLab)
--
-- RLS: not applicable (system-level context). Access is controlled at the
-- application layer + service-account level. Per-cell isolation lives in
-- the `multitenancy` and `rbac` contexts which reference users.id.
--
-- Required extensions (created elsewhere, listed here for traceability):
--   CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()
--   CREATE EXTENSION IF NOT EXISTS "citext";    -- case-insensitive emails
-- =====================================================================

-- ---------------------------------------------------------------------
-- Table: users
-- Purpose:
--   Canonical person record. Email is the natural identifier; password is
--   stored as argon2id hash. Soft-delete via deleted_at (GDPR/ФЗ-152 purge
--   job removes the row after the retention window).
-- ---------------------------------------------------------------------
CREATE TABLE iam.users (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email               citext NOT NULL,
    email_verified_at   timestamptz,
    password_hash       text,
    password_algo       text NOT NULL DEFAULT 'argon2id'
        CHECK (password_algo IN ('argon2id')),
    display_name        text,
    locale              text NOT NULL DEFAULT 'ru-RU',
    timezone            text NOT NULL DEFAULT 'Europe/Moscow',
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    deleted_at          timestamptz
);

-- Unique active email (case-insensitive via citext); soft-deleted rows
-- keep their email but cannot collide with live ones.
CREATE UNIQUE INDEX users_email_active_uidx
    ON iam.users (email)
    WHERE deleted_at IS NULL;

CREATE INDEX users_deleted_at_idx
    ON iam.users (deleted_at)
    WHERE deleted_at IS NOT NULL;

CREATE INDEX users_created_at_desc_idx
    ON iam.users (created_at DESC);

COMMENT ON TABLE  iam.users IS 'Canonical user identity. Soft-delete via deleted_at; hard purge by retention job.';
COMMENT ON COLUMN iam.users.password_algo IS 'Only argon2id allowed. md5/sha1/bcrypt-legacy MUST NOT be introduced.';

-- ---------------------------------------------------------------------
-- Table: sessions
-- Purpose:
--   One row per active browser/device session. Holds enough fingerprint
--   data to support session-management UI (list / revoke). Expiry is hard
--   (expires_at); revoked_at marks early termination.
-- ---------------------------------------------------------------------
CREATE TABLE iam.sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
    ip_address      inet,
    user_agent      text,
    fingerprint     text,
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX sessions_user_id_idx       ON iam.sessions (user_id);
CREATE INDEX sessions_expires_at_idx    ON iam.sessions (expires_at);
CREATE INDEX sessions_active_idx        ON iam.sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;

COMMENT ON TABLE iam.sessions IS 'Active login sessions per user. ON DELETE CASCADE from users.';

-- ---------------------------------------------------------------------
-- Table: refresh_tokens
-- Purpose:
--   Single-use refresh tokens. Rotation chain enables detection of token
--   reuse attacks: if a previously-used token is presented again, the
--   whole rotation_chain_id is revoked.
-- ---------------------------------------------------------------------
CREATE TABLE iam.refresh_tokens (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          uuid NOT NULL REFERENCES iam.sessions(id) ON DELETE CASCADE,
    token_hash          text NOT NULL,
    rotated_to          uuid REFERENCES iam.refresh_tokens(id) ON DELETE SET NULL,
    rotation_chain_id   uuid NOT NULL,
    issued_at           timestamptz NOT NULL DEFAULT now(),
    expires_at          timestamptz NOT NULL,
    used_at             timestamptz,
    revoked_at          timestamptz
);

CREATE UNIQUE INDEX refresh_tokens_hash_uidx ON iam.refresh_tokens (token_hash);
CREATE INDEX refresh_tokens_session_id_idx   ON iam.refresh_tokens (session_id);
CREATE INDEX refresh_tokens_chain_idx        ON iam.refresh_tokens (rotation_chain_id);
CREATE INDEX refresh_tokens_active_idx       ON iam.refresh_tokens (session_id, expires_at)
    WHERE used_at IS NULL AND revoked_at IS NULL;

COMMENT ON TABLE iam.refresh_tokens IS 'Single-use refresh tokens. Reuse of a used token revokes the entire rotation_chain_id.';

-- ---------------------------------------------------------------------
-- Table: oauth_links
-- Purpose:
--   External IdP linkages. Provider tokens are stored encrypted (AES-256-GCM,
--   key per environment via KMS). One (provider, provider_user_id) pair
--   maps to at most one user.
-- ---------------------------------------------------------------------
CREATE TABLE iam.oauth_links (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                     uuid REFERENCES iam.users(id) ON DELETE SET NULL,
    provider                    text NOT NULL
        CHECK (provider IN ('yandex','google','vk','gitlab')),
    provider_user_id            text NOT NULL,
    access_token_encrypted      bytea,
    refresh_token_encrypted     bytea,
    expires_at                  timestamptz,
    created_at                  timestamptz NOT NULL DEFAULT now(),
    updated_at                  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX oauth_links_provider_uid_uidx
    ON iam.oauth_links (provider, provider_user_id);
CREATE INDEX oauth_links_user_id_idx
    ON iam.oauth_links (user_id);

COMMENT ON TABLE  iam.oauth_links IS 'External IdP linkages. Tokens encrypted AES-256-GCM with KMS-managed keys.';
COMMENT ON COLUMN iam.oauth_links.access_token_encrypted IS 'Ciphertext only. Plaintext MUST NOT be logged or persisted.';

-- ---------------------------------------------------------------------
-- Table: consents
-- Purpose:
--   FZ-152 / GDPR consent ledger. One row per (user, kind) grant. The
--   `pdn` consent is mandatory before register completes (enforced at
--   service layer — DB allows historical rows for soft-deleted users).
--   Revocation is soft (revoked_at). Version is pinned at grant time so
--   future Privacy Policy revisions do not retroactively change what the
--   user agreed to.
-- ---------------------------------------------------------------------
CREATE TABLE iam.consents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
    kind            text NOT NULL
        CHECK (kind IN ('pdn','marketing','tos')),
    version         text NOT NULL,
    ip              inet,
    user_agent      text,
    granted_at      timestamptz NOT NULL DEFAULT now(),
    revoked_at      timestamptz
);

CREATE INDEX consents_user_kind_active_idx
    ON iam.consents (user_id, kind)
    WHERE revoked_at IS NULL;

CREATE INDEX consents_user_id_idx ON iam.consents (user_id);

COMMENT ON TABLE  iam.consents IS
    'FZ-152 / GDPR consent ledger. pdn is mandatory before register; revocation is soft.';
COMMENT ON COLUMN iam.consents.version IS
    'Privacy Policy / consent-form version pinned at grant time. Never mutated.';

-- ---------------------------------------------------------------------
-- Table: email_verification_tokens
-- Purpose:
--   Single-use email-ownership proof tokens. Plaintext is sent via email
--   only; storage holds SHA-256 hex hash so a DB read alone cannot complete
--   verification. Expires after 24h. used_at marks consumption.
-- ---------------------------------------------------------------------
CREATE TABLE iam.email_verification_tokens (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
    token_hash      text NOT NULL,
    expires_at      timestamptz NOT NULL,
    used_at         timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX email_verification_tokens_hash_uidx
    ON iam.email_verification_tokens (token_hash);
CREATE INDEX email_verification_tokens_user_active_idx
    ON iam.email_verification_tokens (user_id, expires_at)
    WHERE used_at IS NULL;

COMMENT ON TABLE iam.email_verification_tokens IS
    'Single-use email-verification tokens. SHA-256 hashed before storage; plaintext only over email.';

-- ---------------------------------------------------------------------
-- Table: password_reset_tokens
-- Purpose:
--   Single-use password-reset tokens. Plaintext sent via email only; storage
--   holds SHA-256 hex hash. Expires after 1h. Reuse of a consumed token
--   triggers chain-revoke of every outstanding reset token for the user
--   (mirrors refresh-token rotation pattern). Belongs to a `reset_chain_id`
--   so chain-revoke can be implemented without scanning all rows.
-- ---------------------------------------------------------------------
CREATE TABLE iam.password_reset_tokens (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES iam.users(id) ON DELETE CASCADE,
    token_hash          text NOT NULL,
    reset_chain_id      uuid NOT NULL,
    expires_at          timestamptz NOT NULL,
    used_at             timestamptz,
    revoked_at          timestamptz,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX password_reset_tokens_hash_uidx
    ON iam.password_reset_tokens (token_hash);
CREATE INDEX password_reset_tokens_user_id_idx
    ON iam.password_reset_tokens (user_id);
CREATE INDEX password_reset_tokens_chain_idx
    ON iam.password_reset_tokens (reset_chain_id);
CREATE INDEX password_reset_tokens_user_active_idx
    ON iam.password_reset_tokens (user_id, expires_at)
    WHERE used_at IS NULL AND revoked_at IS NULL;

COMMENT ON TABLE iam.password_reset_tokens IS
    'Single-use password-reset tokens. Reuse of a used token revokes the entire reset_chain_id.';

-- ---------------------------------------------------------------------
-- Updated_at trigger pattern (applied via shared function in `_shared.sql`).
-- Listed here as a reminder for the implementer; actual function definition
-- lives in the global migration bootstrap (see _shared/0001_init.py).
-- ---------------------------------------------------------------------
-- CREATE TRIGGER users_set_updated_at        BEFORE UPDATE ON iam.users        FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
-- CREATE TRIGGER oauth_links_set_updated_at  BEFORE UPDATE ON iam.oauth_links  FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
