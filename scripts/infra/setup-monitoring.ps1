#
# MLOps Monitoring Setup Script
# Полная настройка системы мониторинга с нуля
#

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('setup', 'cleanup', 'status', 'test')]
    [string]$Action = 'setup'
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$MonitoringNamespace = "monitoring"
$AppNamespace = "mlops-sentiment"

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

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Magenta
}

# Banner
function Show-Banner {
    Write-Host @"

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    🚀 MLOps Sentiment Analysis - Monitoring Setup 📊        ║
║                                                              ║
║    Полная настройка системы мониторинга:                     ║
║    • Prometheus + Alertmanager                               ║
║    • Grafana с дашбордами                                    ║
║    • NetworkPolicy для безопасности                         ║
║    • Helm упаковка                                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Magenta
}

# Check prerequisites
function Test-Prerequisites {
    Write-Step "Проверка предварительных требований..."
    
    $missingTools = @()
    
    # Check kubectl
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        $missingTools += "kubectl"
    }
    
    # Check helm
    if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
        $missingTools += "helm"
    }
    
    # Check yq (for YAML processing)
    if (-not (Get-Command yq -ErrorAction SilentlyContinue)) {
        Write-Warning "yq не найден, некоторые функции могут быть недоступны"
    }
    
    if ($missingTools.Count -gt 0) {
        Write-ErrorMsg "Отсутствуют необходимые инструменты: $($missingTools -join ', ')"
        Write-Info "Установите их и повторите попытку:"
        Write-Host "  kubectl: https://kubernetes.io/docs/tasks/tools/"
        Write-Host "  helm: https://helm.sh/docs/intro/install/"
        exit 1
    }
    
    # Check cluster connection
    try {
        kubectl cluster-info 2>$null | Out-Null
    } catch {
        Write-ErrorMsg "Не удается подключиться к кластеру Kubernetes"
        Write-Info "Убедитесь, что kubectl настроен правильно"
        exit 1
    }
    
    Write-Success "Все предварительные требования выполнены"
}

# Setup namespaces
function Initialize-Namespaces {
    Write-Step "Настройка пространств имен..."
    
    # Create monitoring namespace
    $monitoringExists = kubectl get namespace $MonitoringNamespace 2>$null
    if ($LASTEXITCODE -ne 0) {
        kubectl create namespace $MonitoringNamespace
        kubectl label namespace $MonitoringNamespace name=$MonitoringNamespace
        Write-Success "Создано пространство имен: $MonitoringNamespace"
    } else {
        Write-Info "Пространство имен $MonitoringNamespace уже существует"
    }
    
    # Create app namespace
    $appExists = kubectl get namespace $AppNamespace 2>$null
    if ($LASTEXITCODE -ne 0) {
        kubectl create namespace $AppNamespace
        kubectl label namespace $AppNamespace name=$AppNamespace
        Write-Success "Создано пространство имен: $AppNamespace"
    } else {
        Write-Info "Пространство имен $AppNamespace уже существует"
    }
}

# Add Helm repositories
function Initialize-HelmRepos {
    Write-Step "Настройка Helm репозиториев..."
    
    # Add Prometheus community repo
    $prometheusRepo = helm repo list 2>$null | Select-String -Pattern "prometheus-community"
    if (-not $prometheusRepo) {
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        Write-Success "Добавлен репозиторий prometheus-community"
    }
    
    # Add Grafana repo
    $grafanaRepo = helm repo list 2>$null | Select-String -Pattern "grafana"
    if (-not $grafanaRepo) {
        helm repo add grafana https://grafana.github.io/helm-charts
        Write-Success "Добавлен репозиторий grafana"
    }
    
    # Update repos
    helm repo update
    Write-Success "Репозитории обновлены"
}

