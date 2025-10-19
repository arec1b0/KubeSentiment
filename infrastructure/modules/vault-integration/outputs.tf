/**
 * Outputs for Vault Integration Module
 */

output "secrets_mount_path" {
  description = "Path where KV v2 secrets engine is mounted"
  value       = vault_mount.kv_v2.path
}

output "k8s_auth_path" {
  description = "Path for Kubernetes authentication backend"
  value       = vault_auth_backend.kubernetes.path
}

output "vault_role_dev" {
  description = "Vault role name for development environment"
  value       = vault_kubernetes_auth_backend_role.mlops_dev.role_name
}

output "vault_role_staging" {
  description = "Vault role name for staging environment"
  value       = vault_kubernetes_auth_backend_role.mlops_staging.role_name
}

output "vault_role_prod" {
  description = "Vault role name for production environment"
  value       = vault_kubernetes_auth_backend_role.mlops_prod.role_name
}

output "vault_policy_dev" {
  description = "Vault policy name for development environment"
  value       = vault_policy.mlops_dev.name
}

output "vault_policy_staging" {
  description = "Vault policy name for staging environment"
  value       = vault_policy.mlops_staging.name
}

output "vault_policy_prod" {
  description = "Vault policy name for production environment"
  value       = vault_policy.mlops_prod.name
}

output "vault_policy_admin" {
  description = "Vault admin policy name for CI/CD and secret rotation"
  value       = vault_policy.mlops_admin.name
}

output "github_actions_jwt_path" {
  description = "JWT auth path for GitHub Actions"
  value       = var.enable_github_actions_auth ? vault_jwt_auth_backend.github_actions[0].path : null
}

output "github_actions_role" {
  description = "JWT auth role for GitHub Actions"
  value       = var.enable_github_actions_auth ? vault_jwt_auth_backend_role.github_actions[0].role_name : null
}

output "secret_paths" {
  description = "Secret paths structure for each environment"
  value = {
    dev = {
      base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/dev"
      common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
    }
    staging = {
      base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/staging"
      common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
    }
    prod = {
      base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/prod"
      common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
    }
  }
}

output "token_ttl" {
  description = "Default token TTL in seconds"
  value       = var.token_ttl
}

output "token_max_ttl" {
  description = "Maximum token TTL in seconds"
  value       = var.token_max_ttl
}

# Database secrets engine outputs
output "database_mount_path" {
  description = "Path where database secrets engine is mounted"
  value       = var.enable_database_secrets ? vault_mount.database[0].path : null
}

output "database_connection_name" {
  description = "Database connection name"
  value       = var.enable_database_secrets ? vault_database_secret_backend_connection.postgresql[0].name : null
}

output "database_roles" {
  description = "Database roles created"
  value = var.enable_database_secrets ? {
    readonly  = vault_database_secret_backend_role.readonly[0].name
    readwrite = vault_database_secret_backend_role.readwrite[0].name
  } : {}
}

# AWS secrets engine outputs
output "aws_mount_path" {
  description = "Path where AWS secrets engine is mounted"
  value       = var.enable_aws_secrets ? vault_mount.aws[0].path : null
}

output "aws_roles" {
  description = "AWS roles created"
  value = var.enable_aws_secrets ? {
    readonly  = vault_aws_secret_backend_role.readonly[0].name
    readwrite = vault_aws_secret_backend_role.readwrite[0].name
  } : {}
}

# Azure secrets engine outputs
output "azure_mount_path" {
  description = "Path where Azure secrets engine is mounted"
  value       = var.enable_azure_secrets ? vault_mount.azure[0].path : null
}

output "azure_roles" {
  description = "Azure roles created"
  value = var.enable_azure_secrets ? {
    readonly    = vault_azure_secret_backend_role.readonly[0].name
    contributor = vault_azure_secret_backend_role.contributor[0].name
  } : {}
}

# GCP secrets engine outputs
output "gcp_mount_path" {
  description = "Path where GCP secrets engine is mounted"
  value       = var.enable_gcp_secrets ? vault_mount.gcp[0].path : null
}

output "gcp_roles" {
  description = "GCP roles created"
  value = var.enable_gcp_secrets ? {
    readonly  = vault_gcp_secret_roleset.readonly[0].name
    readwrite = vault_gcp_secret_roleset.readwrite[0].name
  } : {}
}

# Combined secret paths for all environments and engines
output "all_secret_paths" {
  description = "All secret paths organized by environment and engine"
  value = {
    kv = {
      dev = {
        base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/dev"
        common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
      }
      staging = {
        base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/staging"
        common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
      }
      prod = {
        base   = "${var.secrets_mount_path}/data/${var.environment_prefix}/prod"
        common = "${var.secrets_mount_path}/data/${var.environment_prefix}/common"
      }
    }
    database = var.enable_database_secrets ? {
      mount = vault_mount.database[0].path
      roles = {
        readonly  = vault_database_secret_backend_role.readonly[0].name
        readwrite = vault_database_secret_backend_role.readwrite[0].name
      }
    } : {}
    aws = var.enable_aws_secrets ? {
      mount = vault_mount.aws[0].path
      roles = {
        readonly  = vault_aws_secret_backend_role.readonly[0].name
        readwrite = vault_aws_secret_backend_role.readwrite[0].name
      }
    } : {}
    azure = var.enable_azure_secrets ? {
      mount = vault_mount.azure[0].path
      roles = {
        readonly    = vault_azure_secret_backend_role.readonly[0].name
        contributor = vault_azure_secret_backend_role.contributor[0].name
      }
    } : {}
    gcp = var.enable_gcp_secrets ? {
      mount = vault_mount.gcp[0].path
      roles = {
        readonly  = vault_gcp_secret_roleset.readonly[0].name
        readwrite = vault_gcp_secret_roleset.readwrite[0].name
      }
    } : {}
  }
}

