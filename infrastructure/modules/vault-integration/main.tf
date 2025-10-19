/**
 * HashiCorp Vault Integration Module
 *
 * This module configures Vault for MLOps secrets management with:
 * - KV v2 secrets engine for application secrets
 * - Kubernetes authentication method
 * - Environment-specific policies and namespaces
 * - Dynamic secrets engines for databases and cloud providers
 */

terraform {
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = ">= 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.11.0"
    }
  }
}

# Enable KV v2 secrets engine for application secrets
resource "vault_mount" "kv_v2" {
  path        = var.secrets_mount_path
  type        = "kv"
  options     = { version = "2" }
  description = "KV v2 secrets engine for MLOps application secrets"
}

# Enable Kubernetes authentication method
resource "vault_auth_backend" "kubernetes" {
  type        = "kubernetes"
  path        = var.k8s_auth_path
  description = "Kubernetes authentication for MLOps workloads"
}

# Configure Kubernetes auth backend
resource "vault_kubernetes_auth_backend_config" "config" {
  backend            = vault_auth_backend.kubernetes.path
  kubernetes_host    = var.kubernetes_host
  kubernetes_ca_cert = var.kubernetes_ca_cert
  token_reviewer_jwt = var.kubernetes_token_reviewer_jwt
}

# Create policies for each environment
resource "vault_policy" "mlops_dev" {
  name = "mlops-sentiment-dev"

  policy = <<EOT
# Read access to dev secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/dev/*" {
  capabilities = ["read", "list"]
}

# Read access to common secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/common/*" {
  capabilities = ["read", "list"]
}

# List secrets metadata
path "${var.secrets_mount_path}/metadata/${var.environment_prefix}/dev/*" {
  capabilities = ["list"]
}
EOT
}

resource "vault_policy" "mlops_staging" {
  name = "mlops-sentiment-staging"

  policy = <<EOT
# Read access to staging secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/staging/*" {
  capabilities = ["read", "list"]
}

# Read access to common secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/common/*" {
  capabilities = ["read", "list"]
}

# List secrets metadata
path "${var.secrets_mount_path}/metadata/${var.environment_prefix}/staging/*" {
  capabilities = ["list"]
}
EOT
}

resource "vault_policy" "mlops_prod" {
  name = "mlops-sentiment-prod"

  policy = <<EOT
# Read access to prod secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/prod/*" {
  capabilities = ["read", "list"]
}

# Read access to common secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/common/*" {
  capabilities = ["read", "list"]
}

# List secrets metadata
path "${var.secrets_mount_path}/metadata/${var.environment_prefix}/prod/*" {
  capabilities = ["list"]
}
EOT
}

# Create Kubernetes auth roles for each environment
resource "vault_kubernetes_auth_backend_role" "mlops_dev" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mlops-sentiment-dev"
  bound_service_account_names      = [var.service_account_name]
  bound_service_account_namespaces = ["mlops-dev"]
  token_ttl                        = var.token_ttl
  token_max_ttl                    = var.token_max_ttl
  token_policies                   = [vault_policy.mlops_dev.name]
  audience                         = var.k8s_auth_audience
}

resource "vault_kubernetes_auth_backend_role" "mlops_staging" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mlops-sentiment-staging"
  bound_service_account_names      = [var.service_account_name]
  bound_service_account_namespaces = ["mlops-staging"]
  token_ttl                        = var.token_ttl
  token_max_ttl                    = var.token_max_ttl
  token_policies                   = [vault_policy.mlops_staging.name]
  audience                         = var.k8s_auth_audience
}

resource "vault_kubernetes_auth_backend_role" "mlops_prod" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "mlops-sentiment-prod"
  bound_service_account_names      = [var.service_account_name]
  bound_service_account_namespaces = ["mlops-prod"]
  token_ttl                        = var.token_ttl
  token_max_ttl                    = var.token_max_ttl
  token_policies                   = [vault_policy.mlops_prod.name]
  audience                         = var.k8s_auth_audience
}

