# ADR 008: Use Terraform for Multi-Cloud Infrastructure as Code

**Status:** Accepted
**Date:** 2024-03-10
**Authors:** KubeSentiment Team

## Context

KubeSentiment requires deployment across multiple environments and cloud providers. Managing infrastructure manually leads to several challenges:

1. **Inconsistency**: Manual configuration leads to environment drift
2. **Repeatability**: Difficult to recreate infrastructure reliably
3. **Multi-cloud**: Need to support AWS, GCP, Azure, and on-premises Kubernetes
4. **Collaboration**: Hard to review and approve infrastructure changes
5. **Documentation**: Infrastructure configuration not version-controlled
6. **Disaster recovery**: Slow to rebuild infrastructure after failures

Key requirements:
- Multi-cloud support (AWS EKS, GCP GKE, Azure AKS)
- Local development support (Kind/Minikube)
- Version-controlled infrastructure
- Reusable modules for common patterns
- Integration with Helm for application deployment
- State management for team collaboration
- Cost estimation before deployment

## Decision

We will use **Terraform** as the Infrastructure as Code (IaC) tool for provisioning and managing infrastructure across all cloud providers and environments.

### Implementation Strategy

1. **Directory Structure**:
   ```
   infrastructure/
   ├── providers.tf           # Provider configurations
   ├── variables.tf           # Input variables
   ├── outputs.tf             # Output values
   ├── versions.tf            # Version constraints
   ├── modules/
   │   ├── kind/              # Local Kind cluster
   │   ├── gke/               # Google Kubernetes Engine
   │   ├── eks/               # Amazon Elastic Kubernetes Service
   │   ├── aks/               # Azure Kubernetes Service
   │   └── helm-release/      # Helm chart deployment
   └── environments/
       ├── dev/               # Development environment
       ├── staging/           # Staging environment
       └── production/        # Production environment
   ```

2. **Module Design**:
   - Reusable modules for each cloud provider
   - Standardized inputs/outputs across modules
   - Environment-specific variable files
   - Shared networking and security configurations

3. **State Management**:
   - Remote state storage (S3, GCS, Azure Blob)
   - State locking with DynamoDB/Cloud Storage
   - Separate state files per environment
   - Encrypted state storage

4. **Deployment Workflow**:
   - `terraform plan` for change preview
   - Pull request review for infrastructure changes
   - `terraform apply` in CI/CD pipeline
   - Automated validation and compliance checks

## Consequences

### Positive

- **Multi-cloud support**: Single tool for AWS, GCP, Azure, and on-premises
- **Version control**: Infrastructure changes tracked in Git
- **Reproducibility**: Identical environments every deployment
- **Collaboration**: Team can review infrastructure changes via PRs
- **Modularity**: Reusable modules reduce code duplication
- **Documentation**: Code serves as living documentation
- **Safety**: Plan step prevents accidental changes
- **Cost estimation**: Infracost integration for cost preview
- **Declarative**: Specify desired state, Terraform handles implementation

### Negative

- **State management**: Remote state adds complexity
- **Learning curve**: HCL (HashiCorp Configuration Language) syntax to learn
- **Provider limitations**: Some features lag behind cloud providers
- **Breaking changes**: Major version upgrades can be disruptive
- **Debugging**: Error messages can be cryptic
- **State drift**: Manual changes outside Terraform cause inconsistencies
- **Plan time**: Large infrastructures take time to plan

### Neutral

- **Imperative vs. Declarative**: Different mindset from scripting
- **Community modules**: Quality varies, need evaluation
- **Cloud provider choice**: No vendor lock-in (positive) but no deep integration (neutral)

## Alternatives Considered

### Alternative 1: Cloud-Specific IaC (CloudFormation, Deployment Manager, ARM Templates)

**Pros:**
- Native integration with cloud provider
- First-class support for new features
- No additional tools needed
- Better error messages

**Cons:**
- Different tool per cloud provider
- No multi-cloud story
- Limited local development support
- Smaller community

**Rejected because**: Multi-cloud strategy requires unified IaC tool.

### Alternative 2: Pulumi

**Pros:**
- Use familiar programming languages (Python, TypeScript)
- Strong type safety
- Better testability
- Modern architecture

**Cons:**
- Smaller community than Terraform
- Less mature ecosystem
- Fewer pre-built modules
- Steeper learning curve for ops teams
- Commercial product (OSS version limited)

**Rejected because**: Terraform has larger community, more modules, and better multi-cloud support.

### Alternative 3: Ansible

**Pros:**
- Agentless architecture
- Simple YAML syntax
- Good for configuration management
- Large ecosystem

