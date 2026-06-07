# Phase 00.6 PR-B — VPC network, subnet, security group.

resource "yandex_vpc_network" "staging" {
  name   = "oriion-staging-net"
  labels = local.common_labels
}

resource "yandex_vpc_subnet" "staging" {
  name           = "oriion-staging-subnet"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.staging.id
  v4_cidr_blocks = [var.subnet_cidr]
  labels         = local.common_labels
}

# Security group: allow HTTP/HTTPS in from anywhere (Caddy ACME + serving),
# SSH from anywhere (deploy — tighten to office IP in Wave-1 hardening), and
# all egress. Managed PG/Redis live in the same SG with no public IP.
resource "yandex_vpc_security_group" "staging" {
  name       = "oriion-staging-sg"
  network_id = yandex_vpc_network.staging.id
  labels     = local.common_labels

  ingress {
    protocol       = "TCP"
    description    = "HTTP (ACME HTTP-01 + redirect)"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 80
  }

  ingress {
    protocol       = "TCP"
    description    = "HTTPS"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 443
  }

  ingress {
    protocol       = "TCP"
    description    = "SSH (deploy) — restrict to known IPs in Wave-1"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  ingress {
    protocol          = "ANY"
    description       = "Intra-SG (VM <-> managed PG/Redis)"
    predefined_target = "self_security_group"
    from_port         = 0
    to_port           = 65535
  }

  egress {
    protocol       = "ANY"
    description    = "All egress (LLM providers, package mirrors, ACME)"
    v4_cidr_blocks = ["0.0.0.0/0"]
    from_port      = 0
    to_port        = 65535
  }
}
