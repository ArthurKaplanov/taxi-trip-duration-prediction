
output "network_id" {
  description = "ID of the shared Taxi VPC"
  value       = yandex_vpc_network.taxi.id
}

output "subnet_ids" {
  description = "Subnet IDs by logical purpose"

  value = {
    for key, subnet in yandex_vpc_subnet.taxi :
    key => subnet.id
  }
}

output "subnet_cidrs" {
  description = "Subnet IPv4 CIDR ranges"

  value = {
    for key, subnet in yandex_vpc_subnet.taxi :
    key => subnet.v4_cidr_blocks
  }
}

output "zone" {
  description = "Availability zone"
  value       = var.yc_config.zone
}
