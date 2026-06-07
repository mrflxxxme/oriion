# Phase 00.6 PR-B — outputs consumed by the deploy workflow + founder runbook.

output "vm_public_ip" {
  description = "Public IP of the staging VM — point staging.<brand_domain> A-record here."
  value       = yandex_compute_instance.staging.network_interface[0].nat_ip_address
}

output "vm_ssh_user" {
  description = "SSH user for deploy (matches deploy-staging.yml STAGING_VM_HOST login)."
  value       = var.ssh_user
}

output "vm_ssh_command" {
  description = "Convenience SSH command."
  value       = "ssh ${var.ssh_user}@${yandex_compute_instance.staging.network_interface[0].nat_ip_address}"
}

output "lockbox_secret_id" {
  description = "Lockbox secret id — deploy workflow resolves payload from here."
  value       = yandex_lockbox_secret.staging.id
}

output "pg_cluster_fqdn" {
  description = "Managed PostgreSQL primary host FQDN."
  value       = local.pg_fqdn
}

output "database_url" {
  description = "asyncpg DSN for the backend (also stored in Lockbox)."
  value       = local.database_url
  sensitive   = true
}

output "redis_url" {
  description = "TLS Redis DSN for the backend (also stored in Lockbox)."
  value       = local.redis_url
  sensitive   = true
}

output "loki_archive_bucket" {
  description = "Object Storage bucket for Loki 90d archival (Wave-1 wiring)."
  value       = yandex_storage_bucket.loki_archive.bucket
}

output "staging_fqdn" {
  description = "Staging FQDN the demo + deploy smoke-tests target."
  value       = "staging.${var.brand_domain}"
}
