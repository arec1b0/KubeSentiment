terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.0.13"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.1"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.11.0"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0"
    }
    vault = {
      source = "hashicorp/vault"
      version = ">= 3.0"
    }
  }
}

# Provider for local Kind cluster
provider "kind" {}

# Provider for Helm (Week 2)
provider "helm" {
  kubernetes {
    config_path = "~/.kube/config" # This will be dynamically set later
  }
}

# Provider for Kubernetes
provider "kubernetes" {
  config_path = "~/.kube/config" # This will be dynamically set later
}

# Placeholder for Google Cloud (GKE)
# provider "google" {
#   project = var.gcp_project
#   region  = var.gcp_region
# }

# Placeholder for AWS (EKS)
# provider "aws" {
#   region = var.aws_region
# }

# Placeholder for Azure (AKS)
# provider "azurerm" {
#   features {}
# }

# Placeholder for Vault (Week 3)
# provider "vault" {
#   address = var.vault_addr
# }
