#!/bin/bash

# MLOps Monitoring Setup Script
# Полная настройка системы мониторинга с нуля

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MONITORING_NAMESPACE="monitoring"
APP_NAMESPACE="mlops-sentiment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${PURPLE}"
    cat << "EOF"
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
EOF
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_step "Проверка предварительных требований..."
    
    local missing_tools=()
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi
    
    # Check yq (for YAML processing)
    if ! command -v yq &> /dev/null; then
        log_warning "yq не найден, некоторые функции могут быть недоступны"
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Отсутствуют необходимые инструменты: ${missing_tools[*]}"
        log_info "Установите их и повторите попытку:"
        echo "  kubectl: https://kubernetes.io/docs/tasks/tools/"
        echo "  helm: https://helm.sh/docs/intro/install/"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Не удается подключиться к кластеру Kubernetes"
        log_info "Убедитесь, что kubectl настроен правильно"
        exit 1
    fi
    
    log_success "Все предварительные требования выполнены"
}

# Setup namespaces
setup_namespaces() {
    log_step "Настройка пространств имен..."
    
    # Create monitoring namespace
    if ! kubectl get namespace $MONITORING_NAMESPACE &> /dev/null; then
        kubectl create namespace $MONITORING_NAMESPACE
        kubectl label namespace $MONITORING_NAMESPACE name=$MONITORING_NAMESPACE
        log_success "Создано пространство имен: $MONITORING_NAMESPACE"
    else
        log_info "Пространство имен $MONITORING_NAMESPACE уже существует"
    fi
    
    # Create app namespace
    if ! kubectl get namespace $APP_NAMESPACE &> /dev/null; then
        kubectl create namespace $APP_NAMESPACE
        kubectl label namespace $APP_NAMESPACE name=$APP_NAMESPACE
        log_success "Создано пространство имен: $APP_NAMESPACE"
    else
        log_info "Пространство имен $APP_NAMESPACE уже существует"
    fi
}

# Add Helm repositories
setup_helm_repos() {
    log_step "Настройка Helm репозиториев..."
    
    # Add Prometheus community repo
    if ! helm repo list | grep -q prometheus-community; then
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        log_success "Добавлен репозиторий prometheus-community"
    fi
    
    # Add Grafana repo
    if ! helm repo list | grep -q grafana; then
        helm repo add grafana https://grafana.github.io/helm-charts
        log_success "Добавлен репозиторий grafana"
    fi
    
    # Update repos
    helm repo update
    log_success "Репозитории обновлены"
}

# Install Prometheus Operator
install_prometheus_operator() {
    log_step "Установка Prometheus Operator..."
    
    if helm list -n $MONITORING_NAMESPACE | grep -q prometheus-operator; then
        log_info "Prometheus Operator уже установлен"
        return
    fi
    
    log_info "Установка Prometheus Operator (это может занять несколько минут)..."
    
    helm install prometheus-operator prometheus-community/kube-prometheus-stack \
        --namespace $MONITORING_NAMESPACE \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.ruleSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.retention=30d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --set grafana.adminPassword=admin123 \
        --set grafana.persistence.enabled=true \
        --set grafana.persistence.size=10Gi \
        --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=5Gi \
        --wait \
        --timeout=15m
    
    log_success "Prometheus Operator установлен"
}

# Apply monitoring configurations
apply_monitoring_configs() {
    log_step "Применение конфигураций мониторинга..."
    
    # Apply Grafana datasources
    if [[ -f "$PROJECT_ROOT/monitoring/grafana-datasources.yaml" ]]; then
        kubectl apply -f "$PROJECT_ROOT/monitoring/grafana-datasources.yaml"
        log_success "Применены источники данных Grafana"
    fi
    
    # Apply Alertmanager config
    if [[ -f "$PROJECT_ROOT/monitoring/alertmanager-config.yaml" ]]; then
        kubectl apply -f "$PROJECT_ROOT/monitoring/alertmanager-config.yaml"
        log_success "Применена конфигурация Alertmanager"
    fi
    
    # Apply extended Prometheus rules
    if [[ -f "$PROJECT_ROOT/monitoring/prometheus-rules.yaml" ]]; then
        kubectl apply -f "$PROJECT_ROOT/monitoring/prometheus-rules.yaml"
        log_success "Применены расширенные правила Prometheus"
    fi
}

