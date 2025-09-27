#!/bin/bash
# MLOps Sentiment Analysis - Benchmarking System Installer
# Автоматическая установка и настройка системы бенчмаркинга

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

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "🚀 Установка системы бенчмаркинга MLOps Sentiment Analysis"
log_info "Директория проекта: $PROJECT_ROOT"

# Проверка операционной системы
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        log_error "Неподдерживаемая операционная система: $OSTYPE"
        exit 1
    fi
    log_info "Обнаружена ОС: $OS"
}

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка системных зависимостей..."
    
    local missing_deps=()
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Проверяем pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    fi
    
    # Проверяем kubectl (опционально)
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl не найден. Kubernetes функции будут недоступны."
    fi
    
    # Проверяем docker (опционально)
    if ! command -v docker &> /dev/null; then
        log_warning "Docker не найден. Некоторые функции могут быть недоступны."
    fi
    
    # Проверяем jq для обработки JSON
    if ! command -v jq &> /dev/null; then
        log_warning "jq не найден. Установите для лучшего отображения результатов."
        if [[ "$OS" == "linux" ]]; then
            log_info "Установка: sudo apt-get install jq"
        elif [[ "$OS" == "macos" ]]; then
            log_info "Установка: brew install jq"
        fi
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Отсутствуют обязательные зависимости: ${missing_deps[*]}"
        log_info "Установите их и повторите попытку."
        exit 1
    fi
    
    log_success "Все обязательные зависимости найдены"
}

# Установка Python зависимостей
install_python_deps() {
    log_info "Установка Python зависимостей..."
    
    cd "$SCRIPT_DIR/.."
    
    # Проверяем версию Python
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Версия Python: $python_version"
    
    if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
        log_error "Требуется Python 3.8 или выше. Текущая версия: $python_version"
        exit 1
    fi
    
    # Создаем виртуальное окружение (опционально)
    if [[ "$1" == "--venv" ]]; then
        log_info "Создание виртуального окружения..."
        python3 -m venv venv
        source venv/bin/activate
        log_success "Виртуальное окружение активировано"
    fi
    
    # Обновляем pip
    pip3 install --upgrade pip
    
    # Устанавливаем зависимости
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        log_success "Python зависимости установлены"
    else
        log_error "Файл requirements.txt не найден"
        exit 1
    fi
}

