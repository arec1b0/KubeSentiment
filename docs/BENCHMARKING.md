# 🚀 MLOps Sentiment Analysis - Benchmarking Guide

## 📊 Обзор

Комплексная система бенчмаркинга для тестирования производительности модели анализа тональности на различных типах инстансов (CPU и GPU). Этот модуль позволяет:

- **Измерить производительность** - латентность, RPS, throughput
- **Проанализировать стоимость** - стоимость 1000 предсказаний для каждого типа инстанса
- **Мониторить ресурсы** - утилизация CPU, GPU, памяти во время нагрузки
- **Сравнить инстансы** - выбрать оптимальный тип для ваших требований

## 🎯 Цели бенчмаркинга

### Производительность
- ⚡ **Латентность** - время отклика на запросы (P50, P95, P99)
- 🚀 **RPS** - количество запросов в секунду
- 📊 **Throughput** - общая пропускная способность
- ❌ **Error Rate** - процент неуспешных запросов

### Ресурсы
- 🖥️ **CPU Utilization** - использование процессора
- 💾 **Memory Usage** - потребление памяти
- 🎮 **GPU Utilization** - использование GPU (для GPU инстансов)
- 🌐 **Network I/O** - сетевой трафик

### Стоимость
- 💰 **Cost per 1000 predictions** - основная метрика стоимости
- ⏰ **Cost per hour** - почасовая стоимость инстанса
- 📈 **Cost efficiency** - соотношение производительность/стоимость

## 🚀 Быстрый старт

### 1. Простой тест
```bash
cd benchmarking

# Установка зависимостей
pip install -r requirements.txt

# Быстрый тест с настройками по умолчанию
./quick-benchmark.sh
```

### 2. Тест конкретного инстанса
```bash
# CPU инстанс с 20 пользователями на 2 минуты
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# GPU инстанс с высокой нагрузкой
./quick-benchmark.sh -t gpu-t4 -u 100 -d 300
```

### 3. Полный бенчмарк всех инстансов
```bash
# Автоматическое тестирование всех типов инстансов
./scripts/deploy-benchmark.sh
```

## 📋 Поддерживаемые типы инстансов

### CPU Инстансы
| Тип | vCPU | Memory | Стоимость/час | Рекомендации |
|-----|------|--------|---------------|--------------|
| `cpu-small` (t3.medium) | 2 | 4GB | $0.0416 | Разработка, тестирование |
| `cpu-medium` (c5.large) | 2 | 4GB | $0.096 | Небольшая нагрузка |
| `cpu-large` (c5.xlarge) | 4 | 8GB | $0.192 | Средняя нагрузка |
| `cpu-xlarge` (c5.2xlarge) | 8 | 16GB | $0.384 | Высокая нагрузка |

### GPU Инстансы
| Тип | GPU | vCPU | Memory | Стоимость/час | Рекомендации |
|-----|-----|------|--------|---------------|--------------|
| `gpu-t4` (g4dn.xlarge) | T4 | 4 | 16GB | $0.526 | Инференс, средняя нагрузка |
| `gpu-v100` (p3.2xlarge) | V100 | 8 | 61GB | $3.06 | Высокопроизводительный инференс |
| `gpu-a100` (p4d.xlarge) | A100 | 4 | 96GB | $3.912 | Максимальная производительность |

## 📊 Интерпретация результатов

### Метрики производительности

#### Латентность
- **P50 < 100ms** - отличная производительность
- **P95 < 200ms** - хорошая производительность  
- **P99 < 500ms** - приемлемая производительность
- **P99 > 1000ms** - требует оптимизации

#### RPS (Requests Per Second)
- **< 10 RPS** - низкая производительность
- **10-50 RPS** - средняя производительность
- **50-100 RPS** - хорошая производительность
- **> 100 RPS** - отличная производительность

#### Error Rate
- **< 1%** - отличная стабильность
- **1-5%** - приемлемая стабильность
- **> 5%** - требует исследования

### Анализ стоимости

#### Стоимость 1000 предсказаний
- **< $0.01** - очень экономично
- **$0.01-0.05** - экономично
- **$0.05-0.10** - умеренно
- **> $0.10** - дорого

#### Эффективность
Рассчитывается как: `(RPS × Latency_Score) / Cost_per_Hour`

## 🎯 Рекомендации по выбору инстанса

