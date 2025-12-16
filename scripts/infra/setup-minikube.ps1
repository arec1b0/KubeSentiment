#
# MLOps Sentiment Analysis Service - Minikube Setup Script
# This script sets up Minikube for local Kubernetes development
#

$ErrorActionPreference = "Stop"

Write-Host "MLOps Sentiment Service - Minikube Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if Minikube is installed
if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) {
    Write-Host "Minikube is not installed" -ForegroundColor Red
    Write-Host "Please install Minikube from: https://minikube.sigs.k8s.io/docs/start/" -ForegroundColor Yellow
    exit 1
}

$minikubeVersion = minikube version --short 2>$null
Write-Host "Minikube is installed: $minikubeVersion" -ForegroundColor Green

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

# Check if Minikube is already running
try {
    minikube status 2>$null | Out-Null
    $minikubeRunning = $true
} catch {
    $minikubeRunning = $false
}

if ($minikubeRunning) {
    Write-Host "Minikube is already running" -ForegroundColor Yellow
    minikube status
    
    $response = Read-Host "Do you want to restart Minikube? (y/N)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "Stopping Minikube..." -ForegroundColor Yellow
        minikube stop
        
        Write-Host "Deleting existing Minikube cluster..." -ForegroundColor Yellow
        minikube delete
    } else {
        Write-Host "Using existing Minikube cluster" -ForegroundColor Blue
        kubectl config use-context minikube
        Write-Host "Minikube setup completed!" -ForegroundColor Green
        exit 0
    }
}

# Start Minikube with optimized settings for ML workloads
Write-Host "Starting Minikube..." -ForegroundColor Blue
$k8sVersion = "v1.28.3"

minikube start `
    --driver=docker `
    --cpus=4 `
    --memory=8192 `
    --disk-size=20g `
    --kubernetes-version=$k8sVersion `
    --container-runtime=docker `
    --extra-config=kubelet.housekeeping-interval=10s

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Version $k8sVersion failed, trying stable version..."
    minikube start `
        --driver=docker `
        --cpus=4 `
        --memory=8192 `
        --disk-size=20g `
        --kubernetes-version=stable `
        --container-runtime=docker `
        --extra-config=kubelet.housekeeping-interval=10s
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to start Minikube" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Minikube started successfully!" -ForegroundColor Green

# Enable necessary addons
Write-Host "Enabling Minikube addons..." -ForegroundColor Blue

# Enable metrics server for HPA
Write-Host "Enabling metrics-server..." -ForegroundColor Yellow
minikube addons enable metrics-server

# Enable NGINX Ingress Controller
Write-Host "Enabling ingress..." -ForegroundColor Yellow
minikube addons enable ingress

# Enable dashboard (optional)
Write-Host "Enabling dashboard..." -ForegroundColor Yellow
minikube addons enable dashboard

# Wait for addons to be ready
Write-Host "Waiting for addons to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=60s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=60s

# Configure kubectl context
Write-Host "Configuring kubectl..." -ForegroundColor Blue
kubectl config use-context minikube

# Verify cluster
Write-Host "Verifying cluster..." -ForegroundColor Blue
kubectl cluster-info
kubectl get nodes -o wide

# Show cluster information
Write-Host "Cluster Information:" -ForegroundColor Blue
$minikubeIp = minikube ip
Write-Host "Minikube IP: $minikubeIp" -ForegroundColor Green

# Get dashboard URL (non-blocking)
Write-Host "Dashboard URL: Run 'minikube dashboard' to access" -ForegroundColor Green

# Test cluster functionality
Write-Host "Testing cluster functionality..." -ForegroundColor Blue
kubectl create namespace test-namespace --dry-run=client -o yaml | kubectl apply -f -
kubectl delete namespace test-namespace

Write-Host "Minikube setup completed successfully!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Blue
Write-Host "  - Deploy the service: .\scripts\infra\deploy-helm.ps1" -ForegroundColor Yellow
Write-Host "  - Access dashboard: minikube dashboard" -ForegroundColor Yellow
Write-Host "  - View cluster status: minikube status" -ForegroundColor Yellow
Write-Host "  - Stop Minikube: minikube stop" -ForegroundColor Yellow
Write-Host "  - Delete cluster: minikube delete" -ForegroundColor Yellow

Write-Host ""
Write-Host "Useful Minikube commands:" -ForegroundColor Blue
Write-Host "  - Get Minikube IP: minikube ip" -ForegroundColor Yellow
Write-Host "  - SSH into node: minikube ssh" -ForegroundColor Yellow
Write-Host "  - Load Docker image: minikube image load <image-name>" -ForegroundColor Yellow
Write-Host "  - Service URL: minikube service <service-name> --url" -ForegroundColor Yellow
