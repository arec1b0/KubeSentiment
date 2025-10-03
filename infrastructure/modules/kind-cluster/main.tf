resource "kind_cluster" "default" {
  name           = var.cluster_name
  wait_for_ready = true
  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }

    node {
      role = "worker"
    }
  }
}

output "kubeconfig" {
  value = kind_cluster.default.kubeconfig
}

output "cluster_name" {
  value = kind_cluster.default.name
}
