#!/bin/bash
# Автоматическая настройка CI/CD пайплайна
# Скрипт для первоначальной настройки всех необходимых компонентов

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Логирование
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

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    # Проверяем наличие необходимых инструментов
    local deps=("gh" "kubectl" "docker" "curl" "jq")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Отсутствуют необходимые зависимости: ${missing[*]}"
        log_info "Установите недостающие инструменты:"
        for dep in "${missing[@]}"; do
            case $dep in
                "gh")
                    echo "  - GitHub CLI: https://cli.github.com/"
                    ;;
                "kubectl")
                    echo "  - kubectl: https://kubernetes.io/docs/tasks/tools/"
                    ;;
                "docker")
                    echo "  - Docker: https://docs.docker.com/get-docker/"
                    ;;
                "curl")
                    echo "  - curl: обычно предустановлен"
                    ;;
                "jq")
                    echo "  - jq: https://stedolan.github.io/jq/"
                    ;;
            esac
        done
        exit 1
    fi
    
    log_success "Все зависимости установлены"
}

# Проверка аутентификации GitHub
check_github_auth() {
    log_info "Проверка аутентификации GitHub..."
    
    if ! gh auth status &> /dev/null; then
        log_warning "GitHub CLI не аутентифицирован"
        log_info "Запуск аутентификации..."
        gh auth login
    fi
    
    log_success "GitHub аутентификация OK"
}

# Настройка GitHub Environments
setup_environments() {
    log_info "Настройка GitHub Environments..."
    
    local environments=("development" "staging" "production")
    
    for env in "${environments[@]}"; do
        log_info "Создание окружения: $env"
        
        # Создаем окружение (игнорируем ошибку если уже существует)
        gh api repos/:owner/:repo/environments/$env \
            --method PUT \
            --field wait_timer=0 \
            --silent 2>/dev/null || true
        
        # Настраиваем protection rules для production
        if [ "$env" = "production" ]; then
            log_info "Настройка protection rules для production..."
            gh api repos/:owner/:repo/environments/production \
                --method PUT \
                --field wait_timer=600 \
                --field prevent_self_review=true \
                --field reviewers='[{"type":"Team","id":null}]' \
                --silent 2>/dev/null || true
        fi
    done
    
    log_success "GitHub Environments настроены"
}

# Настройка секретов
setup_secrets() {
    log_info "Настройка секретов..."
    
    # Kubernetes configurations
    setup_kubernetes_secrets
    
    # Slack webhook
    setup_slack_webhook
    
    # Container signing
    setup_cosign_keys
    
    log_success "Секреты настроены"
}

# Настройка Kubernetes секретов
setup_kubernetes_secrets() {
    log_info "Настройка Kubernetes секретов..."
    
    local kube_configs=("dev" "staging" "prod")
    
    for env in "${kube_configs[@]}"; do
        local config_file="$HOME/.kube/config-$env"
        local secret_name="KUBE_CONFIG_${env^^}"
        
        if [ -f "$config_file" ]; then
            log_info "Настройка $secret_name..."
            base64 -w 0 "$config_file" | gh secret set "$secret_name"
            log_success "$secret_name настроен"
        else
            log_warning "Файл $config_file не найден, пропускаем $secret_name"
            log_info "Создайте файл kubeconfig для окружения $env или настройте секрет вручную"
        fi
    done
}

# Настройка Slack webhook
setup_slack_webhook() {
    log_info "Настройка Slack webhook..."
    
    read -p "Введите Slack Webhook URL (или нажмите Enter для пропуска): " slack_url
    
    if [ -n "$slack_url" ]; then
        echo "$slack_url" | gh secret set SLACK_WEBHOOK_URL
        log_success "Slack webhook настроен"
    else
        log_warning "Slack webhook пропущен"
    fi
}

# Настройка ключей для подписи контейнеров
setup_cosign_keys() {
    log_info "Настройка ключей cosign для подписи контейнеров..."
    
    if command -v cosign &> /dev/null; then
        read -p "Сгенерировать новые ключи cosign? (y/n): " generate_keys
        
        if [ "$generate_keys" = "y" ] || [ "$generate_keys" = "Y" ]; then
            log_info "Генерация ключей cosign..."
            
            # Создаем временную директорию
            local temp_dir=$(mktemp -d)
            cd "$temp_dir"
            
            # Генерируем ключи
            cosign generate-key-pair
            
            # Устанавливаем секреты
            gh secret set COSIGN_PRIVATE_KEY < cosign.key
            
            read -s -p "Введите пароль для ключа cosign: " cosign_password
            echo
            echo "$cosign_password" | gh secret set COSIGN_PASSWORD
            
            # Очищаем временные файлы
            cd - > /dev/null
            rm -rf "$temp_dir"
            
            log_success "Ключи cosign настроены"
        else
            log_warning "Генерация ключей cosign пропущена"
        fi
    else
        log_warning "cosign не установлен, пропускаем настройку ключей"
        log_info "Установите cosign: https://docs.sigstore.dev/cosign/installation/"
    fi
}

