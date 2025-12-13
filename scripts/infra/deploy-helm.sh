#!/bin/bash

# MLOps Sentiment Analysis - Helm Deployment Script
# Скрипт для развертывания полного стека мониторинга

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-mlops-sentiment}"
RELEASE_NAME="${RELEASE_NAME:-mlops-sentiment}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
CHART_PATH="./helm/mlops-sentiment"
VALUES_FILE="${VALUES_FILE:-values-${ENVIRONMENT}.yaml}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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
    
    # Check if kubectl is installed and configured
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to Kubernetes cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace ${NAMESPACE}..."
    
    if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_warning "Namespace ${NAMESPACE} already exists"
    else
        kubectl create namespace "${NAMESPACE}"
        kubectl label namespace "${NAMESPACE}" name="${NAMESPACE}"
        log_success "Namespace ${NAMESPACE} created"
    fi
}

# Add Helm repositories
add_helm_repos() {
    log_info "Adding Helm repositories..."
    
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    log_success "Helm repositories added and updated"
}

# Install monitoring namespace and tools
install_monitoring() {
    log_info "Installing monitoring stack..."
    
    # Create monitoring namespace
    if ! kubectl get namespace monitoring &> /dev/null; then
        kubectl create namespace monitoring
        kubectl label namespace monitoring name=monitoring
    fi
    
    # Install Prometheus Operator (if not already installed)
    if ! helm list -n monitoring | grep -q prometheus-operator; then
        log_info "Installing Prometheus Operator..."
        helm install prometheus-operator prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
            --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false \
            --wait
    fi
    
    log_success "Monitoring stack installed"
}

# Deploy the application
deploy_application() {
    log_info "Deploying MLOps Sentiment Analysis application..."
    
    # Check if values file exists
    if [[ -f "${CHART_PATH}/${VALUES_FILE}" ]]; then
        VALUES_ARG="-f ${CHART_PATH}/${VALUES_FILE}"
    else
        log_warning "Values file ${VALUES_FILE} not found, using default values"
        VALUES_ARG=""
    fi
    
    # Deploy with Helm
    helm upgrade --install "${RELEASE_NAME}" "${CHART_PATH}" \
        --namespace "${NAMESPACE}" \
        --create-namespace \
        ${VALUES_ARG} \
        --set image.tag="${IMAGE_TAG:-latest}" \
        --set deployment.env.MLOPS_DEBUG="${DEBUG:-false}" \
        --set deployment.env.MLOPS_LOG_LEVEL="${LOG_LEVEL:-INFO}" \
        --wait \
        --timeout=10m
    
    log_success "Application deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod \
        --selector=app.kubernetes.io/name=mlops-sentiment \
        --namespace="${NAMESPACE}" \
        --timeout=300s
    
    # Check service endpoints
    kubectl get endpoints -n "${NAMESPACE}"
    
    # Check if ServiceMonitor is created
    if kubectl get servicemonitor -n "${NAMESPACE}" "${RELEASE_NAME}" &> /dev/null; then
        log_success "ServiceMonitor created successfully"
    else
        log_warning "ServiceMonitor not found"
    fi
    
    log_success "Deployment verification completed"
}

# Display access information
show_access_info() {
    log_info "Access Information:"
    echo ""
    
    # Application endpoints
    echo "🚀 Application Endpoints:"
    if kubectl get ingress -n "${NAMESPACE}" "${RELEASE_NAME}" &> /dev/null; then
        INGRESS_HOST=$(kubectl get ingress -n "${NAMESPACE}" "${RELEASE_NAME}" -o jsonpath='{.spec.rules[0].host}')
        echo "  • Application: https://${INGRESS_HOST}"
        echo "  • Health Check: https://${INGRESS_HOST}/health"
        echo "  • Metrics: https://${INGRESS_HOST}/metrics"
        echo "  • API Docs: https://${INGRESS_HOST}/docs"
    else
        echo "  • Use port-forward: kubectl port-forward -n ${NAMESPACE} svc/${RELEASE_NAME} 8080:80"
    fi
    
    echo ""
    echo "📊 Monitoring Stack:"
    
    # Grafana access
    if kubectl get svc -n monitoring grafana &> /dev/null; then
        echo "  • Grafana: kubectl port-forward -n monitoring svc/grafana 3000:80"
        echo "    Default credentials: admin/admin123"
    fi
    
    # Prometheus access
    if kubectl get svc -n monitoring prometheus-operated &> /dev/null; then
        echo "  • Prometheus: kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090"
    fi
    
    # Alertmanager access
    if kubectl get svc -n monitoring alertmanager-operated &> /dev/null; then
        echo "  • Alertmanager: kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093"
    fi
    
    echo ""
    echo "🔧 Useful Commands:"
    echo "  • View logs: kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=mlops-sentiment -f"
    echo "  • Scale deployment: kubectl scale deployment -n ${NAMESPACE} ${RELEASE_NAME} --replicas=5"
    echo "  • Update deployment: helm upgrade ${RELEASE_NAME} ${CHART_PATH} -n ${NAMESPACE}"
    echo "  • Uninstall: helm uninstall ${RELEASE_NAME} -n ${NAMESPACE}"
}

# Main execution
main() {
    echo "🚀 MLOps Sentiment Analysis - Helm Deployment"
    echo "=============================================="
    echo ""
    
    check_prerequisites
    create_namespace
    add_helm_repos
    install_monitoring
    deploy_application
    verify_deployment
    show_access_info
    
    echo ""
    log_success "🎉 Deployment completed successfully!"
    echo ""
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "upgrade")
        deploy_application
        verify_deployment
        ;;
    "uninstall")
        log_info "Uninstalling ${RELEASE_NAME}..."
        helm uninstall "${RELEASE_NAME}" -n "${NAMESPACE}"
        log_success "Application uninstalled"
        ;;
    "status")
        helm status "${RELEASE_NAME}" -n "${NAMESPACE}"
        kubectl get all -n "${NAMESPACE}"
        ;;
    *)
        echo "Usage: $0 {deploy|upgrade|uninstall|status}"
        exit 1
        ;;
esac
