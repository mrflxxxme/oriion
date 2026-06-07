# Phase 00.6 PR-B — Yandex Cloud staging baseline (provider config).
#
# Invoked manually in Wave 0 (founder runs `terraform init + plan + apply`).
# State is kept in Yandex Object Storage (S3-compatible) — see backend.tf.
#
# ФЗ-152: every regional resource pins zone = ru-central1-* (validated in
# variables.tf). No personal data ever leaves the RU region.

provider "yandex" {
  service_account_key_file = var.yc_sa_key_file
  cloud_id                 = var.yc_cloud_id
  folder_id                = var.yc_folder_id
  zone                     = var.yc_zone
}

locals {
  # Common labels for cost attribution + ownership across all resources.
  common_labels = {
    env     = "staging"
    project = "oriion"
    wave    = "0"
  }
}
