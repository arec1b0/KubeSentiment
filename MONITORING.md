# 📊 MLOps Sentiment Analysis - Monitoring & Observability

## 🎯 Обзор

Эта система мониторинга обеспечивает полную наблюдаемость MLOps сервиса анализа тональности с помощью современного стека:

- **Prometheus** - сбор метрик и алертинг
- **Grafana** - визуализация и дашборды
- **Alertmanager** - управление уведомлениями
- **NetworkPolicy** - безопасность сетевого трафика
- **Helm** - упаковка и развертывание

## 🏗️ Архитектура мониторинга

```mermaid
graph TB
    subgraph "MLOps Application"
        APP[Sentiment Service]
        APP --> METRICS[/metrics endpoint]
    end
    
    subgraph "Monitoring Stack"
        PROM[Prometheus]
        GRAF[Grafana]
        AM[Alertmanager]
        
        METRICS --> PROM
        PROM --> GRAF
        PROM --> AM
    end
    
    subgraph "Notifications"
        SLACK[Slack]
        EMAIL[Email]
        PD[PagerDuty]
        
        AM --> SLACK
        AM --> EMAIL
        AM --> PD
    end
    
    subgraph "Security"
        NP[NetworkPolicy]
        NP -.-> APP
        NP -.-> PROM
        NP -.-> GRAF
    end
```

## 🚀 Быстрый старт

### Предварительные требования

```bash
# Установка необходимых инструментов
kubectl version --client
helm version
```

### Развертывание с Helm

```bash
# Клонируйте репозиторий
git clone https://github.com/arec1b0/mlops-sentiment.git
cd mlops-sentiment

# Развертывание в dev окружении
./scripts/deploy-helm.sh

# Или развертывание в production
ENVIRONMENT=prod IMAGE_TAG=v1.0.0 ./scripts/deploy-helm.sh
```

### Доступ к интерфейсам

```bash
# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80
# Откройте http://localhost:3000 (admin/admin123)

# Prometheus
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
# Откройте http://localhost:9090

# Alertmanager
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093
# Откройте http://localhost:9093
```

## 📊 Дашборды Grafana

### Основной дашборд
- **URL**: `/d/mlops-sentiment/mlops-sentiment-analysis`
- **Метрики**: Базовые метрики производительности
- **Обновление**: 30 секунд

### Продвинутый дашборд
- **URL**: `/d/mlops-sentiment-advanced/mlops-sentiment-analysis-advanced`
- **Метрики**: SLO/SLI, предиктивная аналитика
- **Обновление**: 30 секунд

### Ключевые панели

1. **Service Availability** - SLO 99.9%
2. **Request Latency** - SLO 95% < 200ms
3. **ML Prediction Confidence** - SLO >80%
4. **Resource Utilization** - CPU/Memory
5. **Error Rate Distribution** - 2xx/4xx/5xx
6. **Active Alerts** - Текущие проблемы

## 🚨 Система алертинг

### Категории алертов

#### 🔴 Critical (Критичные)
- `MLOpsServiceDown` - Сервис недоступен
- `MLOpsModelNotLoaded` - ML модель не загружена
- `MLOpsPodCrashLooping` - Поды перезапускаются
- `MLOpsSLOAvailabilityBreach` - Нарушение SLO доступности

#### 🟡 Warning (Предупреждения)
- `MLOpsHighLatency` - Высокая задержка
- `MLOpsHighErrorRate` - Высокий процент ошибок
- `MLOpsHighCPUUsage` - Высокое использование CPU
- `MLOpsLowPredictionConfidence` - Низкая уверенность ML модели

#### 🔵 Info (Информационные)
- `MLOpsResourceInefficiency` - Неэффективное использование ресурсов
- `MLOpsTrafficSpike` - Всплеск трафика

### Каналы уведомлений

```yaml
# Slack каналы
#critical-alerts    - Критичные проблемы
#alerts            - Обычные предупреждения
#ml-alerts         - ML-специфичные проблемы
#security          - Проблемы безопасности
#performance       - Проблемы производительности

# Email
oncall@company.com     - Критичные алерты
ml-team@company.com    - ML проблемы
security@company.com   - Безопасность

# PagerDuty
Критичные алерты автоматически создают инциденты
```

## 🔒 Безопасность (NetworkPolicy)

### Принципы безопасности

1. **Deny by Default** - Запрет всего трафика по умолчанию
2. **Least Privilege** - Минимальные необходимые права
3. **Explicit Allow** - Явное разрешение нужных соединений

### Разрешенные соединения

```yaml
# Ingress (входящий трафик)
✅ Ingress Controller → MLOps Service (8000)
✅ Prometheus → MLOps Service (8000) для метрик
✅ MLOps Service ↔ MLOps Service (межподовое общение)

# Egress (исходящий трафик)
✅ MLOps Service → DNS (53)
✅ MLOps Service → HTTPS (443) для загрузки моделей
✅ MLOps Service → Monitoring (9090, 9093, 3000)
❌ Все остальное - ЗАПРЕЩЕНО
```

### Проверка NetworkPolicy

