# IPTVPORTAL JSONSQL API — Полная документация

***

## Протокол и транспорт

JSONSQL API — это протокол взаимодействия IPTVPORTAL с внешними системами, полностью основанный на JSONRPC через HTTPS.

- **Endpoint для команд DML/SQL:**  
  `https://{domain}.admin.iptvportal.ru/api/jsonsql/`
- **Endpoint для авторизации:**  
  `https://{domain}.admin.iptvportal.ru/api/jsonrpc/`
- Все команды требуют заголовок:  
  `Iptvportal-Authorization: sessionid={sid}`  
  где `sid` — идентификатор сессии из успешной авторизации.

***

## Авторизация администратора

### Запрос
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "authorize_user",
  "params": {"username": "admin", "password": "adminpassword"}
}
```
### Ответ
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {"session_id": "sid"}
}
```
### Ошибка
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {"message": "Error message"}
}
```

***

## Поддерживаемые команды DML:
- **SELECT**
- **INSERT**
- **UPDATE**
- **DELETE**

***

## SELECT — Выборка данных

### Формат
```json
{
  "distinct": ...,
  "data": ...,
  "from": ...,
  "where": ...,
  "group_by": ...,
  "order_by": ...,
  "limit": ...,
  "offset": ...
}
```

#### Примеры

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "select",
  "params": {
    "data": ["id", "name", "protocol", "inet_addr", "port"],
    "from": "media",
    "where": {"is": ["is_tv", true]},
    "order_by": "name"
  }
}
```
**SQL-аналог:**
```sql
SELECT id, name, protocol, inet_addr, port
FROM media
WHERE is_tv IS TRUE
ORDER BY name
```

***

## INSERT — Добавление новых данных

### Формат
```json
{
  "into": ...,
  "columns": ...,
  "values": ...,
  "returning": ...
}
```

#### Примеры

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "insert",
  "params": {
    "into": "package",
    "columns": ["name", "paid"],
    "values": [["movie", true], ["sports", true]],
    "returning": "id"
  }
}
```
**SQL-аналог:**
```sql
INSERT INTO package (name, paid) VALUES
  ('movie', true), ('sports', true)
RETURNING id
```

***

## UPDATE — Обновление данных

### Формат
```json
{
  "table": ...,
  "set": ...,
  "where": ...,
  "returning": ...
}
```

#### Примеры

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "update",
  "params": {
    "table": "subscriber",
    "set": {"disabled": true},
    "where": {"eq": ["username", "12345"]},
    "returning": "id"
  }
}
```
**SQL-аналог:**
```sql
UPDATE subscriber SET disabled = TRUE WHERE username = '12345' RETURNING id
```

***

## DELETE — Удаление данных

### Формат
```json
{
  "from": ...,
  "where": ...,
  "returning": ...
}
```

#### Примеры

