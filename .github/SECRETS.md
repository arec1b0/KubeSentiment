# GitHub Secrets Configuration Guide

Этот документ описывает все необходимые секреты и переменные для работы CI/CD пайплайна.

## 🔐 Repository Secrets

### Обязательные секреты

#### Kubernetes Configuration

```
KUBE_CONFIG_DEV      # Base64-encoded kubeconfig для development окружения
KUBE_CONFIG_STAGING  # Base64-encoded kubeconfig для staging окружения  
KUBE_CONFIG_PROD     # Base64-encoded kubeconfig для production окружения
```

**Как получить:**

```bash
# Получить kubeconfig и закодировать в base64
cat ~/.kube/config | base64 -w 0
```

#### Container Signing (опционально, но рекомендуется)

```
COSIGN_PRIVATE_KEY   # Приватный ключ для подписи Docker образов
COSIGN_PASSWORD      # Пароль для приватного ключа cosign
```

**Как создать:**

```bash
# Генерация ключей для cosign
cosign generate-key-pair
# Сохранить содержимое cosign.key в COSIGN_PRIVATE_KEY
# Сохранить пароль в COSIGN_PASSWORD
```

### Интеграции (опционально)

#### Slack Notifications

```
SLACK_WEBHOOK_URL    # Webhook URL для уведомлений в Slack
```

#### Jira Integration

```
JIRA_API_TOKEN       # API токен для интеграции с Jira
```

## 🌍 Repository Variables

### Общие переменные

```
JIRA_BASE_URL        # URL Jira инстанса (например: https://company.atlassian.net)
JIRA_USER_EMAIL      # Email пользователя Jira
JIRA_PROJECT_KEY     # Ключ проекта в Jira (например: MLOPS)
```

## 🏢 Environment Secrets

Секреты, специфичные для каждого окружения (настраиваются в Settings > Environments):

### Development Environment

- `KUBE_CONFIG`: Kubeconfig для dev кластера
- `SLACK_WEBHOOK_URL`: Webhook для dev уведомлений

### Staging Environment  

- `KUBE_CONFIG`: Kubeconfig для staging кластера
- `SLACK_WEBHOOK_URL`: Webhook для staging уведомлений

### Production Environment

- `KUBE_CONFIG`: Kubeconfig для prod кластера
- `SLACK_WEBHOOK_URL`: Webhook для prod уведомлений

## 📋 Настройка Environments

1. Перейдите в `Settings > Environments`
2. Создайте три окружения:
   - `development`
   - `staging`
   - `production`

3. Для каждого окружения настройте:
   - **Protection rules**: Требование review для production
   - **Environment secrets**: Соответствующие KUBE_CONFIG
   - **Deployment branches**: Ограничения по веткам

### Пример настройки Protection Rules

#### Development

- Deployment branches: `develop`
- Required reviewers: 0

#### Staging  

- Deployment branches: `main`
- Required reviewers: 1

#### Production

- Deployment branches: `main`, tags `v*`
- Required reviewers: 2
- Wait timer: 5 minutes

## 🔧 Автоматическая настройка секретов

Создайте скрипт для автоматической настройки:

```bash
#!/bin/bash
# setup-secrets.sh

# Установка GitHub CLI если не установлен
if ! command -v gh &> /dev/null; then
    echo "Please install GitHub CLI first"
    exit 1
fi

# Аутентификация
gh auth login

# Установка Kubernetes секретов
echo "Setting up Kubernetes secrets..."
gh secret set KUBE_CONFIG_DEV < ~/.kube/config-dev
gh secret set KUBE_CONFIG_STAGING < ~/.kube/config-staging  
gh secret set KUBE_CONFIG_PROD < ~/.kube/config-prod

# Установка Slack webhook (замените на свой URL)
read -p "Enter Slack Webhook URL: " SLACK_URL
gh secret set SLACK_WEBHOOK_URL -b "$SLACK_URL"

# Генерация cosign ключей
echo "Generating cosign keys..."
cosign generate-key-pair
gh secret set COSIGN_PRIVATE_KEY < cosign.key
read -s -p "Enter cosign key password: " COSIGN_PASS
gh secret set COSIGN_PASSWORD -b "$COSIGN_PASS"

# Очистка временных файлов
rm -f cosign.key cosign.pub

echo "✅ Secrets setup completed!"
```

## 🔍 Проверка конфигурации

Используйте этот workflow для проверки настроек:

```yaml
name: Verify Secrets
on:
  workflow_dispatch:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
    - name: Check required secrets
      run: |
        secrets_ok=true
        
        # Проверяем наличие обязательных секретов
        if [ -z "${{ secrets.KUBE_CONFIG_DEV }}" ]; then
          echo "❌ KUBE_CONFIG_DEV is missing"
          secrets_ok=false
        fi
        
        if [ -z "${{ secrets.KUBE_CONFIG_STAGING }}" ]; then
          echo "❌ KUBE_CONFIG_STAGING is missing"  
          secrets_ok=false
        fi
        
        if [ -z "${{ secrets.KUBE_CONFIG_PROD }}" ]; then
          echo "❌ KUBE_CONFIG_PROD is missing"
          secrets_ok=false
        fi
        
        if [ "$secrets_ok" = true ]; then
          echo "✅ All required secrets are configured"
        else
          echo "❌ Some secrets are missing"
          exit 1
        fi
```

## 🔄 Ротация секретов

Регулярно обновляйте секреты:

1. **Kubernetes configs**: При обновлении кластеров
2. **API токены**: Каждые 90 дней
3. **Cosign ключи**: Каждые 365 дней

## 📚 Дополнительные ресурсы

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Environment Protection Rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)
