output "kubeconfig_path" {
  description = "The path to the kubeconfig file for the created cluster."
  value       = kind_cluster.default.kubeconfig_path
}

output "cluster_name" {
  description = "The name of the created Kind cluster."
  value       = kind_cluster.default.name
}
