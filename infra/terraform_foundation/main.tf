
# ----------------------------------------------
# VPC Network
# ----------------------------------------------

resource "yandex_vpc_network" "taxi" {
  name        = var.network_name
  description = "Shared VPC for Taxi MLOps project"

  folder_id = var.yc_config.folder_id

  labels = {
    project = "taxi-ml"
    layer   = "foundation"
  }
}

# ----------------------------------------------
# Subnets
# ----------------------------------------------

resource "yandex_vpc_subnet" "taxi" {
  for_each = var.subnets

  name       = each.value.name
  folder_id  = var.yc_config.folder_id
  network_id = yandex_vpc_network.taxi.id

  zone = var.yc_config.zone

  v4_cidr_blocks = [
    each.value.cidr
  ]

  description = "Subnet for ${each.key} resources"

  labels = {
    project = "taxi-ml"
    layer   = "foundation"
    purpose = each.key
  }
}
