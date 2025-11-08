# IPTVPortal JSONSQL API Documentation

## Описание протокола

JSONSQL API предоставляет SQL-подобный JSON формат для DML-операций, поддерживает JOIN, GROUP BY, агрегаты и подзапросы, полностью совместим с логикой PostgreSQL.

- Запросы передаются через методы JSONRPC (`select`, `insert`, `update`, `delete`)
- Поддерживаются JOIN всех типов, подзапросы, GROUP BY, агрегаты, математические и строковые функции, WHERE выражения с логическими операторами (and, or, not)

---

## Примеры: JSONSQL vs SQL

### 1. JOIN и выборка (complete_playlog)

**JSONSQL**
```json
{
  "data": [
    {"terminal_playlog": "start", "as": "playlog__start"},
    {"terminal_playlog": "domain_id", "as": "playlog__domain_id"},
    {"terminal_playlog": "mac_addr", "as": "playlog__mac_addr"},
    {"tv_channel": "name", "as": "playlog__channel_name"}
  ],
  "from": [
    {"table": "terminal_playlog", "as": "terminal_playlog"},
    {"join": "tv_channel", "as": "tv_channel", "on": {
      "and": [
        {"eq": [{"tv_channel": "id"}, {"terminal_playlog": "channel_id"}]}
      ]
    }},
    {"join": "tv_program", "as": "tv_program", "on": {
      "and": [
        {"eq": [{"tv_program": "epg_provider_id"}, 36]},
        {"gt": [{"terminal_playlog": "start"}, {"tv_program": "start"}]},
        {"lt": [{"terminal_playlog": "start"}, {"tv_program": "stop"}]},
        {"eq": [{"tv_channel": "id"}, {"tv_program": "channel_id"}]}
      ]
    }},
    {"join": "tv_program_category", "as": "crosscat", "on": {
      "and": [
        {"eq": [{"crosscat": "program_id"}, {"tv_program": "id"}]}
      ]
    }},
    {"join": "tv_category", "as": "tv_category", "on": {
      "and": [
        {"eq": [{"crosscat": "category_id"}, {"tv_category": "id"}]}
      ]
    }}
  ],
  "where": {
    "and": [
      {"gt": [{"terminal_playlog": "start"}, "2020-02-17 00:00:00"]},
      {"lt": [{"terminal_playlog": "start"}, "2020-04-20 00:00:00"]}
    ]
  }
}
```

**SQL**
```sql
SELECT
    tp.start AS playlog__start,
    tp.domain_id AS playlog__domain_id,
    tp.mac_addr AS playlog__mac_addr,
    tc.name AS playlog__channel_name
FROM terminal_playlog tp
JOIN tv_channel tc ON tc.id = tp.channel_id
JOIN tv_program tvp ON
    tvp.epg_provider_id = 36 AND
    tp.start > tvp.start AND
    tp.start < tvp.stop AND
    tc.id = tvp.channel_id
JOIN tv_program_category crosscat ON crosscat.program_id = tvp.id
JOIN tv_category tcat ON crosscat.category_id = tcat.id
WHERE
    tp.start > '2020-02-17 00:00:00' AND
    tp.start < '2020-04-20 00:00:00'
```

---

### 2. Агрегат с подзапросом (aggr_playlog)

**JSONSQL**
```json
{
  "data": [
    {"function": "count", "args": ["*"], "as": "rowcount"},
    {"function": "count", "args": {"function": "distinct", "args": {"q": "playlog__mac_addr"}}, "as": "uniques"}
  ],
  "from": [
    {"select": complete_playlog, "as": "q"}
  ]
}
```
**SQL**
```sql
SELECT
    COUNT(*) AS rowcount,
    COUNT(DISTINCT q.playlog__mac_addr) AS uniques
FROM (
    -- inner SQL is previous JOIN example
) AS q
```

---

### 3. Подзапросы в WHERE (example delete)

**JSONSQL**
```json
{
  "from": "terminal",
  "where": {
    "in": ["subscriber_id", {
      "select": {
        "data": "id",
        "from": "subscriber",
        "where": {"eq": ["username", "test"]}
      }
    }]
  }
}
```
**SQL**
```sql
DELETE FROM terminal
WHERE subscriber_id IN (
    SELECT id FROM subscriber WHERE username = 'test'
)
```

---

### 4. Применение функций и фильтров

**JSONSQL**
```json
{
  "data": [
    {"function": "regexp_replace", "args": ["tv_channel.name", "\\s\\(.*", ""], "as": "cleared"},
    "name",
    "id"
  ],
  "from": "tv_channel"
}
```
**SQL**
```sql
SELECT
    REGEXP_REPLACE(tv_channel.name, '\s\(.*', '') AS cleared,
    name,
    id
FROM tv_channel
```

---

### Операторные конструкции

- **AND, OR, NOT:** `{ "and": [expr1, expr2] }` аналогично SQL-выражениям
- **JOINs:** `{ "join": ... }` с условием `