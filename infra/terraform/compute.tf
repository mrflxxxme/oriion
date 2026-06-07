# Phase 00.6 PR-B — single staging VM (Docker Compose host).

data "yandex_compute_image" "ubuntu" {
  family = var.vm_image_family
}

resource "yandex_compute_instance" "staging" {
  name        = "oriion-staging-vm"
  platform_id = "standard-v3"
  zone        = var.yc_zone
  labels      = local.common_labels

  resources {
    cores  = var.vm_cores
    memory = var.vm_memory_gb
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = var.vm_disk_gb
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.staging.id
    nat                = true # public IP for Caddy ACME + serving
    security_group_ids = [yandex_vpc_security_group.staging.id]
  }

  metadata = {
    ssh-keys  = "${var.ssh_user}:${file(var.ssh_public_key_file)}"
    user-data = local.cloud_init
  }
}

locals {
  # cloud-init: install Docker Engine + compose plugin, create /opt/oriion,
  # and install the Russian Trusted Root CA (GigaChat TLS chain). The deploy
  # workflow (deploy-staging.yml) rsyncs infra/ + runs `docker compose up`.
  cloud_init = <<-EOT
    #cloud-config
    package_update: true
    packages:
      - ca-certificates
      - curl
      - rsync
    runcmd:
      - install -m 0755 -d /etc/apt/keyrings
      - curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
      - chmod a+r /etc/apt/keyrings/docker.asc
      - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
      - apt-get update
      - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
      - usermod -aG docker ${var.ssh_user}
      - mkdir -p /opt/oriion
      - chown -R ${var.ssh_user}:${var.ssh_user} /opt/oriion
      - curl -fsSL "https://storage.yandexcloud.net/cloud-certs/RootCA.pem" -o /usr/local/share/ca-certificates/yandex-root.crt || true
      - update-ca-certificates || true
  EOT
}
