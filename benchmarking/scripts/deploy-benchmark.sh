#!/bin/bash
# MLOps Sentiment Analysis - Automated Benchmarking Deployment Script
# Автоматическое развертывание и запуск бенчмарков на разных типах инстансов

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/configs/benchmark-config.yaml"
RESULTS_DIR="${PROJECT_ROOT}/results"
NAMESPACE="mlops-benchmark"

# Функции для логирования
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

# Функция для проверки зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверяем kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl не найден. Установите Kubernetes CLI."
        exit 1
    fi
    
    # Проверяем helm
    if ! command -v helm &> /dev/null; then
        log_error "helm не найден. Установите Helm."
        exit 1
    fi
    
    # Проверяем python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 не найден."
        exit 1
    fi
    
    # Проверяем подключение к кластеру
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Нет подключения к Kubernetes кластеру."
        exit 1
    fi
    
    log_success "Все зависимости проверены"
}

# Функция для создания namespace
create_namespace() {
    log_info "Создание namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE уже существует"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace $NAMESPACE создан"
    fi
    
    # Добавляем labels для мониторинга
    kubectl label namespace "$NAMESPACE" monitoring=enabled --overwrite
    kubectl label namespace "$NAMESPACE" benchmark=true --overwrite
}

# Функция для установки Python зависимостей
install_python_deps() {
    log_info "Установка Python зависимостей..."
    
    cd "$PROJECT_ROOT"
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        log_success "Python зависимости установлены"
    else
        log_warning "requirements.txt не найден, создаем..."
        cat > requirements.txt << EOF
asyncio
aiohttp
pyyaml
numpy
pandas
matplotlib
seaborn
psutil
kubernetes
pynvml
prometheus-client
EOF
        pip3 install -r requirements.txt
        log_success "Python зависимости установлены"
    fi
}

# Функция для развертывания приложения на CPU инстансе
deploy_cpu_instance() {
    local instance_type=$1
    log_info "Развертывание CPU инстанса: $instance_type"
    
    # Копируем и модифицируем deployment файл
    local deployment_file="/tmp/cpu-deployment-${instance_type}.yaml"
    cp "${PROJECT_ROOT}/deployments/cpu-deployment.yaml" "$deployment_file"
    
    # Заменяем тип инстанса в deployment
    sed -i "s/t3.medium/$instance_type/g" "$deployment_file"
    sed -i "s/mlops-sentiment-cpu/mlops-sentiment-cpu-${instance_type}/g" "$deployment_file"
    
    # Применяем deployment
    kubectl apply -f "$deployment_file" -n "$NAMESPACE"
    
    # Ждем готовности пода
    log_info "Ожидание готовности пода..."
    kubectl wait --for=condition=ready pod -l app=mlops-sentiment,instance-type=cpu -n "$NAMESPACE" --timeout=300s
    
    log_success "CPU инстанс $instance_type развернут"
}

# Функция для развертывания приложения на GPU инстансе
deploy_gpu_instance() {
    local instance_type=$1
    local gpu_type=$2
    log_info "Развертывание GPU инстанса: $instance_type ($gpu_type)"
    
    # Копируем и модифицируем deployment файл
    local deployment_file="/tmp/gpu-deployment-${instance_type}.yaml"
    cp "${PROJECT_ROOT}/deployments/gpu-deployment.yaml" "$deployment_file"
    
    # Заменяем тип инстанса и GPU в deployment
    sed -i "s/nvidia-tesla-t4/nvidia-${gpu_type,,}/g" "$deployment_file"
    sed -i "s/mlops-sentiment-gpu/mlops-sentiment-gpu-${instance_type}/g" "$deployment_file"
    
    # Применяем deployment
    kubectl apply -f "$deployment_file" -n "$NAMESPACE"
    
    # Ждем готовности пода
    log_info "Ожидание готовности GPU пода..."
    kubectl wait --for=condition=ready pod -l app=mlops-sentiment,instance-type=gpu -n "$NAMESPACE" --timeout=600s
    
    log_success "GPU инстанс $instance_type развернут"
}

