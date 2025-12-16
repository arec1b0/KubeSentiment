#
# MLOps Sentiment Analysis - Helm Deployment Script
# Скрипт для развертывания полного стека мониторинга
#

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('deploy', 'upgrade', 'uninstall', 'status')]
    [string]$Action = 'deploy'
)

$ErrorActionPreference = "Stop"

# Configuration
$Namespace = if ($env:NAMESPACE) { $env:NAMESPACE } else { "mlops-sentiment" }
$ReleaseName = if ($env:RELEASE_NAME) { $env:RELEASE_NAME } else { "mlops-sentiment" }
$Environment = if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { "dev" }
$ChartPath = ".\helm\mlops-sentiment"
$ValuesFile = if ($env:VALUES_FILE) { $env:VALUES_FILE } else { "values-${Environment}.yaml" }

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check if kubectl is installed and configured
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        Write-Error "kubectl is not installed or not in PATH"
        exit 1
    }
    
    # Check if helm is installed
    if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
        Write-Error "helm is not installed or not in PATH"
        exit 1
    }
    
    # Check if we can connect to Kubernetes cluster
    try {
        kubectl cluster-info 2>$null | Out-Null
    } catch {
        Write-Error "Cannot connect to Kubernetes cluster"
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Create namespace if it doesn't exist
function New-K8sNamespace {
    Write-Info "Creating namespace $Namespace..."
    
    $namespaceExists = kubectl get namespace $Namespace 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Warning "Namespace $Namespace already exists"
    } else {
        kubectl create namespace $Namespace
        kubectl label namespace $Namespace name=$Namespace
        Write-Success "Namespace $Namespace created"
    }
}

# Add Helm repositories
function Add-HelmRepos {
    Write-Info "Adding Helm repositories..."
    
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    Write-Success "Helm repositories added and updated"
}

# Install monitoring namespace and tools
function Install-Monitoring {
    Write-Info "Installing monitoring stack..."
    
    # Create monitoring namespace
    $monitoringExists = kubectl get namespace monitoring 2>$null
    if ($LASTEXITCODE -ne 0) {
        kubectl create namespace monitoring
        kubectl label namespace monitoring name=monitoring
    }
    
    # Install Prometheus Operator (if not already installed)
    $prometheusInstalled = helm list -n monitoring 2>$null | Select-String -Pattern "prometheus-operator"
    if (-not $prometheusInstalled) {
        Write-Info "Installing Prometheus Operator..."
        helm install prometheus-operator prometheus-community/kube-prometheus-stack `
            --namespace monitoring `
            --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false `
            --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false `
            --wait
    }
    
    Write-Success "Monitoring stack installed"
}

# Deploy the application
function Deploy-Application {
    Write-Info "Deploying MLOps Sentiment Analysis application..."
    
    # Build helm command
    $imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
    $debug = if ($env:DEBUG) { $env:DEBUG } else { "false" }
    $logLevel = if ($env:LOG_LEVEL) { $env:LOG_LEVEL } else { "INFO" }
    
    $helmArgs = @(
        "upgrade", "--install", $ReleaseName, $ChartPath,
        "--namespace", $Namespace,
        "--create-namespace",
        "--set", "image.tag=$imageTag",
        "--set", "deployment.env.MLOPS_DEBUG=$debug",
        "--set", "deployment.env.MLOPS_LOG_LEVEL=$logLevel",
        "--wait",
        "--timeout=10m"
    )
    
    # Add values file if it exists
    if (Test-Path "$ChartPath\$ValuesFile") {
        $helmArgs += "-f", "$ChartPath\$ValuesFile"
    } else {
        Write-Warning "Values file $ValuesFile not found, using default values"
    }
    
    & helm @helmArgs
    
    Write-Success "Application deployed successfully"
}

# Verify deployment
function Test-Deployment {
    Write-Info "Verifying deployment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod `
        --selector=app.kubernetes.io/name=mlops-sentiment `
        --namespace=$Namespace `
        --timeout=300s
    
    # Check service endpoints
    kubectl get endpoints -n $Namespace
    
    # Check if ServiceMonitor is created
    $serviceMonitorExists = kubectl get servicemonitor -n $Namespace $ReleaseName 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ServiceMonitor created successfully"
    } else {
        Write-Warning "ServiceMonitor not found"
    }
    
    Write-Success "Deployment verification completed"
}

# Display access information
function Show-AccessInfo {
    Write-Info "Access Information:"
    Write-Host ""
    
    # Application endpoints
    Write-Host "Application Endpoints:" -ForegroundColor Cyan
    $ingressExists = kubectl get ingress -n $Namespace $ReleaseName 2>$null
    if ($LASTEXITCODE -eq 0) {
        $ingressHost = kubectl get ingress -n $Namespace $ReleaseName -o jsonpath='{.spec.rules[0].host}'
        Write-Host "  - Application: https://$ingressHost"
        Write-Host "  - Health Check: https://$ingressHost/health"
        Write-Host "  - Metrics: https://$ingressHost/metrics"
        Write-Host "  - API Docs: https://$ingressHost/docs"
    } else {
        Write-Host "  - Use port-forward: kubectl port-forward -n $Namespace svc/$ReleaseName 8080:80"
    }
    
    Write-Host ""
    Write-Host "Monitoring Stack:" -ForegroundColor Cyan
    
    # Grafana access
    $grafanaExists = kubectl get svc -n monitoring grafana 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  - Grafana: kubectl port-forward -n monitoring svc/grafana 3000:80"
        Write-Host "    Default credentials: admin/admin123"
    }
    
    # Prometheus access
    $prometheusExists = kubectl get svc -n monitoring prometheus-operated 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  - Prometheus: kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090"
    }
    
    # Alertmanager access
    $alertmanagerExists = kubectl get svc -n monitoring alertmanager-operated 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  - Alertmanager: kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093"
    }
    
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Cyan
    Write-Host "  - View logs: kubectl logs -n $Namespace -l app.kubernetes.io/name=mlops-sentiment -f"
    Write-Host "  - Scale deployment: kubectl scale deployment -n $Namespace $ReleaseName --replicas=5"
    Write-Host "  - Update deployment: helm upgrade $ReleaseName $ChartPath -n $Namespace"
    Write-Host "  - Uninstall: helm uninstall $ReleaseName -n $Namespace"
}

# Main execution
function Start-Deployment {
    Write-Host "MLOps Sentiment Analysis - Helm Deployment" -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""
    
    Test-Prerequisites
    New-K8sNamespace
    Add-HelmRepos
    Install-Monitoring
    Deploy-Application
    Test-Deployment
    Show-AccessInfo
    
    Write-Host ""
    Write-Success "Deployment completed successfully!"
    Write-Host ""
}

# Handle script actions
switch ($Action) {
    "deploy" {
        Start-Deployment
    }
    "upgrade" {
        Deploy-Application
        Test-Deployment
    }
    "uninstall" {
        Write-Info "Uninstalling $ReleaseName..."
        helm uninstall $ReleaseName -n $Namespace
        Write-Success "Application uninstalled"
    }
    "status" {
        helm status $ReleaseName -n $Namespace
        kubectl get all -n $Namespace
    }
}
