# Phase 00.6 PR-B — input variables. Founder fills terraform.tfvars
# (gitignored; see terraform.tfvars.example for the template).

# ── Auth + placement ──────────────────────────────────────────────────────

variable "yc_sa_key_file" {
  description = "Path to the Yandex service-account key JSON (authorized_key)."
  type        = string
  default     = "~/.yc/sa-key.json"
}

variable "yc_cloud_id" {
  description = "Yandex Cloud cloud_id."
  type        = string
}

variable "yc_folder_id" {
  description = "Yandex Cloud folder_id (staging)."
  type        = string
}

variable "yc_zone" {
  description = "Availability zone — MUST be ru-central1-* for ФЗ-152 compliance."
  type        = string
  default     = "ru-central1-a"

  validation {
    condition     = can(regex("^ru-central1-", var.yc_zone))
    error_message = "ФЗ-152: zone must be in the RU region (ru-central1-*). Personal data may not leave РФ."
  }
}

# ── Networking ─────────────────────────────────────────────────────────────

variable "subnet_cidr" {
  description = "IPv4 CIDR for the staging subnet."
  type        = string
  default     = "10.10.0.0/24"
}

# ── Compute (VM) ───────────────────────────────────────────────────────────

variable "vm_cores" {
  description = "VM vCPU count."
  type        = number
  default     = 4
}

variable "vm_memory_gb" {
  description = "VM RAM in GiB."
  type        = number
  default     = 8
}

variable "vm_disk_gb" {
  description = "VM boot disk size in GiB."
  type        = number
  default     = 50
}

variable "vm_image_family" {
  description = "Compute image family for the VM boot disk."
  type        = string
  default     = "ubuntu-2404-lts"
}

variable "ssh_user" {
  description = "Linux user provisioned on the VM for deploy/SSH."
  type        = string
  default     = "deploy"
}

variable "ssh_public_key_file" {
  description = "Path to the deploy SSH public key (injected into VM metadata)."
  type        = string
  default     = "~/.ssh/oriion-deploy.pub"
}

# ── Managed PostgreSQL ─────────────────────────────────────────────────────

variable "pg_resource_preset" {
  description = "Managed PostgreSQL host preset (per phase-spec: s2.medium)."
  type        = string
  default     = "s2.medium"
}

variable "pg_disk_gb" {
  description = "Managed PostgreSQL disk size in GiB."
  type        = number
  default     = 100
}

variable "pg_environment" {
  description = "PRESTABLE (staging) or PRODUCTION."
  type        = string
  default     = "PRESTABLE"
}

variable "pg_database" {
  description = "Application database name."
  type        = string
  default     = "oriion"
}

variable "pg_user" {
  description = "Application DB role (matches backend DATABASE_URL user)."
  type        = string
  default     = "oriion_app"
}

# ── Managed Redis ──────────────────────────────────────────────────────────

variable "redis_resource_preset" {
  description = "Managed Redis host preset."
  type        = string
  default     = "hm3-c2-m8" # adjust per quota; small staging node
}

variable "redis_disk_gb" {
  description = "Managed Redis disk size in GiB."
  type        = number
  default     = 16
}

variable "redis_version" {
  description = "Redis major version."
  type        = string
  default     = "7.2"
}

# ── DNS ────────────────────────────────────────────────────────────────────

variable "brand_domain" {
  description = "Brand apex domain. Staging FQDN is staging.<brand_domain>."
  type        = string
  default     = "oriion.dev"
}

variable "manage_dns" {
  description = <<-EOT
    Whether Terraform manages the DNS zone + A-record for staging.<brand_domain>.
    Set true ONLY if oriion.dev is delegated to Yandex Cloud DNS. If the domain
    is registered elsewhere (default), leave false and create the A-record
    manually pointing at the vm_public_ip output (see README).
  EOT
  type        = bool
  default     = false
}

# ── Lockbox secret values (sensitive — founder supplies via tfvars) ────────
# These become Lockbox entries the backend reads at startup. Empty defaults
# keep `terraform plan` runnable; founder MUST fill real values before apply.

variable "lockbox_deepseek_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "lockbox_yandex_gpt_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "lockbox_yandex_gpt_catalog_id" {
  type    = string
  default = ""
}

variable "lockbox_gigachat_auth_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "lockbox_jwt_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "lockbox_byok_master_key_b64" {
  type      = string
  sensitive = true
  default   = ""
}

variable "lockbox_grafana_admin_user" {
  type    = string
  default = "admin"
}

variable "lockbox_grafana_admin_password" {
  type      = string
  sensitive = true
  default   = ""
}