# Deploy MLOps application
deploy_mlops_app() {
    log_step "Развертывание MLOps приложения..."
    
    local environment="${ENVIRONMENT:-dev}"
    local image_tag="${IMAGE_TAG:-latest}"
    
    log_info "Развертывание в окружении: $environment"
    log_info "Тег образа: $image_tag"
    
    # Deploy with Helm
    helm upgrade --install mlops-sentiment "$PROJECT_ROOT/helm/mlops-sentiment" \
        --namespace $APP_NAMESPACE \
        --values "$PROJECT_ROOT/helm/mlops-sentiment/values-$environment.yaml" \
        --set image.tag="$image_tag" \
        --wait \
        --timeout=10m
    
    log_success "MLOps приложение развернуто"
}

# Verify deployment
verify_deployment() {
    log_step "Проверка развертывания..."
    
    # Check Prometheus Operator components
    log_info "Проверка компонентов Prometheus Operator..."
    kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=prometheus
    kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=grafana
    kubectl get pods -n $MONITORING_NAMESPACE -l app.kubernetes.io/name=alertmanager
    
    # Check MLOps application
    log_info "Проверка MLOps приложения..."
    kubectl get pods -n $APP_NAMESPACE -l app.kubernetes.io/name=mlops-sentiment
    
    # Wait for pods to be ready
    log_info "Ожидание готовности подов..."
    kubectl wait --for=condition=ready pod \
        --selector=app.kubernetes.io/name=prometheus \
        --namespace=$MONITORING_NAMESPACE \
        --timeout=300s
    
    kubectl wait --for=condition=ready pod \
        --selector=app.kubernetes.io/name=grafana \
        --namespace=$MONITORING_NAMESPACE \
        --timeout=300s
    
    kubectl wait --for=condition=ready pod \
        --selector=app.kubernetes.io/name=mlops-sentiment \
        --namespace=$APP_NAMESPACE \
        --timeout=300s
    
    log_success "Все компоненты готовы к работе"
}

# Test monitoring stack
test_monitoring() {
    log_step "Тестирование системы мониторинга..."
    
    # Test metrics endpoint
    log_info "Тестирование эндпоинта метрик..."
    kubectl port-forward -n $APP_NAMESPACE svc/mlops-sentiment 8080:80 &
    PF_PID=$!
    
    sleep 10
    
    if curl -f http://localhost:8080/metrics &> /dev/null; then
        log_success "Эндпоинт метрик работает"
    else
        log_error "Эндпоинт метрик недоступен"
    fi
    
    kill $PF_PID &> /dev/null || true
    
    # Check ServiceMonitor
    if kubectl get servicemonitor -n $APP_NAMESPACE mlops-sentiment &> /dev/null; then
        log_success "ServiceMonitor создан"
    else
        log_warning "ServiceMonitor не найден"
    fi
    
    # Check PrometheusRule
    if kubectl get prometheusrule -n $APP_NAMESPACE mlops-sentiment-alerts &> /dev/null; then
        log_success "PrometheusRule создан"
    else
        log_warning "PrometheusRule не найден"
    fi
}

