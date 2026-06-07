# Phase 00.6 PR-B — Yandex Lockbox secret (backend reads at startup).
#
# The docker-compose.staging.yml backend service maps ${LOCKBOX_*} env-vars.
# In Wave-0 the deploy workflow resolves these from Lockbox via `yc lockbox
# payload get` and writes them into the VM's /opt/oriion/.env before
# `docker compose up`. AC-W1-9 swaps this for the backend reading Lockbox
# directly via SDK at startup (no .env materialization on disk).

resource "yandex_lockbox_secret" "staging" {
  name        = "oriion-staging-secrets"
  description = "Wave-0 staging secrets — DB/Redis DSNs + LLM keys + JWT + Grafana."
  labels      = local.common_labels
}

resource "yandex_lockbox_secret_version" "staging" {
  secret_id = yandex_lockbox_secret.staging.id

  # DB + Redis DSNs are computed from the managed clusters above.
  entries {
    key        = "DATABASE_URL"
    text_value = local.database_url
  }
  entries {
    key        = "REDIS_URL"
    text_value = local.redis_url
  }

  # LLM provider keys + JWT + BYOK master — founder-supplied via tfvars.
  entries {
    key        = "DEEPSEEK_API_KEY"
    text_value = var.lockbox_deepseek_api_key
  }
  entries {
    key        = "YANDEX_GPT_API_KEY"
    text_value = var.lockbox_yandex_gpt_api_key
  }
  entries {
    key        = "YANDEX_GPT_CATALOG_ID"
    text_value = var.lockbox_yandex_gpt_catalog_id
  }
  entries {
    key        = "GIGACHAT_AUTH_KEY"
    text_value = var.lockbox_gigachat_auth_key
  }
  entries {
    key        = "JWT_SECRET"
    text_value = var.lockbox_jwt_secret
  }
  entries {
    key        = "BYOK_MASTER_KEY_B64"
    text_value = var.lockbox_byok_master_key_b64
  }

  # Grafana admin — also Lockbox-injected (closes F-SEC-M1 committed-password).
  entries {
    key        = "GRAFANA_ADMIN_USER"
    text_value = var.lockbox_grafana_admin_user
  }
  entries {
    key        = "GRAFANA_ADMIN_PASSWORD"
    text_value = var.lockbox_grafana_admin_password
  }
}
