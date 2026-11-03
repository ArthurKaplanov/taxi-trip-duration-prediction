
output "cluster_id" {
  description = "Managed Kubernetes cluster ID"
  value       = yandex_kubernetes_cluster.taxi.id
}

output "cluster_name" {
  description = "Managed Kubernetes cluster name"
  value       = yandex_kubernetes_cluster.taxi.name
}

output "node_group_id" {
  description = "Kubernetes node group ID"
  value       = yandex_kubernetes_node_group.taxi.id
}

output "security_group_id" {
  description = "Kubernetes security group ID"
  value       = yandex_vpc_security_group.k8s.id
}
