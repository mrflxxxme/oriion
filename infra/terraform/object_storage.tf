# Phase 00.6 PR-B — Object Storage bucket for Loki long-term log archival.
#
# Wave-0 Loki keeps 7d retention on the VM disk; AC-W1-14 raises retention to
# 90d + ships chunks to this RU-zone bucket (ФЗ-152: audit-log ledger stays in
# РФ). The bucket is created here so the Wave-1 archival wiring has a target.
#
# NOTE: the Terraform *state* bucket (backend.tf) is a SEPARATE, pre-existing
# bucket the founder bootstraps once by hand — it cannot be managed by the same
# state it backs (chicken-and-egg). This bucket is app-data only.

# A dedicated SA + static access key are required for the S3-compatible API.
resource "yandex_iam_service_account" "storage" {
  name        = "oriion-staging-storage-sa"
  description = "S3 access for Loki archival bucket."
}

resource "yandex_resourcemanager_folder_iam_member" "storage_editor" {
  folder_id = var.yc_folder_id
  role      = "storage.editor"
  member    = "serviceAccount:${yandex_iam_service_account.storage.id}"
}

resource "yandex_iam_service_account_static_access_key" "storage" {
  service_account_id = yandex_iam_service_account.storage.id
  description        = "Static key for Loki S3 archival."
}

resource "yandex_storage_bucket" "loki_archive" {
  bucket     = "oriion-staging-loki-archive"
  access_key = yandex_iam_service_account_static_access_key.storage.access_key
  secret_key = yandex_iam_service_account_static_access_key.storage.secret_key

  anonymous_access_flags {
    read = false
    list = false
  }

  # 90-day lifecycle aligns with the AC-W1-14 retention target.
  lifecycle_rule {
    id      = "expire-90d"
    enabled = true
    expiration {
      days = 90
    }
  }
}
