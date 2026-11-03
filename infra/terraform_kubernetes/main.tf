
# ==================================================
# IAM
# ==================================================

resource "yandex_iam_service_account" "cluster" {
  name      = "taxi-k8s-cluster-sa"
  folder_id = var.yc_config.folder_id
}

resource "yandex_iam_service_account" "nodes" {
  name      = "taxi-k8s-nodes-sa"
  folder_id = var.yc_config.folder_id
}

# Cluster manages Kubernetes infrastructure
resource "yandex_resourcemanager_folder_iam_member" "cluster_agent" {
  folder_id = var.yc_config.folder_id
  role      = "k8s.clusters.agent"

  member = "serviceAccount:${yandex_iam_service_account.cluster.id}"
}

# Required for public cloud networking
resource "yandex_resourcemanager_folder_iam_member" "cluster_vpc" {
  folder_id = var.yc_config.folder_id
  role      = "vpc.publicAdmin"

  member = "serviceAccount:${yandex_iam_service_account.cluster.id}"
}

# Nodes pull images from Yandex Container Registry
resource "yandex_resourcemanager_folder_iam_member" "registry_puller" {
  folder_id = var.registry_folder_id
  role      = "container-registry.images.puller"

  member = "serviceAccount:${yandex_iam_service_account.nodes.id}"
}


# ==================================================
# Security Group
# ==================================================

resource "yandex_vpc_security_group" "k8s" {
  name       = "taxi-k8s-sg"
  network_id = var.network_id

  # Internal traffic between master and nodes
  ingress {
    description       = "Internal Kubernetes traffic"
    protocol          = "ANY"
    predefined_target = "self_security_group"
  }

  egress {
    description       = "Internal Kubernetes traffic"
    protocol          = "ANY"
    predefined_target = "self_security_group"
  }

  # Pod and Service network traffic
  ingress {
    description = "Pod and Service CIDRs"
    protocol    = "ANY"

    v4_cidr_blocks = [
      "10.96.0.0/16",
      "10.112.0.0/16"
    ]
  }

  # Node health checks from cloud private networks
  ingress {
    description = "Internal ICMP health checks"
    protocol    = "ICMP"

    v4_cidr_blocks = [
      "10.0.0.0/8",
      "172.16.0.0/12",
      "192.168.0.0/16"
    ]
  }

  # Cloud network load balancer health checks
  ingress {
    description       = "Load balancer health checks"
    protocol          = "TCP"
    from_port         = 0
    to_port           = 65535
    predefined_target = "loadbalancer_healthchecks"
  }

  # Kubernetes API access from administrator IP
  ingress {
    description    = "Kubernetes API HTTPS"
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "Kubernetes API"
    protocol       = "TCP"
    port           = 6443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Master metrics-server communication
  egress {
    description    = "Metrics server"
    protocol       = "TCP"
    port           = 4443
    v4_cidr_blocks = ["10.96.0.0/16"]
  }

  # Outbound internet access
  egress {
    description    = "Outbound cloud and internet access"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  labels = {
    project = "taxi-ml"
    layer   = "kubernetes"
  }
}


# ==================================================
# Managed Kubernetes Cluster
# ==================================================

resource "yandex_kubernetes_cluster" "taxi" {
  name        = "taxi-ml-cluster"
  description = "Taxi Trip Duration Prediction cluster"

  network_id = var.network_id

  cluster_ipv4_ranges = ["10.96.0.0/16"]
  service_ipv4_range  = "10.112.0.0/16"

  master {
    zonal {
      zone      = var.yc_config.zone
      subnet_id = var.subnet_id
    }

    public_ip = true

    security_group_ids = [
      yandex_vpc_security_group.k8s.id
    ]
  }

  service_account_id = yandex_iam_service_account.cluster.id

  node_service_account_id = yandex_iam_service_account.nodes.id

  release_channel = "STABLE"

  labels = {
    project = "taxi-ml"
    layer   = "kubernetes"
  }

  depends_on = [
    yandex_resourcemanager_folder_iam_member.cluster_agent,
    yandex_resourcemanager_folder_iam_member.cluster_vpc,
    yandex_resourcemanager_folder_iam_member.registry_puller
  ]
}


# ==================================================
# Kubernetes Node Group
# ==================================================

resource "yandex_kubernetes_node_group" "taxi" {
  cluster_id = yandex_kubernetes_cluster.taxi.id

  name        = "taxi-ml-node-group"
  description = "Budget worker node for ML inference"

  instance_template {
    platform_id = "standard-v3"

    resources {
      cores         = var.node_cpu
      memory        = var.node_memory
      core_fraction = var.node_core_fraction
    }

    boot_disk {
      type = "network-hdd"
      size = 64
    }

    network_interface {
      subnet_ids = [var.subnet_id]

      # Public IP for image pulling without NAT gateway
      nat = true

      security_group_ids = [
        yandex_vpc_security_group.k8s.id
      ]
    }

    scheduling_policy {
      preemptible = false
    }

    container_runtime {
      type = "containerd"
    }
  }

  scale_policy {
    fixed_scale {
      size = 1
    }
  }

  allocation_policy {
    location {
      zone = var.yc_config.zone
    }
  }

  maintenance_policy {
    auto_upgrade = true
    auto_repair  = true
  }

  labels = {
    project = "taxi-ml"
    layer   = "kubernetes"
  }
}
