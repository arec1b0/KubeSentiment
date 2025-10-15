# ⚡ Быстрая справка - Линтинг и форматирование

## 🚀 Самые важные команды

```powershell
# === УСТАНОВКА ===
make install-dev              # Установить все инструменты

# === ФОРМАТИРОВАНИЕ (изменяет файлы) ===
make format                   # Отформатировать весь код
black app/ tests/             # Только Black
isort app/ tests/             # Только isort

# === ПРОВЕРКА (без изменений) ===
make lint                     # Все проверки сразу
black --check app/            # Проверить форматирование
flake8 app/                   # Проверить стиль PEP 8
mypy app/                     # Проверить типы

# === PRE-COMMIT ===
pre-commit install            # Установить (один раз)
pre-commit run --all-files    # Проверить все файлы

# === КОМБО ===
make all                      # Clean + install + lint + test + build
```

## 📁 Главные файлы

| Файл | Что настраивает |
|------|----------------|
| `pyproject.toml` | Black, isort, pytest, mypy, bandit |
| `.flake8` | Flake8 (стиль кода) |
| `.pre-commit-config.yaml` | Автоматические проверки |
| `requirements-dev.txt` | Инструменты разработки |

## 🎯 Workflow

```
1. Пишу код →
2. Сохраняю (Ctrl+S) → VSCode автоформатирует →
3. Перед коммитом: make lint →
4. git commit → pre-commit автоматически запустится →
5. ✅ Готово!
```

## ⚙️ Настройки

- **Длина строки**: 100 символов
- **Python**: 3.11+
- **Стиль**: PEP 8 + Black

## 📚 Документация

- [CODE_QUALITY_SETUP.md](./CODE_QUALITY_SETUP.md) - Полная инструкция
- [LINTING_GUIDE.md](./LINTING_GUIDE.md) - Подробный гайд
- [SETUP_LINTING.md](./SETUP_LINTING.md) - Быстрый старт

## ✨ Первый запуск

```powershell
# 1. Установка
make install-dev

# 2. Настройка pre-commit
pre-commit install

# 3. Форматирование существующего кода
make format

# 4. Проверка
make lint

# 5. Готово! 🎉
```
