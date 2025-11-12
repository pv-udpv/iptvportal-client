# Руководство по тестированию исправлений логирования

## Проблема (до исправления)

При каждом запуске CLI команды появлялось **3 дублирующихся предупреждения**:
```bash
WARNING:iptvportal:Failed to apply advanced logging config; using basicConfig
WARNING:iptvportal:Failed to apply advanced logging config; using basicConfig
WARNING:iptvportal:Failed to apply advanced logging config; using basicConfig
```

## Решение

**PR #73** устраняет проблему через:
1. Идемпотентную реализацию `setup_logging()`
2. Удаление автоинициализации из `__init__.py`
3. Явную инициализацию в `cli/__main__.py`

## Подготовка к тестированию

```bash
cd ~/iptvportal-client
git fetch origin
git checkout fix/logging-duplicate-warnings
git pull origin fix/logging-duplicate-warnings

# Убедитесь что окружение активно
source .venv/bin/activate  # или ваш метод активации
```

## Тесты

### ✅ Тест 1: Базовая команда SQL

```bash
uv run iptvportal jsonsql sql --query "SELECT * FROM subscriber LIMIT 5"
```

**Ожидаемый результат:**
```
INFO:iptvportal:Logging configured
INFO:httpx:HTTP Request: POST https://...
<таблица с результатами>
```

**НЕ должно быть:**
- Дублирующихся WARNING сообщений
- Множественных "Logging configured" сообщений

---

### ✅ Тест 2: Флаг --log-level

```bash
# DEBUG уровень
uv run iptvportal --log-level DEBUG jsonsql sql -q "SELECT * FROM subscriber LIMIT 2"

# WARNING уровень
uv run iptvportal --log-level WARNING jsonsql sql -q "SELECT * FROM subscriber LIMIT 2"
```

**Проверка**: Уровень логирования должен измениться соответственно.

---

### ✅ Тест 3: Флаг -v (verbose для конкретного модуля)

```bash
# Включить DEBUG для core.client
uv run iptvportal -v iptvportal.core.client jsonsql sql -q "SELECT * FROM subscriber LIMIT 2"

# Включить DEBUG для httpx (покажет детали HTTP запросов)
uv run iptvportal -v httpx jsonsql sql -q "SELECT * FROM subscriber LIMIT 2"
```

**Проверка**: Должны появиться DEBUG сообщения от указанных модулей.

---

### ✅ Тест 4: Флаг -q (quiet для конкретного модуля)

```bash
# Отключить INFO сообщения от httpx
uv run iptvportal -q httpx jsonsql sql -q "SELECT * FROM subscriber LIMIT 2"
```

**Проверка**: HTTP запросы httpx не должны логироваться на уровне INFO.

---

### ✅ Тест 5: Schema команды

```bash
# Список схем
uv run iptvportal jsonsql schema list

# Показать конкретную схему
uv run iptvportal jsonsql schema show subscriber

# Импорт схемы (если есть файл)
uv run iptvportal jsonsql schema import config/schemas.yaml
```

**Проверка**: Команды выполняются без дублирующихся warnings.

---

### ✅ Тест 6: Auth команды

```bash
# Статус аутентификации
uv run iptvportal jsonsql auth status

# Логин (если нужно)
uv run iptvportal jsonsql auth login
```

**Проверка**: Auth работает корректно.

---

### ✅ Тест 7: Transpile команда

```bash
uv run iptvportal jsonsql transpile "SELECT * FROM users WHERE id = 1"

uv run iptvportal jsonsql transpile "SELECT c.name, p.title FROM tv_channel c JOIN tv_program p ON c.id = p.channel_id LIMIT 10"
```

**Проверка**: SQL корректно транспилируется в JSONSQL.

---

### ✅ Тест 8: Config команды

```bash
# Показать конфигурацию
uv run iptvportal config show

# Показать конкретный раздел
uv run iptvportal config show logging
```

**Проверка**: Конфигурация отображается корректно.

---

### ✅ Тест 9: Использование как библиотеки

```bash
# Запустить тестовый скрипт
uv run python test_logging_fix.py
```

