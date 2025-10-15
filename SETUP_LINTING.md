# 🚀 Быстрая настройка линтинга и форматирования

## Что было настроено

В проекте KubeSentiment теперь настроены профессиональные инструменты для контроля качества кода:

### ✅ Инструменты

1. **Black** - автоматическое форматирование кода
2. **Flake8** - проверка синтаксиса и стиля (PEP 8)
3. **isort** - сортировка импортов
4. **mypy** - проверка типов
5. **Bandit** - проверка безопасности
6. **Pre-commit** - автоматические проверки перед коммитом

### 📁 Созданные файлы

- `pyproject.toml` - центральная конфигурация (black, isort, pytest, mypy, bandit)
- `.flake8` - конфигурация flake8
- `requirements-dev.txt` - зависимости для разработки
- `.pre-commit-config.yaml` - настройка pre-commit хуков
- `.editorconfig` - универсальные настройки редактора
- `.vscode/settings.json` - настройки VSCode
- `.vscode/extensions.json` - рекомендуемые расширения VSCode
- `LINTING_GUIDE.md` - подробное руководство

## ⚡ Быстрый старт

### Шаг 1: Установка зависимостей

```bash
# Установить все зависимости разработки
make install-dev

# Или вручную
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Шаг 2: Проверка кода

```bash
# Запустить все проверки
make lint

# Выход будет содержать результаты:
# - Black: проверка форматирования
# - isort: проверка импортов
# - Flake8: проверка стиля и синтаксиса
# - mypy: проверка типов
```

### Шаг 3: Автоматическое исправление

```bash
# Автоматически отформатировать весь код
make format

# Или
make lint-fix
```

### Шаг 4: Настройка Pre-commit (рекомендуется)

```bash
# Установить pre-commit хуки
pre-commit install

# Теперь при каждом git commit автоматически будет:
# ✓ Форматироваться код
# ✓ Проверяться стиль
# ✓ Валидироваться YAML/JSON
# ✓ Проверяться безопасность
```

### Шаг 5: Запуск вручную

```bash
# Проверить все файлы с pre-commit
pre-commit run --all-files

# Проверить только измененные файлы
pre-commit run
```

## 🔧 Использование отдельных инструментов

### Black (форматирование)

```bash
# Проверить форматирование
black --check app/ tests/

# Отформатировать код
black app/ tests/

# Отформатировать один файл
black app/main.py
```

### Flake8 (линтинг)

```bash
# Проверить весь проект
flake8 app/ tests/

# Проверить один файл
flake8 app/main.py

# Показать статистику
flake8 --statistics app/
```

### isort (импорты)

```bash
# Проверить импорты
isort --check-only app/ tests/

# Исправить импорты
isort app/ tests/

# Показать diff без изменений
isort --diff app/
```

### mypy (типы)

```bash
# Проверить типы
mypy app/

# Проверить с подробным выводом
mypy app/ --show-error-codes --pretty
```

## 📝 Конфигурация

### Основные параметры

- **Длина строки**: 100 символов (настроено в black и flake8)
- **Отступы**: 4 пробела для Python
- **Кодировка**: UTF-8
- **Окончания строк**: LF (Unix-style)

### Игнорируемые правила Flake8

```ini
E203  # пробелы перед ':' (конфликт с black)
W503  # перенос строки перед оператором (конфликт с black)
E501  # длина строки (управляется black)
```

### Сложность кода

- **Максимальная цикломатическая сложность**: 10
- Flake8 предупредит о слишком сложных функциях

## 💻 Интеграция с VSCode

### Рекомендуемые расширения

Откройте палитру команд (Ctrl+Shift+P) и выберите:
`Extensions: Show Recommended Extensions`

Установите:

- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Flake8 (ms-python.flake8)
- Mypy Type Checker (ms-python.mypy-type-checker)

### Автоматическое форматирование

После установки расширений:

1. Код будет автоматически форматироваться при сохранении (Ctrl+S)
2. Импорты будут автоматически сортироваться
3. Ошибки линтинга будут подсвечиваться в реальном времени

## 🎯 Рабочий процесс

### Ежедневная работа

```bash
# 1. Написать код
# 2. Сохранить файл (VSCode автоматически отформатирует)
# 3. Проверить перед коммитом
make lint

# 4. Если есть ошибки - исправить автоматически
make format

# 5. Сделать коммит (pre-commit автоматически запустится)
git add .
git commit -m "feat: add new feature"
```

### Перед Pull Request

```bash
# Запустить все проверки
make lint
make test

# Или полный CI цикл локально
make all
```

## 🔍 Примеры

### Пример форматирования Black

**До:**

```python
def my_function(x,y,z):
    result=x+y+z
    return result
```

**После:**

```python
def my_function(x, y, z):
    result = x + y + z
    return result
```

### Пример сортировки isort

**До:**

```python
import sys
from app.config import settings
import os
from typing import List
```

**После:**

```python
import os
import sys
from typing import List

from app.config import settings
```

### Пример проверки Flake8

```python
# Ошибка: неиспользуемая переменная
def calculate(x, y):
    z = 10  # F841: local variable 'z' is assigned to but never used
    return x + y

# Ошибка: слишком сложная функция
def complex_function(a, b, c, d, e):  # C901: too complex (11)
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return True
    return False
```

## 🐛 Решение проблем

### Конфликт между инструментами

Конфигурация уже настроена на устранение конфликтов между black и flake8.

### Pre-commit не работает

```bash
# Переустановить хуки
pre-commit uninstall
pre-commit install

# Очистить кеш
pre-commit clean
```

### Слишком много ошибок

```bash
# Исправить автоматически всё, что возможно
make format

# Затем проверить оставшиеся ошибки
make lint

# Оставшиеся ошибки нужно исправить вручную
```

## 📚 Дополнительные ресурсы

- [Подробное руководство](./LINTING_GUIDE.md)
- [Black документация](https://black.readthedocs.io/)
- [Flake8 документация](https://flake8.pycqa.org/)
- [PEP 8 Style Guide](https://pep8.org/)

## ✨ Полезные команды

```bash
# Установка
make install-dev              # Установить dev зависимости

# Проверка
make lint                     # Проверить код (без изменений)
make lint-fix                 # Автоисправление

# Форматирование
make format                   # Отформатировать код

# Тестирование
make test                     # Запустить тесты

# Pre-commit
pre-commit install            # Установить хуки
pre-commit run --all-files    # Проверить все файлы

# Очистка
make clean                    # Удалить кеш и артефакты

# Полный цикл
make all                      # Clean + install + lint + test + build
```

## 🎉 Готово

Теперь ваш код будет:

- ✅ Автоматически форматироваться
- ✅ Соответствовать PEP 8
- ✅ Иметь правильную сортировку импортов
- ✅ Проверяться на безопасность
- ✅ Валидироваться перед каждым коммитом

**Следующий шаг**: Запустите `make format` чтобы отформатировать весь существующий код!