```bash
# Просмотр активных политик
kubectl get networkpolicy -n mlops-sentiment

# Тестирование соединений
kubectl exec -it deployment/mlops-sentiment -n mlops-sentiment -- curl -m 5 google.com
# Должно быть заблокировано

kubectl exec -it deployment/mlops-sentiment -n mlops-sentiment -- curl -m 5 prometheus:9090
# Должно работать
```

## 📈 SLO/SLI Метрики

### Service Level Objectives

| Метрика | SLO | Измерение | Алерт |
|---------|-----|-----------|-------|
| **Availability** | 99.9% | `(1 - error_rate) * 100` | < 99.9% за 5 мин |
| **Latency** | 95% < 200ms | `histogram_quantile(0.95, ...)` | > 200ms за 10 мин |
| **ML Quality** | Confidence > 80% | `avg(prediction_confidence)` | < 80% за 15 мин |

### Пользовательские метрики

```python
# Примеры метрик в коде приложения
from prometheus_client import Counter, Histogram, Gauge

# Счетчики
prediction_total = Counter('mlops_predictions_total', 'Total predictions')
model_load_total = Counter('mlops_model_loads_total', 'Model load attempts')

# Гистограммы
inference_duration = Histogram('mlops_inference_duration_seconds', 'Inference time')
prediction_confidence = Histogram('mlops_prediction_confidence', 'Prediction confidence')

# Индикаторы
model_loaded = Gauge('mlops_model_loaded', 'Model load status')
cache_size = Gauge('mlops_cache_size', 'Prediction cache size')
```

## 🛠️ Операционные процедуры

### Развертывание обновлений

```bash
# Обновление приложения
helm upgrade mlops-sentiment ./helm/mlops-sentiment \
  --namespace mlops-sentiment \
  --set image.tag=v1.1.0 \
  --wait

# Проверка развертывания
kubectl rollout status deployment/mlops-sentiment -n mlops-sentiment
```

### Масштабирование

```bash
# Ручное масштабирование
kubectl scale deployment mlops-sentiment --replicas=10 -n mlops-sentiment

# Настройка HPA
kubectl patch hpa mlops-sentiment -n mlops-sentiment -p '{"spec":{"maxReplicas":20}}'
```

### Отладка проблем

```bash
# Просмотр логов
kubectl logs -f deployment/mlops-sentiment -n mlops-sentiment

# Проверка метрик
kubectl port-forward svc/mlops-sentiment 8080:80 -n mlops-sentiment
curl http://localhost:8080/metrics

# Проверка здоровья
curl http://localhost:8080/health
```

### Резервное копирование

```bash
# Экспорт конфигурации Helm
helm get values mlops-sentiment -n mlops-sentiment > backup-values.yaml

# Экспорт дашбордов Grafana
kubectl get configmap -n monitoring -l grafana_dashboard=1 -o yaml > grafana-dashboards-backup.yaml

# Экспорт правил Prometheus
kubectl get prometheusrule -n monitoring -o yaml > prometheus-rules-backup.yaml
```

## 🔧 Настройка и кастомизация

### Изменение алертов

1. Отредактируйте `helm/mlops-sentiment/templates/prometheusrule.yaml`
2. Примените изменения:
```bash
helm upgrade mlops-sentiment ./helm/mlops-sentiment -n mlops-sentiment
```

### Добавление новых дашбордов

1. Создайте JSON файл дашборда в Grafana UI
2. Добавьте его в `helm/mlops-sentiment/templates/grafana-dashboard.yaml`
3. Примените изменения

### Настройка уведомлений

1. Отредактируйте `monitoring/alertmanager-config.yaml`
2. Обновите секрет:
```bash
kubectl apply -f monitoring/alertmanager-config.yaml
```

## 🐛 Устранение неполадок

### Частые проблемы

#### Prometheus не собирает метрики
```bash
# Проверка ServiceMonitor
kubectl get servicemonitor -n mlops-sentiment

# Проверка endpoints
kubectl get endpoints -n mlops-sentiment

# Проверка targets в Prometheus UI
# Targets → http://prometheus:9090/targets
```

#### Grafana не показывает данные
```bash
# Проверка datasource
kubectl logs -n monitoring deployment/grafana

# Проверка подключения к Prometheus
kubectl exec -n monitoring deployment/grafana -- curl prometheus:9090/api/v1/query?query=up
```

#### Алерты не срабатывают
```bash
# Проверка правил
kubectl get prometheusrule -n monitoring

# Проверка Alertmanager
kubectl logs -n monitoring deployment/alertmanager
```

### Логи и диагностика

```bash
# Все компоненты мониторинга
kubectl get all -n monitoring

# Статус Helm релизов
helm list -A

# События кластера
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 📚 Дополнительные ресурсы

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Helm Documentation](https://helm.sh/docs/)
- [SLO/SLI Best Practices](https://sre.google/sre-book/service-level-objectives/)

## 🤝 Поддержка

Для получения помощи:
1. Проверьте [Issues](https://github.com/arec1b0/mlops-sentiment/issues)
2. Создайте новый Issue с подробным описанием проблемы
3. Приложите логи и конфигурации

---

**Создано с ❤️ для MLOps команды**
