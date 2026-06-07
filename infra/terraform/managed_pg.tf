# Phase 00.6 PR-B — Managed PostgreSQL 16 (pgvector-enabled).

resource "random_password" "pg" {
  length  = 32
  special = false # avoid DSN-encoding headaches in DATABASE_URL
}

resource "yandex_mdb_postgresql_cluster" "staging" {
  name        = "oriion-staging-pg"
  environment = var.pg_environment
  network_id  = yandex_vpc_network.staging.id
  labels      = local.common_labels

  config {
    version = "16"
    resources {
      resource_preset_id = var.pg_resource_preset
      disk_size          = var.pg_disk_gb
      disk_type_id       = "network-ssd"
    }
    backup_window_start {
      hours   = 3
      minutes = 0
    }
  }

  host {
    zone             = var.yc_zone
    subnet_id        = yandex_vpc_subnet.staging.id
    assign_public_ip = false # ФЗ-152 + least-exposure; reached intra-SG
  }
}

resource "yandex_mdb_postgresql_database" "oriion" {
  cluster_id = yandex_mdb_postgresql_cluster.staging.id
  name       = var.pg_database
  owner      = yandex_mdb_postgresql_user.app.name

  # pgvector for embeddings (memory bounded-context) + the extensions the
  # _shared/0001_init migration expects to already exist.
  extension {
    name = "vector"
  }
  extension {
    name = "pg_stat_statements"
  }
}

resource "yandex_mdb_postgresql_user" "app" {
  cluster_id = yandex_mdb_postgresql_cluster.staging.id
  name       = var.pg_user
  password   = random_password.pg.result
  # conn_limit + grants tuned in Wave-1; Wave-0 uses defaults.
}

locals {
  pg_fqdn = yandex_mdb_postgresql_cluster.staging.host[0].fqdn

  # asyncpg DSN consumed by the backend (DATABASE_URL). sslmode=verify-full
  # would need the YC root CA on the VM (installed via cloud-init).
  database_url = format(
    "postgresql+asyncpg://%s:%s@%s:6432/%s",
    var.pg_user,
    random_password.pg.result,
    local.pg_fqdn,
    var.pg_database,
  )
}
