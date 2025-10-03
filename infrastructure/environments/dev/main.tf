terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "kind" {
  # This provider is configured in the root providers.tf file
}

module "kind_cluster" {
  source = "../modules/kind-cluster"

  cluster_name = "mlops-dev-cluster"
}

output "kubeconfig" {
  value = module.kind_cluster.kubeconfig
}
