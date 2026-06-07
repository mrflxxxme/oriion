# Phase 00.6 PR-B — Managed Redis 7 (Dramatiq broker + JWT blacklist + SSE).

resource "random_password" "redis" {
  length  = 32
  special = false
}

resource "yandex_mdb_redis_cluster" "staging" {
  name        = "oriion-staging-redis"
  environment = var.pg_environment # mirror PG env (PRESTABLE for staging)
  network_id  = yandex_vpc_network.staging.id
  tls_enabled = true
  labels      = local.common_labels

  config {
    version  = var.redis_version
    password = random_password.redis.result
  }

  resources {
    resource_preset_id = var.redis_resource_preset
    disk_size          = var.redis_disk_gb
    disk_type_id       = "network-ssd"
  }

  host {
    zone      = var.yc_zone
    subnet_id = yandex_vpc_subnet.staging.id
  }
}

locals {
  redis_fqdn = yandex_mdb_redis_cluster.staging.host[0].fqdn

  # rediss:// (TLS) since tls_enabled = true. Port 6380 is the YC Redis TLS port.
  redis_url = format(
    "rediss://:%s@%s:6380/0",
    random_password.redis.result,
    local.redis_fqdn,
  )
}
