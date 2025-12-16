#!/bin/bash

# ArgoCD Health Check Script
# Verifies ArgoCD is running and applications are healthy

set -euo pipefail

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

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    exit 1
fi

# Check if argocd CLI is available
if ! command -v argocd &> /dev/null; then
    log_warning "argocd CLI is not installed. Install it for full functionality."
    log_info "See: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    ARGOCD_CLI=false
else
    ARGOCD_CLI=true
fi

echo ""
log_info "🔍 ArgoCD Health Check"
echo "========================================"
echo ""

# Check ArgoCD namespace
log_info "Checking ArgoCD namespace..."
if kubectl get namespace argocd &> /dev/null; then
    log_success "ArgoCD namespace exists"
else
    log_error "ArgoCD namespace not found. Is ArgoCD installed?"
    exit 1
fi

# Check ArgoCD pods
log_info "Checking ArgoCD pods..."
echo ""
kubectl get pods -n argocd
echo ""

# Check if pods are running
RUNNING_PODS=$(kubectl get pods -n argocd --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
TOTAL_PODS=$(kubectl get pods -n argocd --no-headers 2>/dev/null | wc -l)

if [ "$RUNNING_PODS" -eq "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
    log_success "All ArgoCD pods are running ($RUNNING_PODS/$TOTAL_PODS)"
else
    log_warning "Not all ArgoCD pods are running ($RUNNING_PODS/$TOTAL_PODS)"
fi

# Check ArgoCD service
log_info "Checking ArgoCD service..."
if kubectl get svc argocd-server -n argocd &> /dev/null; then
    log_success "ArgoCD server service exists"
else
    log_error "ArgoCD server service not found"
fi

# Check ArgoCD applications
log_info "Checking ArgoCD applications..."
echo ""

if [ "$ARGOCD_CLI" = true ]; then
    # Try to list applications
    if kubectl get applications -n argocd &> /dev/null; then
        kubectl get applications -n argocd
        echo ""

        # Check each environment
        for env in development staging production; do
            APP_NAME="mlops-sentiment-$env"
            if kubectl get application "$APP_NAME" -n argocd &> /dev/null; then
                HEALTH=$(kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.status.health.status}')
                SYNC=$(kubectl get application "$APP_NAME" -n argocd -o jsonpath='{.status.sync.status}')

                if [ "$HEALTH" = "Healthy" ]; then
                    log_success "$APP_NAME: Health=$HEALTH, Sync=$SYNC"
                else
                    log_warning "$APP_NAME: Health=$HEALTH, Sync=$SYNC"
                fi
            else
                log_warning "$APP_NAME: Not found"
            fi
        done
    else
        log_warning "No ArgoCD applications found"
    fi
else
    kubectl get applications -n argocd 2>/dev/null || log_warning "No applications found"
fi

echo ""
log_info "🔗 Access Information"
echo "========================================"
echo ""

# Get ArgoCD server endpoint
SERVER_TYPE=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.type}')
echo "Service Type: $SERVER_TYPE"

if [ "$SERVER_TYPE" = "LoadBalancer" ]; then
    EXTERNAL_IP=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -n "$EXTERNAL_IP" ]; then
        echo "External IP: $EXTERNAL_IP"
        echo "URL: https://$EXTERNAL_IP"
    fi
elif [ "$SERVER_TYPE" = "NodePort" ]; then
    NODE_PORT=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')
    echo "Node Port: $NODE_PORT"
    echo "URL: https://<node-ip>:$NODE_PORT"
fi

echo ""
echo "Port Forward Command:"
echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo ""
echo "Access:"
echo "  URL: https://localhost:8080"
echo "  Username: admin"
echo ""
echo "Get Password:"
echo "  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d"
echo ""

if [ "$ARGOCD_CLI" = true ]; then
    echo "Login with CLI:"
    echo "  argocd login localhost:8080"
    echo ""
fi

echo "========================================"
log_success "✅ Health check complete!"
echo ""