### Для разработки и тестирования
```bash
# Рекомендуется: cpu-small
./quick-benchmark.sh -t cpu-small -u 5 -d 60
```
- ✅ Низкая стоимость
- ✅ Достаточно для разработки
- ❌ Ограниченная производительность

### Для production с низкой нагрузкой (< 20 RPS)
```bash
# Рекомендуется: cpu-medium
./quick-benchmark.sh -t cpu-medium -u 20 -d 300
```
- ✅ Хорошее соотношение цена/производительность
- ✅ Стабильная работа
- ✅ Возможность автомасштабирования

### Для production со средней нагрузкой (20-100 RPS)
```bash
# Рекомендуется: cpu-large или gpu-t4
./quick-benchmark.sh -t cpu-large -u 50 -d 300
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300
```
- ✅ Высокая производительность
- ✅ Низкая латентность
- ⚠️ Средняя стоимость

### Для production с высокой нагрузкой (> 100 RPS)
```bash
# Рекомендуется: gpu-v100 или gpu-a100
./quick-benchmark.sh -t gpu-v100 -u 100 -d 600
```
- ✅ Максимальная производительность
- ✅ Минимальная латентность
- ❌ Высокая стоимость

## 📈 Мониторинг и алерты

### Рекомендуемые алерты
```yaml
# Prometheus alerts
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  
- alert: HighErrorRate  
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05

- alert: LowThroughput
  expr: rate(http_requests_total[5m]) < 10
```

### Grafana дашборды
После бенчмарка импортируйте дашборды из `results/grafana_dashboards/`

## 🔧 Настройка и кастомизация

### Изменение параметров тестирования
Отредактируйте `configs/benchmark-config.yaml`:

```yaml
benchmark:
  load_test:
    duration: 300  # Длительность теста в секундах
    concurrent_users: [1, 5, 10, 20, 50, 100]  # Количество пользователей
    
instances:
  cpu:
    - name: "my-custom-cpu"
      type: "c5.4xlarge"
      cost_per_hour: 0.768
```

### Добавление новых типов инстансов
1. Обновите `configs/benchmark-config.yaml`
2. Создайте соответствующие Kubernetes манифесты в `deployments/`
3. Запустите бенчмарк

## 📁 Структура результатов

После выполнения бенчмарка в директории `results/` будут созданы:

```
results/
├── benchmark_*.json              # Результаты нагрузочного тестирования
├── resource_metrics_*.json       # Метрики использования ресурсов
├── cost_analysis.json           # Анализ стоимости
├── consolidated_results.json    # Сводные результаты
├── reports/                     # Графики и визуализация
│   ├── benchmark_report_*.png
│   └── cost_performance_*.png
├── cost_reports/               # Отчеты по стоимости
│   ├── cost_analysis.png
│   └── cost_performance_bubble.png
└── benchmark_final_report.md   # Итоговый отчет
```

## 🚨 Troubleshooting

### Проблема: "No connection to Kubernetes cluster"
```bash
# Проверьте подключение к кластеру
kubectl cluster-info

# Настройте kubeconfig
export KUBECONFIG=/path/to/your/kubeconfig
```

### Проблема: "GPU not available"
```bash
# Проверьте наличие GPU нод
kubectl get nodes -l accelerator=nvidia-tesla-t4

# Установите NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
```

### Проблема: "High error rate during testing"
1. Проверьте логи приложения: `kubectl logs -l app=mlops-sentiment`
2. Увеличьте ресурсы в deployment
3. Уменьшите количество одновременных пользователей

## 🔗 Интеграция с CI/CD

### GitHub Actions
```yaml
name: Performance Benchmark
on:
  schedule:
    - cron: '0 2 * * 1'  # Каждый понедельник в 2:00

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Benchmark
      run: |
        cd benchmarking
        ./quick-benchmark.sh -t cpu-medium -u 20 -d 120
    - name: Upload Results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmarking/results/
```

## 📚 Дополнительные ресурсы

- [Основная документация проекта](../README.md)
- [Руководство по развертыванию](../deployment-guide.md)
- [Архитектура системы](../docs/architecture.md)
- [Troubleshooting](../docs/troubleshooting/index.md)
- [OpenAPI спецификация](../openapi-specs/sentiment-api.yaml)

---

**Следующие шаги:**
1. Запустите быстрый бенчмарк: `./quick-benchmark.sh`
2. Проанализируйте результаты в HTML отчете
3. Выберите оптимальный тип инстанса для ваших требований
4. Настройте production deployment с выбранными параметрами
