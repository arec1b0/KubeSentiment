#!/bin/bash
# MLOps Sentiment Analysis - Quick Benchmark Script
# Быстрый запуск бенчмарка для тестирования одного инстанса

set -e

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Функции логирования
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Конфигурация по умолчанию
INSTANCE_TYPE="cpu-small"
USERS=10
DURATION=60
ENDPOINT="http://localhost:8080/predict"
NAMESPACE="mlops-benchmark"

# Функция помощи
show_help() {
    cat << EOF
🚀 MLOps Sentiment Analysis - Quick Benchmark

Использование: $0 [OPTIONS]

Опции:
  -t, --type INSTANCE_TYPE    Тип инстанса (cpu-small, cpu-medium, gpu-t4, etc.)
  -u, --users USERS          Количество одновременных пользователей (по умолчанию: 10)
  -d, --duration DURATION    Длительность теста в секундах (по умолчанию: 60)
  -e, --endpoint ENDPOINT    URL эндпоинта API (по умолчанию: http://localhost:8080/predict)
  -n, --namespace NAMESPACE  Kubernetes namespace (по умолчанию: mlops-benchmark)
  -h, --help                 Показать эту справку

Примеры:
  $0 -t cpu-medium -u 20 -d 120
  $0 --type gpu-t4 --users 50 --duration 300
  $0 -e http://my-service:8080/predict -u 100

Доступные типы инстансов:
  CPU: cpu-small, cpu-medium, cpu-large, cpu-xlarge
  GPU: gpu-t4, gpu-v100, gpu-a100
EOF
}

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -e|--endpoint)
            ENDPOINT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
done

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="${PROJECT_ROOT}/results"

log_info "🚀 Запуск быстрого бенчмарка"
log_info "Тип инстанса: $INSTANCE_TYPE"
log_info "Пользователи: $USERS"
log_info "Длительность: ${DURATION}s"
log_info "Эндпоинт: $ENDPOINT"

# Создаем директории результатов
mkdir -p "$RESULTS_DIR"/{reports,cost_reports}

# Проверяем доступность эндпоинта
log_info "Проверка доступности эндпоинта..."
if curl -s --connect-timeout 5 "${ENDPOINT%/predict}/health" > /dev/null; then
    log_success "Эндпоинт доступен"
else
    log_warning "Эндпоинт недоступен, продолжаем тестирование..."
fi

# Запускаем мониторинг ресурсов в фоне
log_info "Запуск мониторинга ресурсов..."
python3 "${SCRIPT_DIR}/resource-monitor.py" \
    --namespace "$NAMESPACE" \
    --duration $((DURATION + 30)) \
    --output "${RESULTS_DIR}/resource_metrics_${INSTANCE_TYPE}_quick.json" &
MONITOR_PID=$!

# Небольшая пауза для инициализации мониторинга
sleep 5

# Запускаем нагрузочное тестирование
log_info "Запуск нагрузочного тестирования..."
python3 "${SCRIPT_DIR}/load-test.py" \
    --config "${PROJECT_ROOT}/configs/benchmark-config.yaml" \
    --instance-type "$INSTANCE_TYPE" \
    --endpoint "$ENDPOINT" \
    --users "$USERS" \
    --duration "$DURATION" \
    --output "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json" \
    --report-dir "${RESULTS_DIR}/reports"

# Останавливаем мониторинг
log_info "Остановка мониторинга ресурсов..."
kill $MONITOR_PID 2>/dev/null || true
wait $MONITOR_PID 2>/dev/null || true

# Рассчитываем стоимость
log_info "Расчет стоимости..."
python3 "${SCRIPT_DIR}/cost-calculator.py" \
    --config "${PROJECT_ROOT}/configs/benchmark-config.yaml" \
    --results "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json" \
    --predictions 1000 \
    --output "${RESULTS_DIR}/cost_analysis_${INSTANCE_TYPE}_quick.json" \
    --report-dir "${RESULTS_DIR}/cost_reports"

# Генерируем быстрый отчет
log_info "Генерация отчета..."
python3 "${SCRIPT_DIR}/report-generator.py" \
    --results-dir "$RESULTS_DIR" \
    --output "${RESULTS_DIR}/quick_benchmark_report_${INSTANCE_TYPE}.html"

# Выводим краткие результаты
log_success "🎉 Бенчмарк завершен!"

if [ -f "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json" ]; then
    echo ""
    echo "📊 РЕЗУЛЬТАТЫ БЕНЧМАРКА:"
    echo "========================"
    
    # Извлекаем ключевые метрики с помощью jq
    if command -v jq &> /dev/null; then
        RPS=$(jq -r '.requests_per_second' "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json")
        AVG_LATENCY=$(jq -r '.avg_latency' "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json")
        P95_LATENCY=$(jq -r '.p95_latency' "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json")
        ERROR_RATE=$(jq -r '.error_rate' "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json")
        TOTAL_REQUESTS=$(jq -r '.total_requests' "${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json")
        
        echo "🚀 Запросов в секунду: ${RPS}"
        echo "⚡ Средняя латентность: ${AVG_LATENCY}ms"
        echo "📈 P95 латентность: ${P95_LATENCY}ms"
        echo "❌ Процент ошибок: ${ERROR_RATE}%"
        echo "📊 Всего запросов: ${TOTAL_REQUESTS}"
    else
        log_warning "jq не установлен, подробные результаты смотрите в JSON файлах"
    fi
    
    # Показываем стоимость если доступна
    if [ -f "${RESULTS_DIR}/cost_analysis_${INSTANCE_TYPE}_quick.json" ] && command -v jq &> /dev/null; then
        COST_1000=$(jq -r '.analyses[0].cost_per_1000_predictions' "${RESULTS_DIR}/cost_analysis_${INSTANCE_TYPE}_quick.json" 2>/dev/null)
        if [ "$COST_1000" != "null" ] && [ "$COST_1000" != "" ]; then
            echo "💰 Стоимость 1000 предсказаний: \$${COST_1000}"
        fi
    fi
fi

echo ""
echo "📁 ФАЙЛЫ РЕЗУЛЬТАТОВ:"
echo "====================="
echo "📊 Результаты бенчмарка: ${RESULTS_DIR}/benchmark_${INSTANCE_TYPE}_quick.json"
echo "🖥️  Метрики ресурсов: ${RESULTS_DIR}/resource_metrics_${INSTANCE_TYPE}_quick.json"
echo "💰 Анализ стоимости: ${RESULTS_DIR}/cost_analysis_${INSTANCE_TYPE}_quick.json"
echo "📋 HTML отчет: ${RESULTS_DIR}/quick_benchmark_report_${INSTANCE_TYPE}.html"
echo ""
echo "🌐 Откройте HTML отчет в браузере для детального анализа:"
echo "   file://${RESULTS_DIR}/quick_benchmark_report_${INSTANCE_TYPE}.html"

log_success "Быстрый бенчмарк завершен успешно!"