**Cons:**
- Imperative rather than declarative
- Slower for infrastructure provisioning
- No native state management
- Not designed for cloud infrastructure

**Rejected because**: Ansible better for configuration management than infrastructure provisioning.

### Alternative 4: Kubernetes Operators (Crossplane)

**Pros:**
- Kubernetes-native
- GitOps-friendly
- Declarative API
- Works with ArgoCD/Flux

**Cons:**
- Requires existing Kubernetes cluster
- Chicken-and-egg problem (need K8s to create K8s)
- Less mature than Terraform
- Fewer providers

**Rejected because**: Need to provision Kubernetes clusters themselves; Crossplane requires existing K8s.

### Alternative 5: Manual Configuration

**Pros:**
- No additional tools
- Direct cloud console access
- Immediate feedback

**Cons:**
- Not reproducible
- No version control
- Error-prone
- Slow disaster recovery
- Environment drift

**Rejected because**: Fails all requirements for production infrastructure management.

## Implementation Details

### Multi-Cloud Provider Configuration

```hcl
# infrastructure/providers.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  backend "gcs" {
    bucket = "kubesentiment-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "aws" {
  region = var.aws_region
}

provider "azurerm" {
  features {}
}
```

### GKE Module Example

```hcl
# infrastructure/modules/gke/main.tf
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  # We can't create a cluster with no node pool, so we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable network policy
  network_policy {
    enabled = true
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.node_count

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  node_config {
    machine_type = var.machine_type

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      env     = var.environment
      project = var.project_name
    }

    tags = ["kubesentiment", var.environment]
  }
}
```

### Helm Release Module

```hcl
# infrastructure/modules/helm-release/main.tf
resource "helm_release" "kubesentiment" {
  name       = var.release_name
  namespace  = var.namespace
  repository = var.chart_repository
  chart      = var.chart_name
  version    = var.chart_version

  create_namespace = true

  values = [
    file("${path.module}/values/${var.environment}.yaml")
  ]

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set_sensitive {
    name  = "redis.password"
    value = var.redis_password
  }

  depends_on = [
    var.cluster_ready
  ]
}
```

### Environment-Specific Configuration

```hcl
# infrastructure/environments/production/main.tf
module "gke" {
  source = "../../modules/gke"

  cluster_name  = "kubesentiment-prod"
  project_id    = var.gcp_project_id
  region        = "us-central1"
  environment   = "production"

  node_count     = 3
  min_node_count = 3
  max_node_count = 10
  machine_type   = "n2-standard-4"
}

module "kubesentiment" {
  source = "../../modules/helm-release"

  release_name      = "kubesentiment"
  namespace         = "kubesentiment"
  chart_name        = "mlops-sentiment"
  chart_repository  = "../../helm"
  chart_version     = "1.0.0"
  environment       = "production"
  image_tag         = var.image_tag

  redis_password    = var.redis_password
  cluster_ready     = module.gke.cluster_ready

  depends_on = [module.gke]
}
```

### State Management

```hcl
# infrastructure/backend.tf
terraform {
  backend "gcs" {
    bucket  = "kubesentiment-terraform-state"
    prefix  = "prod/state"

    # Enable encryption
    encryption_key = var.kms_key_name
  }
}

# State locking is automatic with GCS backend
# For S3, add DynamoDB table:
# dynamodb_table = "terraform-lock-table"
```

## Workflow

### Development Workflow

```bash
# 1. Initialize Terraform
terraform init

# 2. Select workspace
terraform workspace select dev

# 3. Plan changes
terraform plan -var-file=environments/dev/terraform.tfvars -out=tfplan

# 4. Review plan
terraform show tfplan

# 5. Apply changes
terraform apply tfplan

# 6. Verify deployment
kubectl get pods -n kubesentiment
```

### CI/CD Integration

```yaml
# .gitlab-ci.yml
terraform-plan:
  stage: plan
  script:
    - cd infrastructure
    - terraform init
    - terraform plan -var-file=environments/${ENV}/terraform.tfvars -out=tfplan
    - terraform show -json tfplan > plan.json
    - infracost breakdown --path plan.json
  artifacts:
    paths:
      - infrastructure/tfplan
      - infrastructure/plan.json

terraform-apply:
  stage: apply
  script:
    - cd infrastructure
    - terraform init
    - terraform apply -auto-approve tfplan
  when: manual
  only:
    - main
```

## Module Catalog

| Module | Purpose | Providers |
|--------|---------|-----------|
| `kind` | Local Kubernetes cluster | Kind |
| `gke` | Google Kubernetes Engine | GCP |
| `eks` | Amazon EKS | AWS |
| `aks` | Azure Kubernetes Service | Azure |
| `helm-release` | Deploy Helm charts | Helm, Kubernetes |
| `monitoring` | Prometheus, Grafana stack | Helm |
| `networking` | VPC, subnets, firewall | AWS, GCP, Azure |