# Функция для запуска бенчмарка
run_benchmark() {
    local instance_name=$1
    local instance_type=$2
    local service_name=$3
    
    log_info "Запуск бенчмарка для $instance_name"
    
    # Port-forward для доступа к сервису
    local local_port=$((8080 + RANDOM % 1000))
    kubectl port-forward "svc/$service_name" "$local_port:80" -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    # Ждем установления соединения
    sleep 10
    
    # Запускаем мониторинг ресурсов в фоне
    log_info "Запуск мониторинга ресурсов..."
    python3 "${SCRIPT_DIR}/resource-monitor.py" \
        --namespace "$NAMESPACE" \
        --duration 360 \
        --output "${RESULTS_DIR}/resource_metrics_${instance_name}.json" &
    local monitor_pid=$!
    
    # Запускаем нагрузочное тестирование
    log_info "Запуск нагрузочного тестирования..."
    
    # Тестируем с разным количеством пользователей
    local users_array=(1 5 10 20 50 100)
    
    for users in "${users_array[@]}"; do
        log_info "Тестирование с $users пользователями..."
        
        python3 "${SCRIPT_DIR}/load-test.py" \
            --config "$CONFIG_FILE" \
            --instance-type "$instance_name" \
            --endpoint "http://localhost:$local_port/predict" \
            --users "$users" \
            --duration 60 \
            --output "${RESULTS_DIR}/benchmark_${instance_name}_${users}users.json" \
            --report-dir "${RESULTS_DIR}/reports"
        
        # Небольшая пауза между тестами
        sleep 30
    done
    
    # Останавливаем мониторинг
    kill $monitor_pid 2>/dev/null || true
    
    # Останавливаем port-forward
    kill $port_forward_pid 2>/dev/null || true
    
    log_success "Бенчмарк для $instance_name завершен"
}

# Функция для объединения результатов
consolidate_results() {
    log_info "Объединение результатов бенчмарков..."
    
    cd "$RESULTS_DIR"
    
    # Создаем сводный JSON файл
    echo "[]" > consolidated_results.json
    
    # Объединяем все результаты
    for result_file in benchmark_*.json; do
        if [ -f "$result_file" ]; then
            # Добавляем результат в сводный файл
            jq '. += [input]' consolidated_results.json "$result_file" > temp.json && mv temp.json consolidated_results.json
        fi
    done
    
    log_success "Результаты объединены в consolidated_results.json"
}

# Функция для генерации отчета о стоимости
generate_cost_report() {
    log_info "Генерация отчета о стоимости..."
    
    python3 "${SCRIPT_DIR}/cost-calculator.py" \
        --config "$CONFIG_FILE" \
        --results "${RESULTS_DIR}/consolidated_results.json" \
        --predictions 1000 \
        --output "${RESULTS_DIR}/cost_analysis.json" \
        --report-dir "${RESULTS_DIR}/cost_reports"
    
    log_success "Отчет о стоимости сгенерирован"
}

# Функция для очистки ресурсов
cleanup() {
    log_info "Очистка ресурсов..."
    
    # Удаляем все deployments в namespace
    kubectl delete deployments --all -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete services --all -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete hpa --all -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete pdb --all -n "$NAMESPACE" 2>/dev/null || true
    
    # Удаляем временные файлы
    rm -f /tmp/cpu-deployment-*.yaml
    rm -f /tmp/gpu-deployment-*.yaml
    
    log_success "Ресурсы очищены"
}