# Настройка прав доступа
setup_permissions() {
    log_info "Настройка прав доступа к скриптам..."
    
    # Делаем скрипты исполняемыми
    chmod +x "$SCRIPT_DIR"/*.sh
    chmod +x "$SCRIPT_DIR/../quick-benchmark.sh"
    
    log_success "Права доступа настроены"
}

# Создание директорий
create_directories() {
    log_info "Создание рабочих директорий..."
    
    local dirs=(
        "$SCRIPT_DIR/../results"
        "$SCRIPT_DIR/../results/reports"
        "$SCRIPT_DIR/../results/cost_reports"
        "$SCRIPT_DIR/../results/archive"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "Создана директория: $dir"
    done
    
    log_success "Рабочие директории созданы"
}

# Проверка конфигурации
validate_config() {
    log_info "Проверка конфигурации..."
    
    local config_file="$SCRIPT_DIR/../configs/benchmark-config.yaml"
    
    if [ ! -f "$config_file" ]; then
        log_error "Файл конфигурации не найден: $config_file"
        exit 1
    fi
    
    # Проверяем синтаксис YAML (если установлен yq)
    if command -v yq &> /dev/null; then
        if yq eval '.' "$config_file" > /dev/null 2>&1; then
            log_success "Конфигурация валидна"
        else
            log_error "Ошибка в файле конфигурации: $config_file"
            exit 1
        fi
    else
        log_warning "yq не установлен, пропускаем валидацию YAML"
    fi
}

# Тестовый запуск
test_installation() {
    log_info "Тестирование установки..."
    
    cd "$SCRIPT_DIR/.."
    
    # Тест импорта Python модулей
    python3 -c "
import asyncio
import aiohttp
import yaml
import pandas as pd
import matplotlib.pyplot as plt
print('✅ Все Python модули импортированы успешно')
" || {
        log_error "Ошибка при импорте Python модулей"
        exit 1
    }
    
    # Тест запуска скриптов
    if python3 scripts/load-test.py --help > /dev/null 2>&1; then
        log_success "Скрипт load-test.py работает"
    else
        log_error "Ошибка в скрипте load-test.py"
        exit 1
    fi
    
    if python3 scripts/cost-calculator.py --help > /dev/null 2>&1; then
        log_success "Скрипт cost-calculator.py работает"
    else
        log_error "Ошибка в скрипте cost-calculator.py"
        exit 1
    fi
    
    log_success "Тестирование завершено успешно"
}

# Создание примера конфигурации
create_example_config() {
    log_info "Создание примера конфигурации..."
    
    local example_file="$SCRIPT_DIR/../configs/benchmark-config.example.yaml"
    
    cp "$SCRIPT_DIR/../configs/benchmark-config.yaml" "$example_file"
    
    log_success "Пример конфигурации создан: $example_file"
}

# Показать информацию о следующих шагах
show_next_steps() {
    echo ""
    log_success "🎉 Установка системы бенчмаркинга завершена!"
    echo ""
    echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
    echo "=================="
    echo ""
    echo "1. 🚀 Быстрый тест:"
    echo "   cd $(basename "$SCRIPT_DIR/..")"
    echo "   ./quick-benchmark.sh"
    echo ""
    echo "2. 🎯 Тест конкретного инстанса:"
    echo "   ./quick-benchmark.sh -t cpu-medium -u 20 -d 120"
    echo ""
    echo "3. 📊 Полный бенчмарк:"
    echo "   ./scripts/deploy-benchmark.sh"
    echo ""
    echo "4. 📚 Документация:"
    echo "   - Основное руководство: BENCHMARKING.md"
    echo "   - Примеры использования: examples/example-usage.md"
    echo "   - Конфигурация: configs/benchmark-config.yaml"
    echo ""
    echo "5. 📁 Результаты будут сохранены в:"
    echo "   - results/ - основные результаты"
    echo "   - results/reports/ - графики и отчеты"
    echo "   - results/cost_reports/ - анализ стоимости"
    echo ""
    echo "🔧 НАСТРОЙКА:"
    echo "============="
    echo "- Отредактируйте configs/benchmark-config.yaml для ваших нужд"
    echo "- Настройте Kubernetes кластер для полного тестирования"
    echo "- Установите jq для лучшего отображения результатов"
    echo ""
    echo "❓ ПОМОЩЬ:"
    echo "=========="
    echo "- ./quick-benchmark.sh --help"
    echo "- ./scripts/deploy-benchmark.sh --help"
    echo "- Документация: BENCHMARKING.md"
}

# Основная функция
main() {
    local use_venv=false
    
    # Парсинг аргументов
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv)
                use_venv=true
                shift
                ;;
            --help)
                echo "Установщик системы бенчмаркинга MLOps Sentiment Analysis"
                echo ""
                echo "Использование: $0 [OPTIONS]"
                echo ""
                echo "Опции:"
                echo "  --venv    Создать и использовать виртуальное окружение Python"
                echo "  --help    Показать эту справку"
                echo ""
                exit 0
                ;;
            *)
                log_error "Неизвестная опция: $1"
                exit 1
                ;;
        esac
    done
    
    # Выполняем установку
    detect_os
    check_dependencies
    create_directories
    setup_permissions
    
    if [ "$use_venv" = true ]; then
        install_python_deps --venv
    else
        install_python_deps
    fi
    
    validate_config
    create_example_config
    test_installation
    show_next_steps
}

# Обработка прерывания
trap 'log_error "Установка прервана пользователем"; exit 1' INT TERM

# Запуск основной функции
main "$@"
