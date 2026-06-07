# Phase 00.6 PR-B — DNS A-record for staging.<brand_domain>.
#
# Conditional (var.manage_dns, default false): only managed if oriion.dev is
# delegated to Yandex Cloud DNS. If the apex is registered with another
# registrar (the Wave-0 default), leave manage_dns=false and create the
# A-record manually at the registrar, pointing at the `vm_public_ip` output.

resource "yandex_dns_zone" "brand" {
  count       = var.manage_dns ? 1 : 0
  name        = "oriion-brand-zone"
  description = "Apex zone for ${var.brand_domain} (only if delegated to YC DNS)."
  zone        = "${var.brand_domain}."
  public      = true
  labels      = local.common_labels
}

resource "yandex_dns_recordset" "staging" {
  count   = var.manage_dns ? 1 : 0
  zone_id = yandex_dns_zone.brand[0].id
  name    = "staging.${var.brand_domain}."
  type    = "A"
  ttl     = 300
  data    = [yandex_compute_instance.staging.network_interface[0].nat_ip_address]
}
