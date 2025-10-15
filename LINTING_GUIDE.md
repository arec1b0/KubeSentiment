# Руководство по линтингу и форматированию кода

## Обзор инструментов

В проекте используются следующие инструменты для контроля качества кода:

### 1. **Black** - Автоматический форматтер кода

- **Назначение**: Автоматическое форматирование Python кода в единообразный стиль
- **Конфигурация**: `pyproject.toml`
- **Длина строки**: 100 символов

### 2. **Flake8** - Линтер для проверки стиля и синтаксиса

- **Назначение**: Проверка кода на соответствие PEP 8 и поиск потенциальных ошибок
- **Конфигурация**: `.flake8`
- **Плагины**:
  - `flake8-bugbear` - находит распространенные ошибки
  - `flake8-comprehensions` - улучшает list/dict comprehensions
  - `flake8-simplify` - предлагает упрощения кода

### 3. **isort** - Сортировка импортов

- **Назначение**: Автоматическая сортировка и группировка импортов
- **Конфигурация**: `pyproject.toml`
- **Профиль**: black (совместимость с black)

### 4. **mypy** - Статическая проверка типов

- **Назначение**: Проверка типов Python
- **Настройки**: Игнорирование отсутствующих импортов

### 5. **Bandit** - Проверка безопасности

- **Назначение**: Поиск проблем безопасности в коде
- **Исключения**: Не применяется к тестам

## Установка

### Основные зависимости

```bash
pip install -r requirements.txt
```

### Зависимости для разработки

```bash
pip install -r requirements-dev.txt
```

### Или всё вместе

```bash
make install-dev
```

## Использование

### Проверка кода (без изменений)

```bash
# Все проверки сразу
make lint

# Или по отдельности
black --check app/ tests/        # Проверить форматирование
flake8 app/ tests/               # Проверить стиль и синтаксис
isort --check-only app/ tests/   # Проверить импорты
mypy app/                        # Проверить типы
```

### Автоматическое исправление

```bash
# Форматирование всего кода
make format

# Или автоматическое исправление линтинга
make lint-fix

# Или по отдельности
black app/ tests/                # Отформатировать код
isort app/ tests/                # Отсортировать импорты
```

### Pre-commit hooks (рекомендуется)

Pre-commit автоматически проверяет код перед каждым коммитом:

```bash
# Установка pre-commit хуков
pip install pre-commit
pre-commit install

# Запуск вручную на всех файлах
pre-commit run --all-files

# Pre-commit будет автоматически запускаться при git commit
```

## Конфигурация

### pyproject.toml

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100
```

### .flake8

```ini
[flake8]
max-line-length = 100
max-complexity = 10
extend-ignore = E203, W503, E501
```

## Интеграция с IDE

### VSCode

Добавьте в `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--config=.flake8"],
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--config", "pyproject.toml"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

### PyCharm

1. Настройки → Tools → Black
   - Включить "On code reformat"
   - Включить "On save"
2. Настройки → Tools → External Tools
   - Добавить flake8 и isort

## Игнорирование предупреждений

### В коде (используйте экономно!)

```python
# Игнорировать конкретное правило для одной строки
result = some_complex_function()  # noqa: E501

# Игнорировать для всего файла
# flake8: noqa

# Игнорировать конкретное правило для всего файла
# flake8: noqa: E501
```

### В конфигурации

Редактировать `.flake8` для глобальных исключений:

```ini
per-file-ignores =
    __init__.py:F401
    tests/*:F401,F811
```

## CI/CD интеграция

В CI pipeline линтинг запускается автоматически:

```yaml
# Пример для GitHub Actions
- name: Lint code
  run: make lint
```

## Решение проблем

### Конфликт между Black и Flake8

Конфигурация уже настроена на игнорирование конфликтующих правил:

- E203 (пробелы перед ':')
- W503 (перенос строки перед бинарным оператором)
- E501 (длина строки, управляется Black)

### Исправление всех проблем сразу

```bash
# 1. Отформатировать код
make format

# 2. Проверить оставшиеся проблемы
make lint

# 3. Исправить вручную то, что не может быть исправлено автоматически
```

## Рекомендации

1. **Запускайте линтинг часто**: Лучше исправлять проблемы сразу
2. **Используйте pre-commit**: Автоматизирует проверки
3. **Настройте IDE**: Автоформатирование при сохранении экономит время
4. **Не игнорируйте предупреждения без причины**: Они существуют для улучшения качества кода
5. **Регулярно обновляйте инструменты**: `pip install -U -r requirements-dev.txt`

## Полезные команды

```bash
# Установка
make install-dev              # Установить dev зависимости

# Проверка
make lint                     # Проверить код
make test                     # Запустить тесты

# Форматирование
make format                   # Отформатировать код
make lint-fix                 # Автоисправление

# Pre-commit
pre-commit install           # Установить хуки
pre-commit run --all-files   # Запустить на всех файлах

# Полный цикл CI локально
make all                     # Clean, install, lint, test, build
```

## Дополнительная информация

- [Black документация](https://black.readthedocs.io/)
- [Flake8 документация](https://flake8.pycqa.org/)
- [isort документация](https://pycqa.github.io/isort/)
- [mypy документация](https://mypy.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)