**Удаление устройств абонента test:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "delete",
  "params": {
    "from": "terminal",
    "where": {
      "in": [
        "subscriber_id",
        {
          "select": {
            "data": "id",
            "from": "subscriber",
            "where": {"eq": ["username", "test"]}
          }
        }
      ]
    },
    "returning": "id"
  }
}
```
**SQL-аналог:**
```sql
DELETE FROM terminal
WHERE subscriber_id IN (
  SELECT id FROM subscriber WHERE username = 'test'
)
RETURNING id
```

***

## Логические и сравнения

- `{ "and": [expr1, expr2, ...] }`  
- `{ "or": [expr1, expr2, ...] }`  
- `{ "not": [expr] }`

**Операции сравнения:**
- `{ "is": [op1, op2] }`
- `{ "is_not": [op1, op2] }`
- `{ "eq": [op1, op2] }`
- `{ "neq": [op1, op2] }`
- `{ "lt": [op1, op2] }`
- `{ "gt": [op1, op2] }`
- `{ "lte": [op1, op2] }`
- `{ "gte": [op1, op2] }`

***

## Математические и строковые функции

- `{ "add": [op1, op2, ...] }`
- `{ "sub": [op1, op2] }`
- `{ "mul": [op1, op2, ...] }`
- `{ "div": [op1, op2] }`
- `{ "mod": [op1, op2] }`
- `{ "like": [field, pattern] }`
- `{ "ilike": [field, pattern] }`
- `{ "regexp_replace": [field, pattern, replacement] }`

**Пример:**
```json
{
  "data": [
    {"function": "regexp_replace", "args": ["tv_channel.name", "\\s\\(.*", ""], "as": "cleared"},
    "name", "id"
  ],
  "from": "tv_channel"
}
```
**SQL-аналог:**
```sql
SELECT regexp_replace(tv_channel.name, '\\s\\(.*', '') AS cleared, name, id FROM tv_channel
```

***

## JOIN, SUBQUERY, GROUP BY

### JOIN через from/join

**Пример JSONSQL JOIN:**
```json
{
  "data": ["a.id", "b.name"],
  "from": [
    {"table": "a", "as": "a"},
    {"join": "b", "as": "b", "on": {"eq": [{"a": "id"}, {"b": "a_id"}]}}
  ]
}
```
**SQL-аналог:**
```sql
SELECT a.id, b.name FROM a JOIN b ON a.id = b.a_id
```

### SUBQUERY в SELECT/FROM/WHERE
- Через вложенные `"select": {...}`

### GROUP BY/ORDER BY
- `"group_by": ["field1", "field2"]`
- `"order_by": ["field1", "DESC"]`

***

## Агрегаты

- `{ "function": "count", "args": ["*"] }` — COUNT(*) в массиве
- `{ "function": "count", "args": "field" }` — COUNT(field) строкой для одного поля
- `{ "function": "distinct", "args": "field" }` — DISTINCT для одного поля
- `{ "function": "distinct", "args": ["field1", "field2"] }` — DISTINCT для нескольких полей
- `{ "function": "avg", ... }`, `{ "function": "max", ... }`, `{ "function": "sum", ... }`

### Примеры агрегатных функций

**COUNT(*) — подсчёт всех строк:**
```json
{
  "data": [{"function": "count", "args": ["*"]}],
  "from": "tv_channel"
}
```
**SQL:** `SELECT COUNT(*) FROM tv_channel`  
**Результат:** `[[7308]]`

**COUNT(field) — подсчёт непустых значений:**
```json
{
  "data": [{"function": "count", "args": "id"}],
  "from": "media"
}
```
**SQL:** `SELECT COUNT(id) FROM media`

**COUNT(DISTINCT field) — подсчёт уникальных значений:**
```json
{
  "data": [
    {
      "function": "count",
      "args": {
        "function": "distinct",
        "args": "mac_addr"
      }
    }
  ],
  "from": "terminal"
}
```
**SQL:** `SELECT COUNT(DISTINCT mac_addr) FROM terminal`

**Несколько агрегатов с алиасами:**
```json
{
  "data": [
    {"function": "count", "args": ["*"], "as": "cnt"},
    {"function": "count", "args": {"function": "distinct", "args": "inet_addr"}, "as": "uniq"}
  ],
  "from": "media"
}
```
**SQL-аналог:**
```sql
SELECT COUNT(*) AS cnt, COUNT(DISTINCT inet_addr) AS uniq
FROM media
```
**Результат:** `[[651232, 14381]]`

### Правила форматирования args

1. **COUNT(\*)** — всегда массив: `["*"]`
2. **Одно поле** — строка: `"field_name"`
3. **Несколько полей** — массив: `["field1", "field2"]`
4. **Вложенные функции** — объект: `{"function": "distinct", "args": "field"}`

***

## Структура основной JSONSQL сущности

- `"data"` — что выбирать или возвращать
- `"from"` — таблицы, join, subquery
- `"where"` — условия
- `"group_by"` — группировка
- `"order_by"` — сортировка
- `"limit"` — лимит
- `"offset"` — смещение

***

## Пример комплексного запроса
**JSONSQL:**
```json
{
  "data": [
    "subscriber.id",
    "subscriber.username",
    {"function": "count", "args": ["terminal.id"], "as": "term_count"}
  ],
  "from": [
    {"table": "subscriber", "as": "subscriber"},
    {"join": "terminal", "as": "terminal", "on": {"eq": [{"subscriber": "id"}, {"terminal": "subscriber_id"}]}}
  ],
  "group_by": ["subscriber.id", "subscriber.username"],
  "order_by": ["term_count", "DESC"],
  "where": {"gt": [{"subscriber": "created_at"}, "2023-01-01 00:00:00"]}
}
```
**SQL-аналог:**
```sql
SELECT
  subscriber.id,
  subscriber.username,
  COUNT(terminal.id) AS term_count
FROM subscriber
JOIN terminal ON subscriber.id = terminal.subscriber_id
WHERE subscriber.created_at > '2023-01-01 00:00:00'
GROUP BY subscriber.id, subscriber.username
ORDER BY term_count DESC
```

***

## Авторизация и работа с API

- Получить `session_id` через метод `authorize_user`
- Передавать его в каждом запросе в заголовке
- Работать с API строго через JSON-RPC 2.0 формат

***

## Полезные ссылки

- [IPTVPORTAL JSONSQL API docs](https://iptvportal.cloud/support/api/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/8.4/interactive/index.html)
- [Примеры production скриптов](http://ftp.iptvportal.cloud/doc/API/examples/)

***

Документация готова для размещения в `docs/jsonsql.md` — с реальными production-паттернами, SQL-аналогами для быстрого старта и интеграции.