# 📊 Примеры использования системы бенчмаркинга

## 🚀 Базовые сценарии

### 1. Быстрый тест для разработки
```bash
# Простой тест с минимальными настройками
./quick-benchmark.sh -t cpu-small -u 5 -d 30

# Результат: быстрая оценка производительности за 30 секунд
```

### 2. Тест для staging окружения
```bash
# Средняя нагрузка на 2 минуты
./quick-benchmark.sh -t cpu-medium -u 20 -d 120

# Проверка стабильности под нагрузкой
```

### 3. Production readiness тест
```bash
# Высокая нагрузка на 10 минут
./quick-benchmark.sh -t cpu-large -u 100 -d 600

# Полная оценка готовности к production
```

## 🎯 Специализированные тесты

### GPU vs CPU сравнение
```bash
# Тест CPU инстанса
./quick-benchmark.sh -t cpu-large -u 50 -d 300

# Тест GPU инстанса с той же нагрузкой
./quick-benchmark.sh -t gpu-t4 -u 50 -d 300

# Сравните результаты в HTML отчетах
```

### Тест масштабируемости
```bash
# Постепенное увеличение нагрузки
for users in 10 20 50 100 200; do
    ./quick-benchmark.sh -t cpu-medium -u $users -d 120
    sleep 60  # Пауза между тестами
done
```

### Стресс-тест
```bash
# Максимальная нагрузка для поиска пределов
./quick-benchmark.sh -t gpu-v100 -u 500 -d 600
```

## 📈 Анализ результатов

### Интерпретация метрик

#### Отличная производительность
- **RPS > 100**
- **P95 latency < 200ms**
- **Error rate < 1%**
- **CPU utilization < 70%**

#### Приемлемая производительность
- **RPS 50-100**
- **P95 latency < 500ms**
- **Error rate < 5%**
- **CPU utilization < 85%**

#### Требует оптимизации
- **RPS < 50**
- **P95 latency > 500ms**
- **Error rate > 5%**
- **CPU utilization > 90%**

### Анализ стоимости

#### Экономичные варианты
```bash
# Для небольших нагрузок (< 20 RPS)
Рекомендация: cpu-small или cpu-medium
Стоимость: $0.01-0.03 за 1000 предсказаний
```

#### Сбалансированные варианты
```bash
# Для средних нагрузок (20-100 RPS)
Рекомендация: cpu-large или gpu-t4
Стоимость: $0.03-0.08 за 1000 предсказаний
```

#### Высокопроизводительные варианты
```bash
# Для высоких нагрузок (> 100 RPS)
Рекомендация: gpu-v100 или gpu-a100
Стоимость: $0.08-0.15 за 1000 предсказаний
```

## 🔧 Кастомизация тестов

### Изменение тестовых данных
```python
# Отредактируйте scripts/load-test.py
test_texts = [
    "Ваш кастомный текст для тестирования",
    "Другой пример текста",
    # ... добавьте свои тексты
]
```

### Настройка метрик
```yaml
# Отредактируйте configs/benchmark-config.yaml
benchmark:
  metrics:
    latency_percentiles: [50, 90, 95, 99, 99.9]
    resource_sampling_interval: 5
```

### Добавление новых инстансов
```yaml
# В configs/benchmark-config.yaml
instances:
  cpu:
    - name: "my-custom-instance"
      type: "c5.4xlarge"
      vcpu: 16
      memory: "32Gi"
      cost_per_hour: 0.768
```

## 📊 Автоматизация

### Еженедельный бенчмарк
```bash
#!/bin/bash
# weekly-benchmark.sh

# Запуск полного бенчмарка каждую неделю
./scripts/deploy-benchmark.sh

# Отправка результатов в Slack
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"Weekly benchmark completed. Check results at: '$(pwd)'/results/"}' \
    YOUR_SLACK_WEBHOOK_URL
```

### CI/CD интеграция
```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmark
on:
  schedule:
    - cron: '0 2 * * 1'  # Каждый понедельник в 2:00

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        cd benchmarking
        pip install -r requirements.txt
    - name: Run benchmark
      run: |
        cd benchmarking
        ./quick-benchmark.sh -t cpu-medium -u 20 -d 300
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmarking/results/
```

## 🚨 Troubleshooting

### Проблема: Высокая латентность
```bash
# Проверьте ресурсы
kubectl top pods -n mlops-benchmark

# Увеличьте ресурсы в deployment
kubectl patch deployment mlops-sentiment-cpu -n mlops-benchmark -p '{"spec":{"template":{"spec":{"containers":[{"name":"mlops-sentiment","resources":{"limits":{"cpu":"4000m","memory":"8Gi"}}}]}}}}'
```

### Проблема: Высокий error rate
```bash
# Проверьте логи
kubectl logs -l app=mlops-sentiment -n mlops-benchmark --tail=100

# Уменьшите нагрузку
./quick-benchmark.sh -t cpu-medium -u 10 -d 60
```

### Проблема: GPU не доступен
```bash
# Проверьте GPU ноды
kubectl get nodes -l accelerator=nvidia-tesla-t4

# Установите NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.1/nvidia-device-plugin.yml
```

## 📋 Чеклист перед production

### Обязательные тесты
- [ ] Тест базовой функциональности (30 сек, 5 пользователей)
- [ ] Тест стабильности (10 мин, 20 пользователей)
- [ ] Тест масштабируемости (различное количество пользователей)
- [ ] Стресс-тест (максимальная нагрузка)
- [ ] Тест восстановления после сбоя

### Анализ результатов
- [ ] P95 latency < 500ms
- [ ] Error rate < 5%
- [ ] CPU utilization < 85%
- [ ] Memory utilization < 80%
- [ ] Стоимость в рамках бюджета

### Настройка мониторинга
- [ ] Алерты на высокую латентность
- [ ] Алерты на высокий error rate
- [ ] Алерты на высокое потребление ресурсов
- [ ] Дашборды в Grafana
- [ ] Логирование настроено

## 🎯 Рекомендации по оптимизации

### Для улучшения латентности
1. Используйте GPU инстансы для больших моделей
2. Настройте model caching
3. Оптимизируйте размер батча
4. Используйте ONNX Runtime

### Для снижения стоимости
1. Выберите минимально достаточный тип инстанса
2. Настройте автомасштабирование
3. Используйте spot instances для dev/test
4. Оптимизируйте использование ресурсов

### Для повышения стабильности
1. Настройте health checks
2. Используйте circuit breakers
3. Настройте retry logic
4. Мониторьте все ключевые метрики
