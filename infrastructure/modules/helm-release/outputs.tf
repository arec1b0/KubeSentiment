output "name" {
  description = "The name of the release."
  value       = helm_release.this.name
}

output "status" {
  description = "The status of the release."
  value       = helm_release.this.status
}

output "namespace" {
  description = "The namespace the release is deployed in."
  value       = helm_release.this.namespace
}
