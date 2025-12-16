#!/bin/bash

# ArgoCD Bootstrap Script for KubeSentiment
# This script installs ArgoCD and sets up initial configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Install ArgoCD
install_argocd() {
    log_info "Installing ArgoCD..."

    # Create namespace
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    # Install ArgoCD (use HA version for production)
    log_info "Applying ArgoCD manifests..."
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

    # Wait for ArgoCD to be ready
    log_info "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available --timeout=300s \
        deployment/argocd-server \
        deployment/argocd-repo-server \
        deployment/argocd-applicationset-controller \
        -n argocd

    log_success "ArgoCD installed successfully"
}

# Apply custom configuration
apply_config() {
    log_info "Applying ArgoCD configuration..."

    # Note: Update the ConfigMaps in argocd-config.yaml before applying
    log_warning "Please update GitHub credentials in argocd-config.yaml before applying"
    log_info "Skipping config application for now. Apply manually after updating credentials."

    # Uncomment to apply:
    # kubectl apply -f infrastructure/gitops/argocd/argocd-config.yaml
}

# Create GitHub credentials secret
create_github_secret() {
    log_info "Creating GitHub credentials secret..."

    # Prompt for GitHub credentials
    read -p "Enter GitHub username (or press Enter to skip): " GITHUB_USER

    if [ -z "$GITHUB_USER" ]; then
        log_warning "Skipping GitHub credentials setup"
        return
    fi

    read -sp "Enter GitHub personal access token: " GITHUB_TOKEN
    echo ""

    # Create secret
    kubectl create secret generic github-credentials \
        -n argocd \
        --from-literal=username="$GITHUB_USER" \
        --from-literal=password="$GITHUB_TOKEN" \
        --dry-run=client -o yaml | kubectl apply -f -

    log_success "GitHub credentials secret created"
}

# Get initial admin password
get_admin_password() {
    log_info "Retrieving ArgoCD admin password..."

    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

    echo ""
    log_success "ArgoCD installed and configured!"
    echo ""
    echo "=========================================="
    echo "ArgoCD Access Information"
    echo "=========================================="
    echo ""
    echo "🌐 URL: https://localhost:8080 (after port-forward)"
    echo "👤 Username: admin"
    echo "🔑 Password: $ARGOCD_PASSWORD"
    echo ""
    echo "To access ArgoCD UI, run:"
    echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo ""
    echo "To change the password:"
    echo "  argocd login localhost:8080"
    echo "  argocd account update-password"
    echo ""
    echo "=========================================="
    echo ""
}

# Install ArgoCD CLI (optional)
install_argocd_cli() {
    log_info "Installing ArgoCD CLI..."

    if command -v argocd &> /dev/null; then
        log_warning "ArgoCD CLI already installed"
        argocd version --client
        return
    fi

    # Detect OS
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            log_info "Detected Linux"
            curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
            sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
            rm /tmp/argocd
            ;;
        Darwin*)
            log_info "Detected macOS"
            curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-darwin-amd64
            sudo install -m 555 /tmp/argocd /usr/local/bin/argocd
            rm /tmp/argocd
            ;;
        *)
            log_warning "Unsupported OS: ${OS}. Please install ArgoCD CLI manually."
            log_info "See: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
            return
            ;;
    esac

    log_success "ArgoCD CLI installed"
    argocd version --client
}

# Create ArgoCD Project
create_project() {
    log_info "Creating ArgoCD Project for KubeSentiment..."

    kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: kubesentiment
  namespace: argocd
spec:
  description: KubeSentiment MLOps Sentiment Analysis Project

  # Source repositories
  sourceRepos:
  - '*'  # Allow all repos (restrict this in production)

  # Destination clusters and namespaces
  destinations:
  - namespace: mlops-sentiment-dev
    server: https://kubernetes.default.svc
  - namespace: mlops-sentiment-staging
    server: https://kubernetes.default.svc
  - namespace: mlops-sentiment
    server: https://kubernetes.default.svc
  - namespace: monitoring
    server: https://kubernetes.default.svc

  # Cluster resource whitelist
  clusterResourceWhitelist:
  - group: ''
    kind: Namespace
  - group: 'rbac.authorization.k8s.io'
    kind: ClusterRole
  - group: 'rbac.authorization.k8s.io'
    kind: ClusterRoleBinding

  # Namespace resource whitelist (allow all by default)
  namespaceResourceWhitelist:
  - group: '*'
    kind: '*'

  # Orphaned resources monitoring
  orphanedResources:
    warn: true
EOF

    log_success "ArgoCD Project created"
}

# Bootstrap applications
bootstrap_applications() {
    log_info "Bootstrapping ArgoCD Applications..."

    # Apply application manifests
    kubectl apply -f infrastructure/gitops/applications/development/
    kubectl apply -f infrastructure/gitops/applications/staging/
    kubectl apply -f infrastructure/gitops/applications/production/

    log_success "Applications bootstrapped"
}

# Main execution
main() {
    echo "🚀 ArgoCD Bootstrap for KubeSentiment"
    echo "======================================="
    echo ""

    check_prerequisites
    install_argocd
    install_argocd_cli
    create_github_secret
    create_project
    apply_config
    get_admin_password

    echo ""
    log_info "Next steps:"
    echo "  1. Update GitHub credentials in infrastructure/gitops/argocd/argocd-config.yaml"
    echo "  2. Apply custom configuration: kubectl apply -f infrastructure/gitops/argocd/argocd-config.yaml"
    echo "  3. Bootstrap applications: kubectl apply -f infrastructure/gitops/applications/"
    echo "  4. Access ArgoCD UI and verify applications"
    echo ""
    log_success "🎉 ArgoCD bootstrap completed!"
}

# Handle script arguments
case "${1:-install}" in
    "install")
        main
        ;;
    "uninstall")
        log_warning "Uninstalling ArgoCD..."
        kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
        kubectl delete namespace argocd
        log_success "ArgoCD uninstalled"
        ;;
    "status")
        kubectl get all -n argocd
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status}"
        exit 1
        ;;
esac
