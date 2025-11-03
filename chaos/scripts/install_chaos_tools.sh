#!/bin/bash
#
# Install Chaos Engineering Tools
# Installs Chaos Mesh, Litmus, and required dependencies
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
INSTALL_CHAOS_MESH="${INSTALL_CHAOS_MESH:-true}"
INSTALL_LITMUS="${INSTALL_LITMUS:-true}"
INSTALL_ARGO="${INSTALL_ARGO:-true}"
CHAOS_MESH_VERSION="${CHAOS_MESH_VERSION:-2.6.0}"
LITMUS_VERSION="${LITMUS_VERSION:-3.0.0}"

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        log_warning "helm not found, will use kubectl for installation"
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

install_chaos_mesh() {
    log_info "Installing Chaos Mesh..."

    if kubectl get namespace chaos-mesh &> /dev/null; then
        log_warning "chaos-mesh namespace already exists"
    else
        kubectl create namespace chaos-mesh
    fi

    if command -v helm &> /dev/null; then
        log_info "Installing Chaos Mesh via Helm..."
        helm repo add chaos-mesh https://charts.chaos-mesh.org
        helm repo update

        helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
            --namespace=chaos-mesh \
            --version=${CHAOS_MESH_VERSION} \
            --set chaosDaemon.runtime=containerd \
            --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
            --set dashboard.create=true \
            --set dashboard.securityMode=false \
            --wait \
            --timeout=10m

        log_success "Chaos Mesh installed via Helm"
    else
        log_info "Installing Chaos Mesh via kubectl..."
        curl -sSL https://mirrors.chaos-mesh.org/v${CHAOS_MESH_VERSION}/install.sh | bash -s -- --local kind
        log_success "Chaos Mesh installed via kubectl"
    fi

    # Wait for pods to be ready
    log_info "Waiting for Chaos Mesh pods to be ready..."
    kubectl wait --for=condition=Ready pods --all -n chaos-mesh --timeout=5m

    # Verify installation
    log_info "Verifying Chaos Mesh installation..."
    kubectl get pods -n chaos-mesh

    log_success "Chaos Mesh installation complete"
}

install_litmus() {
    log_info "Installing Litmus..."

    if kubectl get namespace litmus &> /dev/null; then
        log_warning "litmus namespace already exists"
    else
        kubectl create namespace litmus
    fi

    log_info "Installing Litmus Operator..."
    kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v${LITMUS_VERSION}.yaml

    log_info "Waiting for Litmus operator to be ready..."
    kubectl wait --for=condition=Ready pods --all -n litmus --timeout=5m || true

    # Install generic experiments
    log_info "Installing Litmus generic experiments..."
    kubectl apply -f https://hub.litmuschaos.io/api/chaos/master?file=charts/generic/experiments.yaml

    # Create service account for Litmus
    log_info "Creating Litmus service accounts..."
    kubectl create sa litmus-admin -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding litmus-admin \
        --clusterrole=cluster-admin \
        --serviceaccount=default:litmus-admin \
        --dry-run=client -o yaml | kubectl apply -f -

    log_success "Litmus installation complete"
}

install_argo_workflows() {
    log_info "Installing Argo Workflows..."

    if kubectl get namespace argo &> /dev/null; then
        log_warning "argo namespace already exists"
    else
        kubectl create namespace argo
    fi

    log_info "Installing Argo Workflows..."
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/latest/download/install.yaml

    log_info "Waiting for Argo pods to be ready..."
    kubectl wait --for=condition=Ready pods --all -n argo --timeout=5m || true

    # Create service account for Argo chaos
    log_info "Creating Argo service accounts..."
    kubectl create sa argo-chaos -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding argo-chaos \
        --clusterrole=cluster-admin \
        --serviceaccount=default:argo-chaos \
        --dry-run=client -o yaml | kubectl apply -f -

    log_success "Argo Workflows installation complete"
}

verify_installation() {
    log_info "Verifying installations..."

    echo ""
    if [ "$INSTALL_CHAOS_MESH" == "true" ]; then
        log_info "Chaos Mesh status:"
        kubectl get pods -n chaos-mesh
        echo ""

        if kubectl get crd podchaos.chaos-mesh.org &> /dev/null; then
            log_success "✓ Chaos Mesh CRDs installed"
        else
            log_error "✗ Chaos Mesh CRDs not found"
        fi
    fi

    if [ "$INSTALL_LITMUS" == "true" ]; then
        log_info "Litmus status:"
        kubectl get pods -n litmus
        echo ""

        if kubectl get crd chaosengines.litmuschaos.io &> /dev/null; then
            log_success "✓ Litmus CRDs installed"
        else
            log_error "✗ Litmus CRDs not found"
        fi
    fi

    if [ "$INSTALL_ARGO" == "true" ]; then
        log_info "Argo Workflows status:"
        kubectl get pods -n argo
        echo ""
    fi
}

show_next_steps() {
    cat <<EOF

========================================
Installation Complete!
========================================

Next Steps:

1. Access Chaos Mesh Dashboard (if installed):
   kubectl port-forward -n chaos-mesh svc/chaos-dashboard 2333:2333
   Open http://localhost:2333

2. Run a chaos experiment:
   cd chaos/scripts
   ./run_chaos_experiment.sh pod-kill 300

3. Check chaos documentation:
   cat chaos/README.md

4. View available experiments:
   ls -la chaos/chaos-mesh/
   ls -la chaos/litmus/

Installed Components:
EOF

    if [ "$INSTALL_CHAOS_MESH" == "true" ]; then
        echo "  ✓ Chaos Mesh (namespace: chaos-mesh)"
    fi
    if [ "$INSTALL_LITMUS" == "true" ]; then
        echo "  ✓ Litmus (namespace: litmus)"
    fi
    if [ "$INSTALL_ARGO" == "true" ]; then
        echo "  ✓ Argo Workflows (namespace: argo)"
    fi

    echo ""
    echo "========================================="
}

main() {
    echo ""
    log_info "=========================================="
    log_info "Chaos Engineering Tools Installation"
    log_info "=========================================="
    echo ""

    check_prerequisites

    if [ "$INSTALL_CHAOS_MESH" == "true" ]; then
        install_chaos_mesh
        echo ""
    fi

    if [ "$INSTALL_LITMUS" == "true" ]; then
        install_litmus
        echo ""
    fi

    if [ "$INSTALL_ARGO" == "true" ]; then
        install_argo_workflows
        echo ""
    fi

    verify_installation
    show_next_steps
}

main "$@"
