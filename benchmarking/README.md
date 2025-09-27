# 🚀 MLOps Sentiment Analysis - Benchmarking Framework

## 📊 Обзор

Комплексная система бенчмаркинга для тестирования производительности модели анализа тональности на различных типах инстансов (CPU и GPU).

## 🎯 Цели бенчмаркинга

- **Измерение латентности** - время отклика на запросы
- **Тестирование RPS** - количество запросов в секунду
- **Мониторинг ресурсов** - утилизация CPU, GPU, памяти
- **Расчет стоимости** - стоимость 1000 предсказаний для каждого типа инстанса

## 🏗️ Структура проекта

```
benchmarking/
├── configs/                    # Конфигурации для разных типов инстансов
│   ├── cpu-instances.yaml
│   ├── gpu-instances.yaml
│   └── benchmark-config.yaml
├── scripts/                    # Скрипты для бенчмаркинга
│   ├── load-test.py           # Нагрузочное тестирование
│   ├── resource-monitor.py    # Мониторинг ресурсов
│   ├── cost-calculator.py     # Расчет стоимости
│   └── deploy-benchmark.sh    # Автоматическое развертывание
├── deployments/               # Kubernetes манифесты
│   ├── cpu-deployment.yaml
│   ├── gpu-deployment.yaml
│   └── monitoring.yaml
├── results/                   # Результаты бенчмарков
│   ├── reports/
│   ├── metrics/
│   └── charts/
└── requirements.txt           # Python зависимости
```

## 🚀 Быстрый запуск

### 1. Установка зависимостей
```bash
cd benchmarking
pip install -r requirements.txt

# Сделайте скрипты исполняемыми (Linux/macOS)
chmod +x scripts/*.sh
chmod +x quick-benchmark.sh
```

### 2. Быстрый тест одного инстанса
```bash
# Простой тест с настройками по умолчанию
./quick-benchmark.sh

# Тест с кастомными параметрами
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# Тест GPU инстанса
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300
```

### 3. Полный бенчмарк всех инстансов
```bash
# Автоматический бенчмарк на всех типах инстансов
./scripts/deploy-benchmark.sh

# С кастомными параметрами
./scripts/deploy-benchmark.sh --namespace my-benchmark --results-dir ./my-results
```

### 4. Ручной запуск отдельных компонентов
```bash
# Только нагрузочное тестирование
python scripts/load-test.py --instance-type cpu-small --users 10 --duration 60

# Только мониторинг ресурсов
python scripts/resource-monitor.py --duration 300 --namespace mlops-benchmark

# Только расчет стоимости
python scripts/cost-calculator.py --results results/benchmark_results.json
```

## 📈 Метрики

### Производительность
- **Latency P50/P95/P99** - процентили времени отклика
- **RPS (Requests Per Second)** - пропускная способность
- **Throughput** - количество обработанных запросов

### Ресурсы
- **CPU Utilization** - использование процессора
- **GPU Utilization** - использование GPU (для GPU инстансов)
- **Memory Usage** - потребление памяти
- **Network I/O** - сетевой трафик

### Стоимость
- **Cost per 1000 predictions** - стоимость 1000 предсказаний
- **Cost per hour** - почасовая стоимость
- **Cost efficiency** - соотношение производительность/стоимость

## 🔧 Конфигурация

Основные параметры в `configs/benchmark-config.yaml`:

```yaml
benchmark:
  duration: 300s              # Длительность теста
  concurrent_users: [1, 5, 10, 20, 50, 100]  # Количество одновременных пользователей
  ramp_up_time: 30s          # Время нарастания нагрузки
  
instances:
  cpu:
    - type: "t3.medium"
    - type: "c5.large"
    - type: "c5.xlarge"
  gpu:
    - type: "p3.2xlarge"
    - type: "g4dn.xlarge"
    
costs:
  # Стоимость инстансов в USD/час (AWS)
  t3.medium: 0.0416
  c5.large: 0.096
  c5.xlarge: 0.192
  p3.2xlarge: 3.06
  g4dn.xlarge: 0.526
```

## 📊 Отчеты

После завершения бенчмарка будут созданы:

1. **HTML отчет** - интерактивные графики и таблицы
2. **JSON метрики** - сырые данные для дальнейшего анализа
3. **CSV файлы** - данные для импорта в Excel/Google Sheets
4. **Grafana дашборд** - реальное время мониторинга

## 🎯 Примеры использования

### Сравнение CPU vs GPU
```bash
python scripts/load-test.py --compare-instances --output results/cpu-vs-gpu.json
```

### Тест масштабируемости
```bash
python scripts/load-test.py --scalability-test --max-users 200
```

### Анализ стоимости
```bash
python scripts/cost-calculator.py --predictions 1000000 --report results/cost-analysis.html
```
