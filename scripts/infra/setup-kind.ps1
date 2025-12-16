#
# MLOps Sentiment Analysis Service - Kind Setup Script
# This script sets up Kind (Kubernetes in Docker) for local development
#

$ErrorActionPreference = "Stop"

# Configuration
$ClusterName = "mlops-sentiment"
$KindConfigFile = "kind-config.yaml"

Write-Host "MLOps Sentiment Service - Kind Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Check if Kind is installed
if (-not (Get-Command kind -ErrorAction SilentlyContinue)) {
    Write-Host "Kind is not installed" -ForegroundColor Red
    Write-Host "Installing Kind..." -ForegroundColor Yellow
    
    # Install Kind for Windows
    Write-Host "Please install Kind manually from: https://kind.sigs.k8s.io/docs/user/quick-start/#installation" -ForegroundColor Yellow
    Write-Host "For Windows (using Chocolatey): choco install kind" -ForegroundColor Yellow
    Write-Host "For Windows (manual): Download from https://github.com/kubernetes-sigs/kind/releases" -ForegroundColor Yellow
    exit 1
}

$kindVersion = kind version
Write-Host "Kind is installed: $kindVersion" -ForegroundColor Green

# Check if kubectl is installed
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "kubectl is not installed" -ForegroundColor Red
    Write-Host "Please install kubectl from: https://kubernetes.io/docs/tasks/tools/" -ForegroundColor Yellow
    exit 1
}

$kubectlVersion = kubectl version --client --short 2>$null
Write-Host "kubectl is installed: $kubectlVersion" -ForegroundColor Green

# Check if Docker is running
try {
    docker info 2>$null | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop or Docker daemon" -ForegroundColor Yellow
    exit 1
}

# Check if cluster already exists
$existingCluster = kind get clusters 2>$null | Select-String -Pattern "^$ClusterName$"
if ($existingCluster) {
    Write-Host "Kind cluster '$ClusterName' already exists" -ForegroundColor Yellow
    
    $response = Read-Host "Do you want to delete and recreate the cluster? (y/N)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "Deleting existing cluster..." -ForegroundColor Yellow
        kind delete cluster --name $ClusterName
    } else {
        Write-Host "Using existing cluster" -ForegroundColor Blue
        kubectl config use-context "kind-$ClusterName"
        Write-Host "Kind setup completed!" -ForegroundColor Green
        exit 0
    }
}

# Create Kind configuration file
Write-Host "Creating Kind configuration..." -ForegroundColor Blue
@"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $ClusterName
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 30800
    hostPort: 30800
    protocol: TCP
- role: worker
- role: worker
"@ | Out-File -FilePath $KindConfigFile -Encoding UTF8

# Create Kind cluster
Write-Host "Creating Kind cluster..." -ForegroundColor Blue
kind create cluster --config $KindConfigFile --wait 5m

# Configure kubectl context
Write-Host "Configuring kubectl..." -ForegroundColor Blue
kubectl config use-context "kind-$ClusterName"

# Install NGINX Ingress Controller
Write-Host "Installing NGINX Ingress Controller..." -ForegroundColor Blue
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for NGINX Ingress to be ready
Write-Host "Waiting for NGINX Ingress Controller..." -ForegroundColor Yellow
kubectl wait --namespace ingress-nginx `
    --for=condition=ready pod `
    --selector=app.kubernetes.io/component=controller `
    --timeout=90s

# Install metrics server for HPA
Write-Host "Installing metrics server..." -ForegroundColor Blue
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch metrics server for Kind (disable TLS verification)
kubectl patch deployment metrics-server -n kube-system --type='json' `
    -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Wait for metrics server to be ready
Write-Host "Waiting for metrics server..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=60s

# Verify cluster
Write-Host "Verifying cluster..." -ForegroundColor Blue
kubectl cluster-info
kubectl get nodes -o wide

# Show cluster information
Write-Host "Cluster Information:" -ForegroundColor Blue
kubectl get nodes
kubectl get pods -A

# Test cluster functionality
Write-Host "Testing cluster functionality..." -ForegroundColor Blue
kubectl create namespace test-namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl delete namespace test-namespace

# Clean up configuration file
Remove-Item -Path $KindConfigFile -Force

Write-Host "Kind setup completed successfully!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Blue
Write-Host "  - Deploy the service: .\scripts\infra\deploy-helm.ps1" -ForegroundColor Yellow
Write-Host "  - View cluster status: kubectl get nodes" -ForegroundColor Yellow
Write-Host "  - Delete cluster: kind delete cluster --name $ClusterName" -ForegroundColor Yellow

Write-Host ""
Write-Host "Useful Kind commands:" -ForegroundColor Blue
Write-Host "  - List clusters: kind get clusters" -ForegroundColor Yellow
Write-Host "  - Load Docker image: kind load docker-image <image-name> --name $ClusterName" -ForegroundColor Yellow
Write-Host "  - Get kubeconfig: kind get kubeconfig --name $ClusterName" -ForegroundColor Yellow
Write-Host "  - Export logs: kind export logs --name $ClusterName" -ForegroundColor Yellow

Write-Host ""
Write-Host "Service Access:" -ForegroundColor Blue
Write-Host "  - NodePort services will be available on: http://localhost:30800" -ForegroundColor Yellow
Write-Host "  - Ingress services will be available on: http://localhost" -ForegroundColor Yellow