**Ожидаемый вывод:**
```
================================================================================
Testing IPTVPortal Logging Configuration
================================================================================

[Test 1] Importing iptvportal package...
✓ Package imported successfully
  Version: 0.1.0

[Test 2] Calling setup_logging() explicitly...
INFO:iptvportal:Logging configured
✓ First setup_logging() call completed

[Test 3] Testing idempotency (multiple setup_logging() calls)...
✓ Second setup_logging() call completed
✓ Third setup_logging() call completed
✓ Fourth setup_logging() call completed
  → No errors, no duplicate warnings

[Test 4] Checking logging configuration state...
✓ is_logging_configured() = True

[Test 5] Creating logger and logging test messages...
INFO:test_script:This is an INFO message
WARNING:test_script:This is a WARNING message
✓ Logger created and messages logged

[Test 6] Testing force reconfiguration...
INFO:iptvportal:Logging configured
✓ Force reconfiguration completed

================================================================================
All tests completed successfully! ✓
================================================================================
```

---

### ✅ Тест 10: Множественные команды подряд

```bash
# Запустить несколько команд подряд
uv run iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 1"
uv run iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 1"
uv run iptvportal jsonsql schema list
uv run iptvportal config show
```

**Проверка**: Каждая команда должна показывать только **одно** сообщение `INFO:iptvportal:Logging configured`.

---

## Критерии успеха

### ✅ Обязательные критерии:

- [ ] При запуске любой CLI команды показывается **ТОЛЬКО ОДНО** сообщение:
  ```
  INFO:iptvportal:Logging configured
  ```

- [ ] **НЕТ** дублирующихся WARNING сообщений:
  ```
  WARNING:iptvportal:Failed to apply advanced logging config; using basicConfig
  ```

- [ ] CLI флаги работают корректно:
  - [ ] `--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL`
  - [ ] `-v <module>` (verbose для модуля)
  - [ ] `-q <module>` (quiet для модуля)

- [ ] Все команды работают без ошибок:
  - [ ] `iptvportal jsonsql sql`
  - [ ] `iptvportal jsonsql schema list/show`
  - [ ] `iptvportal jsonsql auth status`
  - [ ] `iptvportal jsonsql transpile`
  - [ ] `iptvportal config show`

- [ ] Использование как библиотеки работает:
  - [ ] `test_logging_fix.py` выполняется без ошибок
  - [ ] Явный вызов `setup_logging()` работает
  - [ ] Повторные вызовы `setup_logging()` безопасны

### ✅ Дополнительные проверки:

- [ ] `is_logging_configured()` возвращает `True` после инициализации
- [ ] `setup_logging(force=True)` работает для реконфигурации
- [ ] Логирование работает в многопоточном окружении
- [ ] Нет регрессий в существующем функционале

---

## Проблемы и решения

### Если всё ещё появляются warnings:

1. **Очистите кеш Python:**
   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
   find . -type f -name "*.pyc" -delete
   ```

2. **Переустановите пакет:**
   ```bash
   uv pip uninstall iptvportal-client
   uv pip install -e .
   ```

3. **Проверьте что вы на правильной ветке:**
   ```bash
   git branch --show-current
   # Должно показать: fix/logging-duplicate-warnings
   ```

### Если тест test_logging_fix.py не работает:

```bash
# Проверьте зависимости
uv pip list | grep iptvportal

# Убедитесь что используется локальная версия
uv run python -c "import iptvportal; print(iptvportal.__file__)"
```

---

## После успешного тестирования

1. **Merge Pull Request #73** в main
2. **Закрыть issue #70**
3. **Обновить CHANGELOG.md**:
   ```markdown
   ## [Unreleased]
   
   ### Fixed
   - Fixed duplicate logging warnings on CLI startup (#70, #73)
   - Made setup_logging() idempotent with global state tracking
   - Removed auto-initialization from package import
   ```

4. **Удалить тестовый скрипт** (опционально):
   ```bash
   git rm test_logging_fix.py
   git commit -m "chore: Remove temporary test script"
   ```

---

## Контакты

Если возникнут проблемы при тестировании:
- Создайте комментарий в PR #73
- Или откройте новый issue с описанием проблемы

---

**Версия документа**: 1.0  
**Дата**: 2025-11-12  
**Автор**: AI Assistant  
**PR**: #73  
**Issue**: #70