# Create admin policy for CI/CD and secret rotation
resource "vault_policy" "mlops_admin" {
  name = "mlops-sentiment-admin"

  policy = <<EOT
# Full access to all environment secrets
path "${var.secrets_mount_path}/data/${var.environment_prefix}/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Full access to metadata
path "${var.secrets_mount_path}/metadata/${var.environment_prefix}/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Ability to delete secret versions
path "${var.secrets_mount_path}/delete/${var.environment_prefix}/*" {
  capabilities = ["update"]
}

# Ability to undelete secret versions
path "${var.secrets_mount_path}/undelete/${var.environment_prefix}/*" {
  capabilities = ["update"]
}

# Ability to destroy secret versions permanently
path "${var.secrets_mount_path}/destroy/${var.environment_prefix}/*" {
  capabilities = ["update"]
}
EOT
}

# Create JWT auth method for GitHub Actions
resource "vault_jwt_auth_backend" "github_actions" {
  count               = var.enable_github_actions_auth ? 1 : 0
  path                = "jwt-github"
  description         = "JWT auth for GitHub Actions"
  oidc_discovery_url  = "https://token.actions.githubusercontent.com"
  bound_issuer        = "https://token.actions.githubusercontent.com"
}

resource "vault_jwt_auth_backend_role" "github_actions" {
  count          = var.enable_github_actions_auth ? 1 : 0
  backend        = vault_jwt_auth_backend.github_actions[0].path
  role_name      = "github-actions"
  token_policies = [vault_policy.mlops_admin.name]

  bound_audiences = ["https://github.com/${var.github_org}"]
  bound_claims = {
    repository = var.github_repository
  }

  user_claim            = "actor"
  role_type            = "jwt"
  token_ttl            = 3600
  token_max_ttl        = 3600
}

# Enable audit logging
resource "vault_audit" "file" {
  count = var.enable_audit_logging ? 1 : 0
  type  = "file"

  options = {
    file_path = "/vault/logs/audit.log"
  }
}

# Enable database secrets engine for PostgreSQL
resource "vault_mount" "database" {
  count = var.enable_database_secrets ? 1 : 0
  path  = "database"
  type  = "database"
}

# Configure PostgreSQL database connection
resource "vault_database_secret_backend_connection" "postgresql" {
  count      = var.enable_database_secrets ? 1 : 0
  backend    = vault_mount.database[0].path
  name       = "postgresql"
  plugin_name = "postgresql-database-plugin"

  postgresql {
    connection_url = "postgresql://{{username}}:{{password}}@${var.database_host}:${var.database_port}/${var.database_name}?sslmode=require"
    username       = var.database_username
    password       = var.database_password
    verify_connection = false
  }

  # Allow revocation of credentials
  allowed_roles = ["readonly", "readwrite"]
}

# Create database roles for different access levels
resource "vault_database_secret_backend_role" "readonly" {
  count            = var.enable_database_secrets ? 1 : 0
  backend          = vault_mount.database[0].path
  name             = "readonly"
  db_name          = vault_database_secret_backend_connection.postgresql[0].name
  creation_statements = [
    "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';",
    "GRANT CONNECT ON DATABASE ${var.database_name} TO \"{{name}}\";",
    "GRANT USAGE ON SCHEMA public TO \"{{name}}\";",
    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";",
  ]
  revocation_statements = [
    "DROP ROLE IF EXISTS \"{{name}}\";"
  ]
  default_ttl = 3600  # 1 hour
  max_ttl     = 86400 # 24 hours
}

resource "vault_database_secret_backend_role" "readwrite" {
  count            = var.enable_database_secrets ? 1 : 0
  backend          = vault_mount.database[0].path
  name             = "readwrite"
  db_name          = vault_database_secret_backend_connection.postgresql[0].name
  creation_statements = [
    "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';",
    "GRANT CONNECT ON DATABASE ${var.database_name} TO \"{{name}}\";",
    "GRANT USAGE ON SCHEMA public TO \"{{name}}\";",
    "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{{name}}\";",
    "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";",
  ]
  revocation_statements = [
    "DROP ROLE IF EXISTS \"{{name}}\";"
  ]
  default_ttl = 3600  # 1 hour
  max_ttl     = 86400 # 24 hours
}

