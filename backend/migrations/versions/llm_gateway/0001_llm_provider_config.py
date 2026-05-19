"""llm_gateway.llm_provider_config — provider registry seed.

DDL matches contracts/llm-gateway/schema.sql 1:1 (authoritative per ADR-024).
Seeded with 5 providers: deepseek (primary, ADR-018), yandexgpt, gigachat,
anthropic, openai. is_active=true for all; per-provider features per vendor docs.

Revision ID: llm_gateway_0001_llm_provider_config
Down revision: _shared_0002_current_user_id_helper
Branch label: llm_gateway
"""

from __future__ import annotations

from alembic import op

revision: str = "llm_gateway_0001_llm_provider_config"
down_revision: str | None = "_shared_0002_current_user_id_helper"
branch_labels: tuple[str, ...] = ("llm_gateway",)
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE llm_gateway.llm_provider_config (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_slug         text NOT NULL UNIQUE,
            display_name          text NOT NULL,
            default_model         text NOT NULL,
            base_url              text NOT NULL,
            is_byok_supported     boolean NOT NULL DEFAULT true,
            is_active             boolean NOT NULL DEFAULT true,
            supported_features    text[] NOT NULL DEFAULT '{}',
            created_at            timestamptz NOT NULL DEFAULT now(),
            updated_at            timestamptz NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE INDEX idx_llm_provider_config_active
            ON llm_gateway.llm_provider_config (is_active)
            WHERE is_active = true;
        """
    )

    op.execute(
        "COMMENT ON TABLE llm_gateway.llm_provider_config IS "
        "'Static registry of LLM providers. Cost-policy lives in cost-budget.yaml.';"
    )
    op.execute(
        "COMMENT ON COLUMN llm_gateway.llm_provider_config.supported_features IS "
        "'Capability flags. Used by router to filter providers per request type.';"
    )

    op.execute(
        """
        CREATE TRIGGER llm_provider_config_set_updated_at
            BEFORE UPDATE ON llm_gateway.llm_provider_config
            FOR EACH ROW EXECUTE FUNCTION _shared.set_updated_at();
        """
    )

    # Seed rows — per ADR-018 (DeepSeek primary). features per vendor capability.
    op.execute(
        """
        INSERT INTO llm_gateway.llm_provider_config
            (provider_slug, display_name, default_model, base_url,
             is_byok_supported, is_active, supported_features)
        VALUES
            ('deepseek',  'DeepSeek',  'deepseek-chat',
             'https://api.deepseek.com',
             true, true,
             ARRAY['chat','tool_use','structured_output']::text[]),
            ('yandexgpt', 'YandexGPT', 'yandexgpt-pro',
             'https://llm.api.cloud.yandex.net',
             true, true,
             ARRAY['chat','embeddings','tool_use']::text[]),
            ('gigachat',  'GigaChat',  'GigaChat-Pro',
             'https://gigachat.devices.sberbank.ru/api/v1',
             true, true,
             ARRAY['chat','tool_use','vision']::text[]),
            ('anthropic', 'Anthropic Claude', 'claude-sonnet-4-6',
             'https://api.anthropic.com',
             true, true,
             ARRAY['chat','tool_use','vision','structured_output']::text[]),
            ('openai',    'OpenAI',    'gpt-4o',
             'https://api.openai.com/v1',
             true, true,
             ARRAY['chat','embeddings','tool_use','vision','structured_output']::text[]);
        """
    )

    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE " "ON llm_gateway.llm_provider_config TO oriion_app;"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS llm_provider_config_set_updated_at "
        "ON llm_gateway.llm_provider_config;"
    )
    op.execute("DROP TABLE IF EXISTS llm_gateway.llm_provider_config;")