# Функция для генерации финального отчета
generate_final_report() {
    log_info "Генерация финального отчета..."
    
    local report_file="${RESULTS_DIR}/benchmark_final_report.md"
    
    cat > "$report_file" << EOF
# 📊 MLOps Sentiment Analysis - Benchmark Report

**Дата:** $(date)
**Namespace:** $NAMESPACE

## 🎯 Результаты бенчмарка

### Протестированные инстансы:
EOF
    
    # Добавляем информацию о каждом тесте
    for result_file in "${RESULTS_DIR}"/benchmark_*.json; do
        if [ -f "$result_file" ]; then
            local instance_name=$(jq -r '.instance_type' "$result_file")
            local rps=$(jq -r '.requests_per_second' "$result_file")
            local latency=$(jq -r '.avg_latency' "$result_file")
            local users=$(jq -r '.concurrent_users' "$result_file")
            
            echo "- **$instance_name** ($users users): ${rps} RPS, ${latency}ms latency" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

## 📈 Файлы результатов:
- Сводные результаты: \`consolidated_results.json\`
- Анализ стоимости: \`cost_analysis.json\`
- Графики и визуализация: \`reports/\` и \`cost_reports/\`
- Метрики ресурсов: \`resource_metrics_*.json\`

## 🚀 Следующие шаги:
1. Проанализируйте результаты в \`cost_reports/\`
2. Выберите оптимальный тип инстанса на основе ваших требований
3. Настройте production deployment с выбранными параметрами

EOF
    
    log_success "Финальный отчет создан: $report_file"
}

# Основная функция
main() {
    log_info "🚀 Запуск автоматического бенчмаркинга MLOps Sentiment Analysis"
    
    # Создаем директории
    mkdir -p "$RESULTS_DIR"/{reports,cost_reports}
    
    # Проверяем зависимости
    check_dependencies
    
    # Устанавливаем Python зависимости
    install_python_deps
    
    # Создаем namespace
    create_namespace
    
    # Читаем конфигурацию инстансов
    log_info "Чтение конфигурации инстансов..."
    
    # CPU инстансы
    local cpu_instances=($(yq eval '.instances.cpu[].name' "$CONFIG_FILE"))
    log_info "Найдено CPU инстансов: ${#cpu_instances[@]}"
    
    # GPU инстансы  
    local gpu_instances=($(yq eval '.instances.gpu[].name' "$CONFIG_FILE"))
    log_info "Найдено GPU инстансов: ${#gpu_instances[@]}"
    
    # Запускаем бенчмарки для CPU инстансов
    for instance in "${cpu_instances[@]}"; do
        local instance_type=$(yq eval ".instances.cpu[] | select(.name == \"$instance\") | .type" "$CONFIG_FILE")
        
        deploy_cpu_instance "$instance_type"
        run_benchmark "$instance" "cpu" "mlops-sentiment-cpu-${instance_type}-svc"
        
        # Очищаем deployment перед следующим тестом
        kubectl delete deployment "mlops-sentiment-cpu-${instance_type}" -n "$NAMESPACE" || true
        sleep 30
    done
    
    # Запускаем бенчмарки для GPU инстансов
    for instance in "${gpu_instances[@]}"; do
        local instance_type=$(yq eval ".instances.gpu[] | select(.name == \"$instance\") | .type" "$CONFIG_FILE")
        local gpu_type=$(yq eval ".instances.gpu[] | select(.name == \"$instance\") | .gpu" "$CONFIG_FILE")
        
        deploy_gpu_instance "$instance_type" "$gpu_type"
        run_benchmark "$instance" "gpu" "mlops-sentiment-gpu-${instance_type}-svc"
        
        # Очищаем deployment перед следующим тестом
        kubectl delete deployment "mlops-sentiment-gpu-${instance_type}" -n "$NAMESPACE" || true
        sleep 30
    done
    
    # Объединяем результаты
    consolidate_results
    
    # Генерируем отчет о стоимости
    generate_cost_report
    
    # Генерируем финальный отчет
    generate_final_report
    
    # Очищаем ресурсы
    cleanup
    
    log_success "🎉 Бенчмаркинг завершен! Результаты доступны в: $RESULTS_DIR"
    log_info "📊 Откройте $RESULTS_DIR/benchmark_final_report.md для просмотра результатов"
}

# Обработка сигналов для корректной очистки
trap cleanup EXIT INT TERM

# Парсинг аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --cleanup-only)
            cleanup
            exit 0
            ;;
        --help)
            echo "Использование: $0 [OPTIONS]"
            echo "Опции:"
            echo "  --config FILE         Путь к файлу конфигурации (по умолчанию: configs/benchmark-config.yaml)"
            echo "  --namespace NAME      Kubernetes namespace (по умолчанию: mlops-benchmark)"
            echo "  --results-dir DIR     Директория для результатов (по умолчанию: results)"
            echo "  --cleanup-only        Только очистить ресурсы и выйти"
            echo "  --help               Показать эту справку"
            exit 0
            ;;
        *)
            log_error "Неизвестная опция: $1"
            exit 1
            ;;
    esac
done

# Запуск основной функции
main