# Enable AWS secrets engine for cloud provider authentication
resource "vault_mount" "aws" {
  count = var.enable_aws_secrets ? 1 : 0
  path  = "aws"
  type  = "aws"
}

# Configure AWS access for Vault
resource "vault_aws_secret_backend" "aws" {
  count = var.enable_aws_secrets ? 1 : 0
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  region     = var.aws_region

  # Optional: Assume role for enhanced security
  # assume_role_arn = var.aws_assume_role_arn
}

# Create AWS roles for different permission levels
resource "vault_aws_secret_backend_role" "readonly" {
  count = var.enable_aws_secrets ? 1 : 0
  backend = vault_mount.aws[0].path
  name    = "readonly"

  credential_type = "assumed_role"
  role_arns       = [var.aws_readonly_role_arn]

  default_sts_ttl = 3600  # 1 hour
  max_sts_ttl     = 43200 # 12 hours
}

resource "vault_aws_secret_backend_role" "readwrite" {
  count = var.enable_aws_secrets ? 1 : 0
  backend = vault_mount.aws[0].path
  name    = "readwrite"

  credential_type = "assumed_role"
  role_arns       = [var.aws_readwrite_role_arn]

  default_sts_ttl = 3600  # 1 hour
  max_sts_ttl     = 43200 # 12 hours
}

# Enable Azure secrets engine
resource "vault_mount" "azure" {
  count = var.enable_azure_secrets ? 1 : 0
  path  = "azure"
  type  = "azure"
}

# Configure Azure secrets backend
resource "vault_azure_secret_backend" "azure" {
  count = var.enable_azure_secrets ? 1 : 0
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
  client_id       = var.azure_client_id
  client_secret   = var.azure_client_secret
  environment     = var.azure_environment
}

# Create Azure roles for different access levels
resource "vault_azure_secret_backend_role" "readonly" {
  count = var.enable_azure_secrets ? 1 : 0
  backend = vault_mount.azure[0].path
  name    = "readonly"

  azure_roles {
    role_name = "Reader"
    scope     = var.azure_subscription_id
  }

  default_ttl = 3600  # 1 hour
  max_ttl     = 43200 # 12 hours
}

resource "vault_azure_secret_backend_role" "contributor" {
  count = var.enable_azure_secrets ? 1 : 0
  backend = vault_mount.azure[0].path
  name    = "contributor"

  azure_roles {
    role_name = "Contributor"
    scope     = var.azure_subscription_id
  }

  default_ttl = 3600  # 1 hour
  max_ttl     = 43200 # 12 hours
}

# Enable GCP secrets engine
resource "vault_mount" "gcp" {
  count = var.enable_gcp_secrets ? 1 : 0
  path  = "gcp"
  type  = "gcp"
}

# Configure GCP secrets backend
resource "vault_gcp_secret_backend" "gcp" {
  count = var.enable_gcp_secrets ? 1 : 0
  credentials = var.gcp_service_account_key
  default_lease_ttl_seconds = 3600  # 1 hour
  max_lease_ttl_seconds     = 43200 # 12 hours
}

# Create GCP roles for different access levels
resource "vault_gcp_secret_roleset" "readonly" {
  count = var.enable_gcp_secrets ? 1 : 0
  backend = vault_mount.gcp[0].path
  name    = "readonly"

  project  = var.gcp_project_id
  secret_type = "access_token"

  binding {
    resource = "//cloudresourcemanager.googleapis.com/projects/${var.gcp_project_id}"

    roles = [
      "roles/viewer"
    ]
  }
}

resource "vault_gcp_secret_roleset" "readwrite" {
  count = var.enable_gcp_secrets ? 1 : 0
  backend = vault_mount.gcp[0].path
  name    = "readwrite"

  project  = var.gcp_project_id
  secret_type = "access_token"

  binding {
    resource = "//cloudresourcemanager.googleapis.com/projects/${var.gcp_project_id}"

    roles = [
      "roles/editor"
    ]
  }
}