# Show access information
show_access_info() {
    log_step "Информация о доступе..."
    
    echo ""
    echo -e "${GREEN}🎉 Система мониторинга успешно развернута!${NC}"
    echo ""
    echo -e "${BLUE}📊 Доступ к интерфейсам:${NC}"
    echo ""
    
    # Grafana
    echo -e "${YELLOW}Grafana Dashboard:${NC}"
    echo "  kubectl port-forward -n $MONITORING_NAMESPACE svc/prometheus-operator-grafana 3000:80"
    echo "  URL: http://localhost:3000"
    echo "  Логин: admin"
    echo "  Пароль: admin123"
    echo ""
    
    # Prometheus
    echo -e "${YELLOW}Prometheus:${NC}"
    echo "  kubectl port-forward -n $MONITORING_NAMESPACE svc/prometheus-operator-kube-p-prometheus 9090:9090"
    echo "  URL: http://localhost:9090"
    echo ""
    
    # Alertmanager
    echo -e "${YELLOW}Alertmanager:${NC}"
    echo "  kubectl port-forward -n $MONITORING_NAMESPACE svc/prometheus-operator-kube-p-alertmanager 9093:9093"
    echo "  URL: http://localhost:9093"
    echo ""
    
    # MLOps Application
    echo -e "${YELLOW}MLOps Application:${NC}"
    echo "  kubectl port-forward -n $APP_NAMESPACE svc/mlops-sentiment 8080:80"
    echo "  Health: http://localhost:8080/health"
    echo "  Metrics: http://localhost:8080/metrics"
    echo "  API Docs: http://localhost:8080/docs"
    echo ""
    
    echo -e "${BLUE}🔧 Полезные команды:${NC}"
    echo "  # Просмотр логов приложения"
    echo "  kubectl logs -f -n $APP_NAMESPACE -l app.kubernetes.io/name=mlops-sentiment"
    echo ""
    echo "  # Масштабирование"
    echo "  kubectl scale deployment mlops-sentiment --replicas=5 -n $APP_NAMESPACE"
    echo ""
    echo "  # Обновление"
    echo "  helm upgrade mlops-sentiment ./helm/mlops-sentiment -n $APP_NAMESPACE"
    echo ""
    echo "  # Удаление"
    echo "  helm uninstall mlops-sentiment -n $APP_NAMESPACE"
    echo "  helm uninstall prometheus-operator -n $MONITORING_NAMESPACE"
    echo ""
    
    echo -e "${GREEN}📚 Документация: ${PROJECT_ROOT}/MONITORING.md${NC}"
    echo ""
}

# Cleanup function
cleanup() {
    log_step "Очистка временных файлов..."
    # Kill any background processes
    jobs -p | xargs -r kill &> /dev/null || true
}

# Main execution
main() {
    # Set trap for cleanup
    trap cleanup EXIT
    
    show_banner
    
    check_prerequisites
    setup_namespaces
    setup_helm_repos
    install_prometheus_operator
    apply_monitoring_configs
    deploy_mlops_app
    verify_deployment
    test_monitoring
    show_access_info
    
    echo ""
    log_success "🎉 Настройка системы мониторинга завершена успешно!"
    echo ""
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "cleanup")
        log_info "Удаление системы мониторинга..."
        helm uninstall mlops-sentiment -n $APP_NAMESPACE 2>/dev/null || true
        helm uninstall prometheus-operator -n $MONITORING_NAMESPACE 2>/dev/null || true
        kubectl delete namespace $APP_NAMESPACE 2>/dev/null || true
        kubectl delete namespace $MONITORING_NAMESPACE 2>/dev/null || true
        log_success "Система мониторинга удалена"
        ;;
    "status")
        echo "📊 Статус системы мониторинга:"
        echo ""
        echo "Prometheus Operator:"
        helm status prometheus-operator -n $MONITORING_NAMESPACE 2>/dev/null || echo "  Не установлен"
        echo ""
        echo "MLOps Application:"
        helm status mlops-sentiment -n $APP_NAMESPACE 2>/dev/null || echo "  Не установлен"
        echo ""
        echo "Поды:"
        kubectl get pods -n $MONITORING_NAMESPACE 2>/dev/null || true
        kubectl get pods -n $APP_NAMESPACE 2>/dev/null || true
        ;;
    "test")
        test_monitoring
        ;;
    *)
        echo "Использование: $0 {setup|cleanup|status|test}"
        echo ""
        echo "  setup   - Полная настройка системы мониторинга"
        echo "  cleanup - Удаление системы мониторинга"
        echo "  status  - Проверка статуса"
        echo "  test    - Тестирование мониторинга"
        exit 1
        ;;
esac
