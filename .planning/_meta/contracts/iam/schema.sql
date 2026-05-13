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
-- Updated_at trigger pattern (applied via shared function in `_shared.sql`).
-- Listed here as a reminder for the implementer; actual function definition
-- lives in the global migration bootstrap.
-- ---------------------------------------------------------------------
-- CREATE TRIGGER users_set_updated_at        BEFORE UPDATE ON iam.users        FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
-- CREATE TRIGGER oauth_links_set_updated_at  BEFORE UPDATE ON iam.oauth_links  FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
