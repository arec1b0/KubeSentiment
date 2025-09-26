# 🚀 MLOps Sentiment Analysis - Quick Start

## ⚡ Быстрый запуск (5 минут)

### 1️⃣ Предварительные требования
```bash
# Проверьте, что у вас есть:
kubectl version --client  # Kubernetes CLI
helm version              # Helm package manager
```

### 2️⃣ Клонирование репозитория
```bash
git clone https://github.com/arec1b0/mlops-sentiment.git
cd mlops-sentiment
```

### 3️⃣ Запуск полной системы мониторинга
```bash
# Сделайте скрипт исполняемым
chmod +x scripts/setup-monitoring.sh

# Запустите полную настройку (займет 5-10 минут)
./scripts/setup-monitoring.sh
```

### 4️⃣ Доступ к интерфейсам

После успешной установки:

```bash
# Grafana (дашборды и визуализация)
kubectl port-forward -n monitoring svc/prometheus-operator-grafana 3000:80
# Откройте: http://localhost:3000 (admin/admin123)

# Prometheus (метрики и алерты)
kubectl port-forward -n monitoring svc/prometheus-operator-kube-p-prometheus 9090:9090
# Откройте: http://localhost:9090

# MLOps API (сам сервис)
kubectl port-forward -n mlops-sentiment svc/mlops-sentiment 8080:80
# Тест: curl http://localhost:8080/health
```

## 🎯 Что вы получите

### 📊 Мониторинг
- **Grafana дашборды** с метриками производительности
- **Prometheus алерты** для критичных проблем
- **SLO/SLI метрики** (доступность 99.9%, латентность <200ms)
- **ML-специфичные метрики** (уверенность модели, время инференса)

### 🔒 Безопасность
- **NetworkPolicy** - строгая изоляция сетевого трафика
- **RBAC** - минимальные права доступа
- **Security Context** - запуск без root прав
- **Secrets management** - безопасное хранение ключей

### 🚀 Развертывание
- **Helm чарты** - упаковка всех компонентов
- **Multi-environment** - dev/staging/prod конфигурации
- **Auto-scaling** - HPA на основе CPU/Memory
- **Rolling updates** - обновления без простоя

### 🚨 Алертинг
- **Slack уведомления** - интеграция с командными каналами
- **Email алерты** - для критичных проблем
- **PagerDuty** - эскалация для production
- **Умная маршрутизация** - разные каналы для разных типов алертов

## 🧪 Тестирование

```bash
# Проверка здоровья сервиса
curl http://localhost:8080/health

# Тест API предсказаний
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this monitoring system!"}'

# Просмотр метрик
curl http://localhost:8080/metrics

# Проверка логов
kubectl logs -f -n mlops-sentiment -l app.kubernetes.io/name=mlops-sentiment
```

## 🔧 Управление

```bash
# Масштабирование
kubectl scale deployment mlops-sentiment --replicas=5 -n mlops-sentiment

# Обновление
helm upgrade mlops-sentiment ./helm/mlops-sentiment -n mlops-sentiment --set image.tag=v1.1.0

# Статус
./scripts/setup-monitoring.sh status

# Полное удаление
./scripts/setup-monitoring.sh cleanup
```

## 📈 Дашборды Grafana

После входа в Grafana найдите:

1. **MLOps Sentiment Analysis** - основной дашборд
2. **MLOps Sentiment Analysis - Advanced** - расширенные метрики
3. **Kubernetes / Compute Resources / Pod** - ресурсы подов
4. **Prometheus / Overview** - статус Prometheus

## 🚨 Алерты

Система автоматически настроит алерты для:

- 🔴 **Critical**: Сервис недоступен, модель не загружена
- 🟡 **Warning**: Высокая латентность, использование ресурсов
- 🔵 **Info**: Аномалии трафика, неэффективность ресурсов

## 🆘 Помощь

```bash
# Проверка статуса всех компонентов
kubectl get all -n monitoring
kubectl get all -n mlops-sentiment

# Просмотр событий
kubectl get events --sort-by=.metadata.creationTimestamp

# Логи мониторинга
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana
```

## 📚 Дальнейшее чтение

- [MONITORING.md](MONITORING.md) - Полная документация по мониторингу
- [DEVELOPMENT.md](DEVELOPMENT.md) - Руководство разработчика
- [KUBERNETES.md](KUBERNETES.md) - Kubernetes развертывание

---

**🎉 Поздравляем! Ваша MLOps система с полным мониторингом готова к работе!**