# Install Prometheus Operator
function Install-PrometheusOperator {
    Write-Step "Установка Prometheus Operator..."
    
    $prometheusInstalled = helm list -n $MonitoringNamespace 2>$null | Select-String -Pattern "prometheus-operator"
    if ($prometheusInstalled) {
        Write-Info "Prometheus Operator уже установлен"
        return
    }
    
    Write-Info "Установка Prometheus Operator (это может занять несколько минут)..."
    
    helm install prometheus-operator prometheus-community/kube-prometheus-stack `
        --namespace $MonitoringNamespace `
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false `
        --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false `
        --set prometheus.prometheusSpec.retention=30d `
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi `
        --set grafana.adminPassword=admin123 `
        --set grafana.persistence.enabled=true `
        --set grafana.persistence.size=10Gi `
        --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=5Gi `
        --wait `
        --timeout=15m
    
    Write-Success "Prometheus Operator установлен"
}

# Apply monitoring configurations
function Set-MonitoringConfigs {
    Write-Step "Применение конфигураций мониторинга..."
    
    # Apply Grafana datasources
    $datasourcesPath = Join-Path $ProjectRoot "config\monitoring\grafana-datasources.yaml"
    if (Test-Path $datasourcesPath) {
        kubectl apply -f $datasourcesPath
        Write-Success "Применены источники данных Grafana"
    }
    
    # Apply Alertmanager config
    $alertmanagerPath = Join-Path $ProjectRoot "config\monitoring\alertmanager-config.yaml"
    if (Test-Path $alertmanagerPath) {
        kubectl apply -f $alertmanagerPath
        Write-Success "Применена конфигурация Alertmanager"
    }
    
    # Apply extended Prometheus rules
    $rulesPath = Join-Path $ProjectRoot "config\monitoring\prometheus-rules.yaml"
    if (Test-Path $rulesPath) {
        kubectl apply -f $rulesPath
        Write-Success "Применены расширенные правила Prometheus"
    }
}

# Deploy MLOps application
function Deploy-MLOpsApp {
    Write-Step "Развертывание MLOps приложения..."
    
    $environment = if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { "dev" }
    $imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
    
    Write-Info "Развертывание в окружении: $environment"
    Write-Info "Тег образа: $imageTag"
    
    $helmPath = Join-Path $ProjectRoot "helm\mlops-sentiment"
    $valuesPath = Join-Path $ProjectRoot "helm\mlops-sentiment\values-$environment.yaml"
    
    # Deploy with Helm
    helm upgrade --install mlops-sentiment $helmPath `
        --namespace $AppNamespace `
        --values $valuesPath `
        --set image.tag=$imageTag `
        --wait `
        --timeout=10m
    
    Write-Success "MLOps приложение развернуто"
}

