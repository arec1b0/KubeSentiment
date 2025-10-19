/**
 * Variables for Vault Integration Module
 */

variable "secrets_mount_path" {
  description = "Path where KV v2 secrets engine will be mounted"
  type        = string
  default     = "mlops-sentiment"
}

variable "environment_prefix" {
  description = "Prefix for organizing secrets by application"
  type        = string
  default     = "mlops-sentiment"
}

variable "k8s_auth_path" {
  description = "Path for Kubernetes authentication method"
  type        = string
  default     = "kubernetes"
}

variable "kubernetes_host" {
  description = "Kubernetes API server URL"
  type        = string
}

variable "kubernetes_ca_cert" {
  description = "Kubernetes CA certificate (base64 encoded)"
  type        = string
  sensitive   = true
}

variable "kubernetes_token_reviewer_jwt" {
  description = "JWT token for Kubernetes token reviewer"
  type        = string
  sensitive   = true
}

variable "service_account_name" {
  description = "Kubernetes service account name for the application"
  type        = string
  default     = "mlops-sentiment"
}

variable "k8s_auth_audience" {
  description = "Audience for Kubernetes JWT authentication"
  type        = string
  default     = "vault"
}

variable "token_ttl" {
  description = "Default TTL for tokens in seconds"
  type        = number
  default     = 3600  # 1 hour
}

variable "token_max_ttl" {
  description = "Maximum TTL for tokens in seconds"
  type        = number
  default     = 28800  # 8 hours
}

variable "enable_github_actions_auth" {
  description = "Enable GitHub Actions JWT authentication"
  type        = bool
  default     = true
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository path (org/repo)"
  type        = string
  default     = ""
}

variable "enable_audit_logging" {
  description = "Enable audit logging to file"
  type        = bool
  default     = true
}

variable "secret_rotation_config" {
  description = "Configuration for automatic secret rotation"
  type = object({
    enabled                 = bool
    rotation_interval_days  = number
    warning_threshold_days  = number
  })
  default = {
    enabled                 = true
    rotation_interval_days  = 90
    warning_threshold_days  = 14
  }
}

variable "vault_namespace" {
  description = "Vault namespace (Enterprise feature)"
  type        = string
  default     = ""
}

# Database secrets engine configuration
variable "enable_database_secrets" {
  description = "Enable database secrets engine for PostgreSQL"
  type        = bool
  default     = false
}

variable "database_host" {
  description = "PostgreSQL database host"
  type        = string
  default     = "localhost"
}

variable "database_port" {
  description = "PostgreSQL database port"
  type        = number
  default     = 5432
}

variable "database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "mlops"
}

variable "database_username" {
  description = "PostgreSQL database username"
  type        = string
  default     = "vault"
  sensitive   = true
}

variable "database_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

# AWS secrets engine configuration
variable "enable_aws_secrets" {
  description = "Enable AWS secrets engine"
  type        = bool
  default     = false
}

variable "aws_access_key" {
  description = "AWS access key ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_secret_key" {
  description = "AWS secret access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_readonly_role_arn" {
  description = "AWS IAM role ARN for read-only access"
  type        = string
  default     = ""
}

variable "aws_readwrite_role_arn" {
  description = "AWS IAM role ARN for read-write access"
  type        = string
  default     = ""
}

# Azure secrets engine configuration
variable "enable_azure_secrets" {
  description = "Enable Azure secrets engine"
  type        = bool
  default     = false
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_client_id" {
  description = "Azure client ID (application ID)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_client_secret" {
  description = "Azure client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "azure_environment" {
  description = "Azure cloud environment"
  type        = string
  default     = "public"
}

# GCP secrets engine configuration
variable "enable_gcp_secrets" {
  description = "Enable GCP secrets engine"
  type        = bool
  default     = false
}

variable "gcp_service_account_key" {
  description = "GCP service account key (JSON)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {
    project     = "mlops-sentiment"
    managed_by  = "terraform"
  }
}