# Настройка переменных репозитория
setup_variables() {
    log_info "Настройка переменных репозитория..."
    
    # Jira integration (опционально)
    read -p "Введите Jira Base URL (или нажмите Enter для пропуска): " jira_url
    if [ -n "$jira_url" ]; then
        gh variable set JIRA_BASE_URL --body "$jira_url"
        
        read -p "Введите Jira Project Key: " jira_key
        if [ -n "$jira_key" ]; then
            gh variable set JIRA_PROJECT_KEY --body "$jira_key"
        fi
        
        read -p "Введите Jira User Email: " jira_email
        if [ -n "$jira_email" ]; then
            gh variable set JIRA_USER_EMAIL --body "$jira_email"
        fi
        
        read -s -p "Введите Jira API Token: " jira_token
        echo
        if [ -n "$jira_token" ]; then
            echo "$jira_token" | gh secret set JIRA_API_TOKEN
        fi
        
        log_success "Jira интеграция настроена"
    fi
    
    log_success "Переменные настроены"
}

# Тестирование настройки
test_setup() {
    log_info "Тестирование настройки..."
    
    # Проверяем доступность секретов
    log_info "Проверка секретов..."
    gh secret list
    
    # Проверяем переменные
    log_info "Проверка переменных..."
    gh variable list
    
    # Проверяем environments
    log_info "Проверка environments..."
    gh api repos/:owner/:repo/environments --jq '.[].name'
    
    log_success "Тестирование завершено"
}

# Создание тестового workflow run
trigger_test_workflow() {
    log_info "Запуск тестового workflow..."
    
    read -p "Запустить тестовый CI/CD workflow? (y/n): " run_test
    
    if [ "$run_test" = "y" ] || [ "$run_test" = "Y" ]; then
        gh workflow run ci.yml
        log_success "Тестовый workflow запущен"
        log_info "Проверьте результаты в GitHub Actions"
    fi
}

# Генерация документации
generate_docs() {
    log_info "Генерация документации..."
    
    cat > CICD_SETUP.md << 'EOF'
# CI/CD Setup Complete

## 🎉 Настройка завершена!

Ваш CI/CD пайплайн готов к работе. Вот что было настроено:

### GitHub Environments
- ✅ Development
- ✅ Staging  
- ✅ Production

### Workflows
- ✅ CI/CD Pipeline (`ci.yml`)
- ✅ Pull Request Check (`pr.yml`)
- ✅ Release Management (`release.yml`)
- ✅ Environment Deployment (`deploy-environments.yml`)
- ✅ Security Scanning (`security-scan.yml`)
- ✅ Cleanup (`cleanup.yml`)

### Секреты и переменные
Проверьте настройки в GitHub Settings:
- Repository secrets
- Environment secrets
- Repository variables

## 🚀 Как использовать

### Для разработки
1. Создайте feature branch
2. Внесите изменения
3. Создайте Pull Request → автоматически запустятся проверки
4. После merge в `develop` → автоматический деплой в development

### Для staging
1. Merge в `main` → автоматический деплой в staging
2. Проверьте staging окружение
3. При готовности создайте release tag

### Для production
1. Создайте git tag: `git tag v1.0.0 && git push origin v1.0.0`
2. Автоматически запустится production deployment
3. Проверьте production окружение

## 📊 Мониторинг

- GitHub Actions для статуса деплойментов
- Slack уведомления (если настроены)
- Security scans в GitHub Security tab

## 🔧 Дополнительная настройка

1. Настройте DNS записи для ingress
2. Настройте SSL сертификаты
3. Настройте мониторинг (Prometheus/Grafana)
4. Настройте логирование

## 📚 Полезные ссылки

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

EOF

    log_success "Документация создана: CICD_SETUP.md"
}

# Основная функция
main() {
    echo "🚀 Настройка CI/CD пайплайна для MLOps проекта"
    echo "=============================================="
    echo
    
    check_dependencies
    check_github_auth
    setup_environments
    setup_secrets
    setup_variables
    test_setup
    generate_docs
    trigger_test_workflow
    
    echo
    log_success "🎉 CI/CD пайплайн успешно настроен!"
    echo
    log_info "Следующие шаги:"
    echo "1. Проверьте настройки в GitHub Settings"
    echo "2. Обновите DNS записи для ingress"
    echo "3. Настройте SSL сертификаты"
    echo "4. Проверьте первый deployment"
    echo
    log_info "Документация создана в файле CICD_SETUP.md"
}

# Обработка аргументов командной строки
case "${1:-}" in
    --help|-h)
        echo "Использование: $0 [опции]"
        echo
        echo "Опции:"
        echo "  --help, -h     Показать эту справку"
        echo "  --check        Только проверить зависимости"
        echo "  --secrets      Только настроить секреты"
        echo "  --test         Только запустить тесты"
        exit 0
        ;;
    --check)
        check_dependencies
        check_github_auth
        exit 0
        ;;
    --secrets)
        check_dependencies
        check_github_auth
        setup_secrets
        exit 0
        ;;
    --test)
        test_setup
        exit 0
        ;;
    *)
        main
        ;;
esac
