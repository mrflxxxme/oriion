# Phase 00.6 PR-B — remote state in Yandex Object Storage (S3-compatible).
#
# BOOTSTRAP (one-time, by hand — the state bucket cannot be managed by the
# state it backs):
#
#   yc storage bucket create --name oriion-tfstate
#   # create an SA + static key with storage.editor, then:
#   export AWS_ACCESS_KEY_ID=<key_id>
#   export AWS_SECRET_ACCESS_KEY=<secret>
#   terraform init \
#     -backend-config="access_key=$AWS_ACCESS_KEY_ID" \
#     -backend-config="secret_key=$AWS_SECRET_ACCESS_KEY"
#
# For OFFLINE validation (no bucket / no creds) use:
#   terraform init -backend=false && terraform validate
#
# Yandex docs: https://yandex.cloud/docs/tutorials/infrastructure-management/terraform-state-storage

terraform {
  backend "s3" {
    endpoints = {
      s3 = "https://storage.yandexcloud.net"
    }
    bucket = "oriion-tfstate"
    region = "ru-central1"
    key    = "staging/terraform.tfstate"

    # Yandex Object Storage is S3-compatible but not AWS — skip the AWS-only
    # validation handshakes.
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}
