# 🚀 CI/CD Pipeline Documentation

Полностью автоматизированный CI/CD пайплайн для MLOps Sentiment Analysis Service.

## 📋 Обзор

Этот пайплайн обеспечивает полную автоматизацию от `git push` до работающего пода в Kubernetes без ручного вмешательства.

### 🔄 Workflow Схема

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   Feature   │───▶│ Pull Request │───▶│    Main     │───▶│  Production  │
│   Branch    │    │   (Tests)    │    │  (Staging)  │    │   (Release)  │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   Dev Deploy         Code Quality        Staging Deploy     Prod Deploy
   (develop)          Security Scan       Integration Tests  Blue-Green
```

## 🛠️ Компоненты пайплайна

### 1. **Main CI/CD Pipeline** (`ci.yml`)

- **Триггеры**: Push в `main`/`develop`, теги `v*`, PR
- **Этапы**:
  - 🧪 Тестирование (Python 3.9, 3.10, 3.11)
  - 🔍 Качество кода (Black, isort, flake8, mypy)
  - 🐳 Сборка и публикация Docker образов
  - 🔒 Сканирование безопасности
  - 🚀 Автоматическое развертывание по окружениям

### 2. **Pull Request Workflow** (`pr.yml`)

- **Быстрые проверки** для PR без развертывания
- **Валидация** Docker сборки
- **Проверка** Kubernetes манифестов
- **Комментарии** с результатами в PR

### 3. **Release Management** (`release.yml`)

- **Автоматическое создание** GitHub releases
- **Подпись контейнеров** с cosign
- **Blue-Green развертывание** в production
- **Комплексная валидация** production

### 4. **Multi-Environment Deployment** (`deploy-environments.yml`)

- **Переиспользуемый** workflow для развертывания
- **Конфигурация** под каждое окружение
- **Автоматическая** проверка здоровья сервиса

### 5. **Security Scanning** (`security-scan.yml`)

- **Ежедневное** сканирование безопасности
- **CodeQL** анализ кода
- **Trivy** сканирование контейнеров
- **Поиск секретов** в коде

### 6. **Cleanup Automation** (`cleanup.yml`)

- **Еженедельная** очистка старых артефактов
- **Удаление** неиспользуемых Docker образов
- **Очистка** workflow runs

## 🌍 Окружения

### Development

- **Ветка**: `develop`
- **Ресурсы**: Минимальные (1 replica, 250m CPU, 512Mi RAM)
- **Автодеплой**: ✅ Автоматический
- **Review**: ❌ Не требуется
- **URL**: `https://dev-sentiment-api.yourdomain.com`

### Staging  

- **Ветка**: `main`
- **Ресурсы**: Средние (2 replicas, 500m CPU, 1Gi RAM)
- **Автодеплой**: ✅ Автоматический
- **Review**: ✅ 1 reviewer
- **URL**: `https://staging-sentiment-api.yourdomain.com`

### Production

- **Теги**: `v*.*.*`
- **Ресурсы**: Максимальные (3 replicas, 1000m CPU, 2Gi RAM)
- **Автодеплой**: ✅ После staging
- **Review**: ✅ 2 reviewers + 10 min задержка
- **URL**: `https://sentiment-api.yourdomain.com`

## 🔐 Безопасность

### Container Security

- **Multi-stage** Docker builds
- **Non-root** пользователь
- **Security updates** в base образе
- **Подпись образов** с cosign
- **Vulnerability scanning** с Trivy

### Code Security

- **Static analysis** с CodeQL
- **Dependency scanning** с Safety
- **Secret detection** с TruffleHog
- **License compliance** проверки

### Kubernetes Security

- **Security contexts**
- **Resource limits**
- **Network policies** (рекомендуется)
- **Pod security standards**

## 📊 Мониторинг и алерты

### GitHub Actions

- **Workflow статусы**
- **Deployment статусы**
- **Security scan результаты**

### Slack Integration

- **Deployment уведомления**
- **Failure алерты**
- **Security инциденты**

### Kubernetes Monitoring

- **Health checks** (`/health`, `/metrics`)
- **Readiness/Liveness** probes
- **HPA** автоскейлинг
- **Resource monitoring**

## 🚀 Использование

### Быстрый старт

1. **Клонируйте репозиторий**

```bash
git clone <repository-url>
cd mlops-sentiment
```

2. **Настройте секреты** (см. `.github/SECRETS.md`)