# Verify deployment
function Test-Deployment {
    Write-Step "Проверка развертывания..."
    
    # Check Prometheus Operator components
    Write-Info "Проверка компонентов Prometheus Operator..."
    kubectl get pods -n $MonitoringNamespace -l app.kubernetes.io/name=prometheus
    kubectl get pods -n $MonitoringNamespace -l app.kubernetes.io/name=grafana
    kubectl get pods -n $MonitoringNamespace -l app.kubernetes.io/name=alertmanager
    
    # Check MLOps application
    Write-Info "Проверка MLOps приложения..."
    kubectl get pods -n $AppNamespace -l app.kubernetes.io/name=mlops-sentiment
    
    # Wait for pods to be ready
    Write-Info "Ожидание готовности подов..."
    kubectl wait --for=condition=ready pod `
        --selector=app.kubernetes.io/name=prometheus `
        --namespace=$MonitoringNamespace `
        --timeout=300s
    
    kubectl wait --for=condition=ready pod `
        --selector=app.kubernetes.io/name=grafana `
        --namespace=$MonitoringNamespace `
        --timeout=300s
    
    kubectl wait --for=condition=ready pod `
        --selector=app.kubernetes.io/name=mlops-sentiment `
        --namespace=$AppNamespace `
        --timeout=300s
    
    Write-Success "Все компоненты готовы к работе"
}

# Test monitoring stack
function Test-Monitoring {
    Write-Step "Тестирование системы мониторинга..."
    
    # Test metrics endpoint
    Write-Info "Тестирование эндпоинта метрик..."
    
    $job = Start-Job -ScriptBlock {
        kubectl port-forward -n $using:AppNamespace svc/mlops-sentiment 8080:80
    }
    
    Start-Sleep -Seconds 10
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/metrics" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "Эндпоинт метрик работает"
        }
    } catch {
        Write-ErrorMsg "Эндпоинт метрик недоступен"
    } finally {
        Stop-Job -Job $job
        Remove-Job -Job $job
    }
    
    # Check ServiceMonitor
    $serviceMonitorExists = kubectl get servicemonitor -n $AppNamespace mlops-sentiment 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ServiceMonitor создан"
    } else {
        Write-Warning "ServiceMonitor не найден"
    }
    
    # Check PrometheusRule
    $ruleExists = kubectl get prometheusrule -n $AppNamespace mlops-sentiment-alerts 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "PrometheusRule создан"
    } else {
        Write-Warning "PrometheusRule не найден"
    }
}

# Show access information
function Show-AccessInfo {
    Write-Step "Информация о доступе..."
    
    Write-Host ""
    Write-Host "Система мониторинга успешно развернута!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Доступ к интерфейсам:" -ForegroundColor Blue
    Write-Host ""
    
    # Grafana
    Write-Host "Grafana Dashboard:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward -n $MonitoringNamespace svc/prometheus-operator-grafana 3000:80"
    Write-Host "  URL: http://localhost:3000"
    Write-Host "  Логин: admin"
    Write-Host "  Пароль: admin123"
    Write-Host ""
    
    # Prometheus
    Write-Host "Prometheus:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward -n $MonitoringNamespace svc/prometheus-operator-kube-p-prometheus 9090:9090"
    Write-Host "  URL: http://localhost:9090"
    Write-Host ""
    
    # Alertmanager
    Write-Host "Alertmanager:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward -n $MonitoringNamespace svc/prometheus-operator-kube-p-alertmanager 9093:9093"
    Write-Host "  URL: http://localhost:9093"
    Write-Host ""
    
    # MLOps Application
    Write-Host "MLOps Application:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward -n $AppNamespace svc/mlops-sentiment 8080:80"
    Write-Host "  Health: http://localhost:8080/health"
    Write-Host "  Metrics: http://localhost:8080/metrics"
    Write-Host "  API Docs: http://localhost:8080/docs"
    Write-Host ""
    
    Write-Host "Полезные команды:" -ForegroundColor Blue
    Write-Host "  # Просмотр логов приложения"
    Write-Host "  kubectl logs -f -n $AppNamespace -l app.kubernetes.io/name=mlops-sentiment"
    Write-Host ""
    Write-Host "  # Масштабирование"
    Write-Host "  kubectl scale deployment mlops-sentiment --replicas=5 -n $AppNamespace"
    Write-Host ""
    Write-Host "  # Обновление"
    Write-Host "  helm upgrade mlops-sentiment .\helm\mlops-sentiment -n $AppNamespace"
    Write-Host ""
    Write-Host "  # Удаление"
    Write-Host "  helm uninstall mlops-sentiment -n $AppNamespace"
    Write-Host "  helm uninstall prometheus-operator -n $MonitoringNamespace"
    Write-Host ""
    
    $docsPath = Join-Path $ProjectRoot "MONITORING.md"
    Write-Host "Документация: $docsPath" -ForegroundColor Green
    Write-Host ""
}

# Main execution
function Start-Setup {
    Show-Banner
    
    Test-Prerequisites
    Initialize-Namespaces
    Initialize-HelmRepos
    Install-PrometheusOperator
    Set-MonitoringConfigs
    Deploy-MLOpsApp
    Test-Deployment
    Test-Monitoring
    Show-AccessInfo
    
    Write-Host ""
    Write-Success "Настройка системы мониторинга завершена успешно!"
    Write-Host ""
}

# Cleanup function
function Remove-Monitoring {
    Write-Info "Удаление системы мониторинга..."
    helm uninstall mlops-sentiment -n $AppNamespace 2>$null
    helm uninstall prometheus-operator -n $MonitoringNamespace 2>$null
    kubectl delete namespace $AppNamespace 2>$null
    kubectl delete namespace $MonitoringNamespace 2>$null
    Write-Success "Система мониторинга удалена"
}

# Status function
function Show-Status {
    Write-Host "Статус системы мониторинга:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Prometheus Operator:"
    helm status prometheus-operator -n $MonitoringNamespace 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "  Не установлен" }
    Write-Host ""
    Write-Host "MLOps Application:"
    helm status mlops-sentiment -n $AppNamespace 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "  Не установлен" }
    Write-Host ""
    Write-Host "Поды:"
    kubectl get pods -n $MonitoringNamespace 2>$null
    kubectl get pods -n $AppNamespace 2>$null
}

# Handle script actions
switch ($Action) {
    "setup" {
        Start-Setup
    }
    "cleanup" {
        Remove-Monitoring
    }
    "status" {
        Show-Status
    }
    "test" {
        Test-Monitoring
    }
}
