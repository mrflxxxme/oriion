"""SQLAlchemy 2.x models for iam bounded context.

Schema is authoritative per .planning/contracts/iam/schema.sql (ADR-024).
Tables live under PostgreSQL schema `iam`. Migrations:
  backend/migrations/versions/iam/0001..0006_*.py
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src._shared.db.base import Base


def _uuid_pk() -> Mapped[UUID]:
    """uuid primary key with DB-side gen_random_uuid() default."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _ts_default_now() -> Mapped[datetime]:
    return mapped_column(server_default=text("now()"), nullable=False)


class User(Base):
    """Canonical user identity. Soft-delete via deleted_at."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("password_algo IN ('argon2id')", name="users_password_algo_check"),
        Index(
            "users_email_active_uidx",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "users_deleted_at_idx",
            "deleted_at",
            postgresql_where=text("deleted_at IS NOT NULL"),
        ),
        Index("users_created_at_desc_idx", text("created_at DESC")),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_algo: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'argon2id'")
    )
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'ru-RU'"))
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Europe/Moscow'")
    )
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    consents: Mapped[list[Consent]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[list[EmailVerificationToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OAuthLink(Base):
    """External IdP linkage. DDL-only in Wave 0; OAuth code lands in Wave 1."""

    __tablename__ = "oauth_links"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('yandex','google','vk','gitlab')",
            name="oauth_links_provider_check",
        ),
        Index(
            "oauth_links_provider_uid_uidx",
            "provider",
            "provider_user_id",
            unique=True,
        ),
        Index("oauth_links_user_id_idx", "user_id"),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = _ts_default_now()
    updated_at: Mapped[datetime] = _ts_default_now()


class Consent(Base):
    """FZ-152 / GDPR consent grant/revoke ledger."""

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint("kind IN ('pdn','marketing','tos')", name="consents_kind_check"),
        Index(
            "consents_user_kind_active_idx",
            "user_id",
            "kind",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("consents_user_id_idx", "user_id"),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime] = _ts_default_now()
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="consents")


class Session(Base):
    """Active login session per user/device."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("sessions_user_id_idx", "user_id"),
        Index("sessions_expires_at_idx", "expires_at"),
        Index(
            "sessions_active_idx",
            "user_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = _ts_default_now()
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = _ts_default_now()

    user: Mapped[User] = relationship(back_populates="sessions")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Single-use refresh token with OWASP rotation chain."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("refresh_tokens_hash_uidx", "token_hash", unique=True),
        Index("refresh_tokens_session_id_idx", "session_id"),
        Index("refresh_tokens_chain_idx", "rotation_chain_id"),
        Index(
            "refresh_tokens_active_idx",
            "session_id",
            "expires_at",
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rotated_to: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    rotation_chain_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    issued_at: Mapped[datetime] = _ts_default_now()
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    session: Mapped[Session] = relationship(back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    """Single-use email-ownership proof; SHA-256 hashed."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index("email_verification_tokens_hash_uidx", "token_hash", unique=True),
        Index(
            "email_verification_tokens_user_active_idx",
            "user_id",
            "expires_at",
            postgresql_where=text("used_at IS NULL"),
        ),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = _ts_default_now()

    user: Mapped[User] = relationship(back_populates="email_verification_tokens")


class PasswordResetToken(Base):
    """Single-use reset token with reset_chain_id chain-revoke."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("password_reset_tokens_hash_uidx", "token_hash", unique=True),
        Index("password_reset_tokens_user_id_idx", "user_id"),
        Index("password_reset_tokens_chain_idx", "reset_chain_id"),
        Index(
            "password_reset_tokens_user_active_idx",
            "user_id",
            "expires_at",
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
        {"schema": "iam"},
    )

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    reset_chain_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = _ts_default_now()

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")