```bash
# Автоматическая настройка (Linux/macOS)
./scripts/setup-cicd.sh

# Или вручную через GitHub UI
```

3. **Создайте feature branch**

```bash
git checkout -b feature/new-feature
# Внесите изменения
git push origin feature/new-feature
```

4. **Создайте Pull Request**
   - Автоматически запустятся проверки
   - После review merge в `develop`

### Development Workflow

```bash
# Создание feature
git checkout -b feature/sentiment-improvements
git push origin feature/sentiment-improvements
# → Создать PR → Автоматические проверки

# Merge в develop
# → Автоматический деплой в development

# Тестирование в dev
curl https://dev-sentiment-api.yourdomain.com/health
```

### Staging Workflow

```bash
# Merge в main
git checkout main
git merge develop
git push origin main
# → Автоматический деплой в staging

# Проверка staging
curl https://staging-sentiment-api.yourdomain.com/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Great service!"}'
```

### Production Release

```bash
# Создание release
git tag v1.2.3
git push origin v1.2.3
# → Автоматический production деплой

# Проверка production
curl https://sentiment-api.yourdomain.com/health
```

## 🔧 Настройка

### Обязательные секреты

```bash
# Kubernetes configs (base64 encoded)
KUBE_CONFIG_DEV
KUBE_CONFIG_STAGING  
KUBE_CONFIG_PROD

# Container signing
COSIGN_PRIVATE_KEY
COSIGN_PASSWORD

# Notifications
SLACK_WEBHOOK_URL
```

### Опциональные интеграции

```bash
# Jira
JIRA_API_TOKEN
JIRA_BASE_URL (variable)
JIRA_PROJECT_KEY (variable)

# Security
SNYK_TOKEN
SECURITY_SLACK_WEBHOOK
```

### Настройка DNS

```bash
# Добавьте A записи для ingress
dev-sentiment-api.yourdomain.com    → <dev-ingress-ip>
staging-sentiment-api.yourdomain.com → <staging-ingress-ip>
sentiment-api.yourdomain.com        → <prod-ingress-ip>
```

## 🐛 Troubleshooting

### Частые проблемы

#### 1. Deployment fails with "ImagePullBackOff"

```bash
# Проверьте права доступа к registry
kubectl get secret regcred -n mlops-sentiment -o yaml

# Проверьте существование образа
docker pull ghcr.io/your-org/mlops-sentiment:tag
```

#### 2. Health check fails

```bash
# Проверьте логи пода
kubectl logs -n mlops-sentiment deployment/sentiment-service

# Проверьте ресурсы
kubectl describe pod -n mlops-sentiment -l app=sentiment-service
```

#### 3. Tests fail in CI

```bash
# Запустите локально
pytest tests/ -v --cov=app

# Проверьте зависимости
pip install -r requirements.txt
```

### Отладка

```bash
# Проверка статуса workflow
gh run list --workflow=ci.yml

# Просмотр логов
gh run view <run-id> --log

# Проверка секретов
gh secret list

# Проверка environments
gh api repos/:owner/:repo/environments
```

## 📈 Метрики и KPI

### Deployment Metrics

- **Deployment frequency**: Ежедневно
- **Lead time**: < 30 минут
- **MTTR**: < 15 минут  
- **Change failure rate**: < 5%

### Quality Metrics

- **Test coverage**: > 80%
- **Security vulnerabilities**: 0 critical/high
- **Code quality**: Все проверки проходят

## 🔄 Continuous Improvement

### Планируемые улучшения

- [ ] **Canary deployments** для production
- [ ] **Automated rollback** по метрикам
- [ ] **Performance testing** в pipeline
- [ ] **Infrastructure as Code** с Terraform
- [ ] **GitOps** с ArgoCD

### Feedback Loop

1. **Мониторинг** метрик production
2. **Анализ** инцидентов и проблем
3. **Улучшение** pipeline и процессов
4. **Документирование** изменений

## 📚 Дополнительные ресурсы

- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/security-hardening-for-github-actions)
- [Kubernetes Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [MLOps Best Practices](https://ml-ops.org/)

---

## 🤝 Поддержка

Для вопросов и предложений:

- 📧 Email: <devops@company.com>
- 💬 Slack: #mlops-support
- 🐛 Issues: GitHub Issues
- 📖 Wiki: Internal documentation

**Создано с ❤️ командой DevOps**