## Cost Management

### Infracost Integration

```bash
# Generate cost estimate
infracost breakdown --path infrastructure/

# Example output:
# ┌─────────────────────────────────────────────────────────────┐
# │ Project: KubeSentiment Production                            │
# ├─────────────────────────────────────────────────────────────┤
# │ google_container_cluster.primary                             │
# │  └─ Cluster management fee              $73.00/mo           │
# │                                                               │
# │ google_container_node_pool.primary_nodes                     │
# │  └─ Instance usage (n2-standard-4)     $486.40/mo           │
# │                                                               │
# │ Total                                  $559.40/mo           │
# └─────────────────────────────────────────────────────────────┘
```

## Security Best Practices

1. **State Encryption**: Enable encryption for state storage
2. **Secret Management**: Use Vault for sensitive values, never commit secrets
3. **Least Privilege**: Service accounts with minimal permissions
4. **Network Isolation**: Private clusters, network policies
5. **Audit Logging**: Enable cloud provider audit logs
6. **Compliance Scanning**: Terraform Sentinel or Checkov

### Security Scanning

```bash
# Run Checkov for security scanning
checkov -d infrastructure/

# Run TFSec for Terraform security
tfsec infrastructure/
```

## Operational Considerations

### State Management

- **Remote State**: S3 (AWS), GCS (GCP), Azure Blob (Azure)
- **State Locking**: DynamoDB (AWS), Cloud Storage (GCP), Azure Blob (Azure)
- **Backup**: Automatic versioning enabled on state storage
- **Access Control**: IAM policies for state access

### Disaster Recovery

1. **Infrastructure Recreation**: `terraform apply` rebuilds entire infrastructure
2. **State Recovery**: Versioned state storage allows rollback
3. **RTO**: < 30 minutes for full infrastructure recovery
4. **RPO**: Near-zero (state synchronized after each apply)

### Change Management

1. **Pull Requests**: All changes reviewed before merge
2. **Plan Review**: `terraform plan` output reviewed
3. **Cost Review**: Infracost report reviewed
4. **Security Review**: Checkov scan must pass
5. **Approval**: Two approvals required for production

## Migration Path

1. **Phase 1** (Complete): Terraform modules for local development (Kind)
2. **Phase 2** (Complete): GKE module for GCP deployment
3. **Phase 3** (Complete): Remote state configuration
4. **Phase 4** (In Progress): EKS and AKS modules
5. **Phase 5** (Planned): Import existing infrastructure to Terraform
6. **Phase 6** (Planned): Terraform Cloud for collaboration

## Performance Metrics

| Environment | Resources | Plan Time | Apply Time |
|-------------|-----------|-----------|------------|
| Development (Kind) | 5 resources | 5s | 30s |
| Staging (GKE) | 25 resources | 15s | 5m |
| Production (GKE) | 50 resources | 30s | 10m |

## Validation

### Testing Strategy

- **Unit tests**: Terratest for module testing
- **Integration tests**: Deploy to ephemeral environments
- **Compliance tests**: Policy-as-Code with Sentinel
- **Cost tests**: Validate costs within budget

### Terratest Example

```go
// infrastructure/test/gke_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestGKEModule(t *testing.T) {
    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/gke",
        Vars: map[string]interface{}{
            "cluster_name": "test-cluster",
            "project_id":   "test-project",
        },
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    clusterName := terraform.Output(t, terraformOptions, "cluster_name")
    assert.Equal(t, "test-cluster", clusterName)
}
```

## References

- [Terraform Documentation](https://www.terraform.io/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Infrastructure Modules](../../infrastructure/modules/)
- [Provider Configurations](../../infrastructure/providers.tf)
- [Terratest Documentation](https://terratest.gruntwork.io/)
- [Infracost Documentation](https://www.infracost.io/docs/)

## Related ADRs

- [ADR 005: Use Helm for Kubernetes Deployments](005-use-helm-for-kubernetes-deployments.md) - Terraform deploys Helm releases
- [ADR 006: Use HashiCorp Vault for Secrets Management](006-use-hashicorp-vault-for-secrets.md) - Vault deployed via Terraform
- [ADR 007: Implement Three Pillars of Observability](007-three-pillars-of-observability.md) - Monitoring stack deployed via Terraform

## Change History

- 2024-03-10: Initial decision
- 2024-03-25: Kind and GKE modules implemented
- 2024-04-10: Remote state configuration complete
- 2024-05-01: EKS and AKS modules added
- 2025-11-18: Added to ADR repository
