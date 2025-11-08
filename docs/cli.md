# IPTVPortal CLI Documentation

Comprehensive guide to using the IPTVPortal command-line interface.

## Installation

```bash
# Install with CLI support
pip install iptvportal-client[cli]

# Or with uv
uv pip install iptvportal-client[cli]
```

## Quick Start

```bash
# 1. Initialize configuration
iptvportal config init

# 2. Test authentication
iptvportal auth

# 3. Run your first SQL query
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5"

# Or use native JSONSQL
iptvportal jsonsql select --from subscriber --limit 5
 
# (New) Schema mapping ON by default: column names shown using schema (auto-generated if missing)
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5"               # mapped
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" --no-map-schema  # disable mapping
iptvportal jsonsql select --from subscriber --limit 5                # mapped
iptvportal jsonsql select --from subscriber --limit 5 --no-map-schema # disable mapping
```

## Configuration

### Initialize Configuration (Interactive)

```bash
iptvportal config init
```

This wizard will prompt you for:
- Operator domain
- Admin username
- Admin password
- Optional settings (timeout, retries, SSL verification)

Creates a `.env` file in the current directory.

### Show Current Configuration

```bash
iptvportal config show
```

Displays all configuration values in a table format.

### Set Individual Values

```bash
iptvportal config set domain operator
iptvportal config set username admin
iptvportal config set timeout 60
iptvportal config set max_retries 5
```

### Get Individual Values

```bash
iptvportal config get domain
iptvportal config get timeout
```

## Authentication

### Check Authentication Status

```bash
iptvportal auth
```

Shows:
- Domain and username
- Auth and API URLs
- Session ID (after successful connection)
- Connection status

### Force Re-authentication

```bash
iptvportal auth --renew
```

## Query Commands

The CLI provides two separate subapps for queries:

1. **`iptvportal sql`** - Execute SQL queries (auto-transpiled to JSONSQL)
2. **`iptvportal jsonsql`** - Execute native JSONSQL queries with subcommands

### SQL Subapp

Execute SQL queries that are automatically transpiled to JSONSQL.

#### Basic Usage

```bash
# Direct query with --query or -q
iptvportal sql -q "SELECT * FROM subscriber LIMIT 10"

# Multi-line query
iptvportal sql --query "
  SELECT id, username, email 
  FROM subscriber 
  WHERE disabled = false 
  LIMIT 20
"

# Open editor to write query
iptvportal sql --edit
iptvportal sql -e
```

#### Output Formats

```bash
# Table format (default)
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5"

# JSON format
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" --format json
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" -f json

# YAML format
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" -f yaml
```

#### Dry-Run Mode

Preview the transpiled JSONSQL without executing:

```bash
iptvportal sql -q "SELECT * FROM subscriber WHERE disabled = false" --dry-run
```

Shows:
- Original SQL query
- Transpiled JSONSQL
- Complete JSON-RPC request
- "Query will NOT be executed" message

#### Show Request Mode

Execute query and show both the request and result:

```bash
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" --show-request
```

Shows:
- JSON-RPC request sent to API
- Query result

#### SQL Examples

```bash
# Simple SELECT
iptvportal sql -q "SELECT * FROM subscriber LIMIT 10"

# With WHERE clause
iptvportal sql -q "SELECT id, username FROM subscriber WHERE disabled = false"

# With JOIN
iptvportal sql -q "
  SELECT s.username, COUNT(t.id) as device_count 
  FROM subscriber s 
  JOIN terminal t ON s.id = t.subscriber_id 
  GROUP BY s.username
"

# Complex JOIN with EPG data
iptvportal sql -q "
  SELECT 
    c.name AS channel,
    p.title AS program,
    cat.name AS category,
    cat.genre AS genre
  FROM tv_program p
  JOIN tv_channel c ON p.channel_id = c.id
  JOIN tv_program_category pc ON pc.program_id = p.id
  JOIN tv_category cat ON pc.category_id = cat.id
  WHERE p.epg_provider_id = 36
  LIMIT 10
"

# INSERT
iptvportal sql -q "INSERT INTO package (name, paid) VALUES ('Premium', true) RETURNING id"

# UPDATE
iptvportal sql -q "UPDATE subscriber SET disabled = true WHERE username = 'test' RETURNING id"

# DELETE
iptvportal sql -q "DELETE FROM terminal WHERE id = 123 RETURNING id"

# Aggregate functions
iptvportal sql -q "SELECT COUNT(*) FROM media"
iptvportal sql -q "SELECT COUNT(id) FROM subscriber"
iptvportal sql -q "SELECT COUNT(DISTINCT inet_addr) FROM media"

# Complex aggregates
iptvportal sql -q "
  SELECT 
    COUNT(*) AS total_count, 
    COUNT(DISTINCT inet_addr) AS unique_addrs 
  FROM media
"

# Group by with aggregates
iptvportal sql -q "
  SELECT subscriber_id, COUNT(*) as device_count 
  FROM terminal 
  GROUP BY subscriber_id 
  ORDER BY device_count DESC
"
```

#### Aggregate Function Details

The SQL transpiler properly handles aggregate functions with optimal JSONSQL format:

**COUNT(\*)** - Counts all rows (uses array format per JSONSQL spec):
```bash
iptvportal sql -q "SELECT COUNT(*) FROM tv_channel" --dry-run
# Transpiles to: {"function": "count", "args": ["*"]}
```

**COUNT(field)** - Counts non-null values in a specific field (uses string format):
```bash
iptvportal sql -q "SELECT COUNT(id) FROM media" --dry-run
# Transpiles to: {"function": "count", "args": "id"}
```

**COUNT(DISTINCT field)** - Counts unique values (uses nested function format):
```bash
iptvportal sql -q "SELECT COUNT(DISTINCT mac_addr) FROM terminal" --dry-run
# Transpiles to: 
# {
#   "function": "count",
#   "args": {
#     "function": "distinct",
#     "args": "mac_addr"
#   }
# }
```

**Multiple aggregates with aliases**:
```bash
iptvportal sql -q "
  SELECT 
    COUNT(*) AS cnt, 
    COUNT(DISTINCT inet_addr) AS uniq 
  FROM media
" --show-request

# Result example: [[651232, 14381]]
```

### JSONSQL Subapp

Execute native JSONSQL queries with dedicated subcommands for each operation type.

#### SELECT Command

```bash
# Basic SELECT
iptvportal jsonsql select \
  --from subscriber \
  --data "id,username,disabled" \
  --limit 10

# With WHERE condition (JSONSQL format)
iptvportal jsonsql select \
  --from subscriber \
  --data "id,username" \
  --where '{"eq": ["disabled", false]}' \
  --limit 10

# With ORDER BY
iptvportal jsonsql select \
  --from subscriber \
  --data "id,username" \
  --order-by username \
  --limit 10

# With OFFSET
iptvportal jsonsql select \
  --from subscriber \
  --data "id,username" \
  --limit 10 \
  --offset 20

# SELECT DISTINCT
iptvportal jsonsql select \
  --from subscriber \
  --data "username" \
  --distinct

# With GROUP BY
iptvportal jsonsql select \
  --from terminal \
  --data "subscriber_id" \
  --group-by subscriber_id

# Using editor
iptvportal jsonsql select --edit
iptvportal jsonsql select -e
```

#### INSERT Command

```bash
# Insert single row
iptvportal jsonsql insert \
  --into package \
  --columns "name,paid" \
  --values '[["Premium", true]]' \
  --returning id

# Insert multiple rows
iptvportal jsonsql insert \
  --into package \
  --columns "name,paid" \
  --values '[["Basic", false], ["Premium", true]]' \
  --returning id

# Using editor
iptvportal jsonsql insert --edit
```

#### UPDATE Command

```bash
# Update with WHERE
iptvportal jsonsql update \
  --table subscriber \
  --set '{"disabled": true}' \
  --where '{"eq": ["username", "test123"]}' \
  --returning id

# Update without WHERE (updates all rows - be careful!)
iptvportal jsonsql update \
  --table subscriber \
  --set '{"verified": false}'

# Using editor
iptvportal jsonsql update --edit
```

#### DELETE Command

```bash
# Delete with WHERE
iptvportal jsonsql delete \
  --from terminal \
  --where '{"eq": ["id", 123]}' \
  --returning id

# Delete with complex WHERE
iptvportal jsonsql delete \
  --from terminal \
  --where '{"and": [{"eq": ["disabled", true]}, {"lt": ["last_active", "2020-01-01"]}]}'

# Using editor
iptvportal jsonsql delete --edit
```

#### JSONSQL Editor Mode

When using `--edit`, the CLI opens your configured editor with a JSON template:

```json
{
  "data": ["*"],
  "from": "table_name",
  "where": {"eq": ["column", "value"]},
  "limit": 10
}
```

Edit the template, save, and exit to execute the query.

## Transpile Command

Convert SQL queries to JSONSQL format without executing them.

### Basic Usage

```bash
# Simple query
iptvportal transpile "SELECT * FROM subscriber"

# With WHERE clause
iptvportal transpile "SELECT id, username FROM subscriber WHERE disabled = false"

# Complex query with JOIN
iptvportal transpile "
  SELECT s.username, t.mac_addr 
  FROM subscriber s 
  JOIN terminal t ON s.id = t.subscriber_id 
  WHERE s.disabled = false
"
```

### Output Formats

```bash
# JSON format (default)
iptvportal transpile "SELECT * FROM subscriber"

# YAML format
iptvportal transpile "SELECT * FROM subscriber" --format yaml
```

### From File

```bash
# Read SQL from file
iptvportal transpile --file query.sql

# With specific format
iptvportal transpile --file query.sql --format yaml
```

## Output Formats

All query commands support multiple output formats:

### Table Format (Default for SELECT)

```bash
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5"

# Output (schema-mapped by default):
# ┏━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
# ┃ id ┃ username ┃ disabled ┃
# ┡━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
# │ 1  │ test123  │ false    │
# │ 2  │ user456  │ false    │
# └────┴──────────┴──────────┘
# Disable mapping if you need raw positional inference:
# iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" --no-map-schema
```

### JSON Format

```bash
iptvportal sql -q "SELECT * FROM subscriber LIMIT 2" --format json

# Output (schema-mapped keys):
# [
#   {"id": 1, "username": "test123", "disabled": false},
#   {"id": 2, "username": "user456", "disabled": false}
# ]
```

### YAML Format

```bash
iptvportal sql -q "SELECT * FROM subscriber LIMIT 2" -f yaml

# Output (schema-mapped keys):
# - id: 1
#   username: test123
#   disabled: false
# - id: 2
#   username: user456
#   disabled: false
```

## Special Modes

### Dry-Run Mode

Preview queries before execution without actually running them.

**Available in:** `sql` and `jsonsql` commands

```bash
# SQL dry-run
iptvportal sql -q "SELECT * FROM subscriber WHERE disabled = false" --dry-run

# JSONSQL dry-run
iptvportal jsonsql select --from subscriber --limit 5 --dry-run
```

**Output includes:**
- Original SQL (for sql command)
- Transpiled JSONSQL
- Complete JSON-RPC request
- "Query will NOT be executed" message

### Show Request Mode

Execute query normally but also display the JSON-RPC request.

**Available in:** `sql` and `jsonsql` commands

```bash
# SQL with request
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" --show-request

# JSONSQL with request
iptvportal jsonsql select --from subscriber --limit 5 --show-request
```

**Output includes:**
- JSON-RPC request sent to API
- Query result (formatted per --format option)

Useful for:
- Debugging API calls
- Understanding request structure
- Learning JSONSQL format
- API integration development

## Editor Integration

The CLI supports opening your preferred editor for writing queries.

### Configuration

Set your editor via environment variable:

```bash
# Linux/macOS
export EDITOR=vim
export EDITOR=nano
export EDITOR=code  # VS Code

# Or use VISUAL
export VISUAL=vim
```

The CLI will automatically detect common editors: vim, vi, nano, emacs.

### Usage

```bash
# SQL editor
iptvportal sql --edit
iptvportal sql -e

# JSONSQL editors
iptvportal jsonsql select --edit
iptvportal jsonsql insert -e
iptvportal jsonsql update --edit
iptvportal jsonsql delete -e
```

**SQL Editor:**
- Opens a `.sql` temp file
- Edit your SQL query
- Save and exit to execute

**JSONSQL Editor:**
- Opens a `.json` temp file with template
- Edit the JSONSQL object
- Save and exit to execute

## Common Use Cases

### 1. Check Active Subscribers

```bash
iptvportal sql -q "
  SELECT id, username, email 
  FROM subscriber 
  WHERE disabled = false 
  LIMIT 20
"
```

### 2. Count Devices per Subscriber

```bash
iptvportal sql -q "
  SELECT subscriber_id, COUNT(*) as device_count 
  FROM terminal 
  GROUP BY subscriber_id 
  ORDER BY device_count DESC
"
```

### 3. Find Subscribers Without Devices

```bash
iptvportal sql -q "
  SELECT s.id, s.username 
  FROM subscriber s 
  LEFT JOIN terminal t ON s.id = t.subscriber_id 
  WHERE t.id IS NULL
"
```

### 4. Disable Test Accounts (with Dry-Run)

```bash
# Preview first
iptvportal sql -q "
  UPDATE subscriber 
  SET disabled = true 
  WHERE username LIKE 'test%' 
  RETURNING id
" --dry-run

# Execute after review
iptvportal sql -q "
  UPDATE subscriber 
  SET disabled = true 
  WHERE username LIKE 'test%' 
  RETURNING id
"
```

### 5. Clean Old Terminal Sessions

```bash
iptvportal sql -q "
  DELETE FROM terminal_playlog 
  WHERE start < '2020-01-01 00:00:00' 
  RETURNING id
"
```

### 6. Complex Query Development

```bash
# Use editor for complex queries
iptvportal sql --edit

# Or break into steps with dry-run
iptvportal sql -q "YOUR_COMPLEX_QUERY" --dry-run
iptvportal transpile "YOUR_COMPLEX_QUERY"  # Check JSONSQL
iptvportal sql -q "YOUR_COMPLEX_QUERY"      # Execute
```

## Environment Variables

All configuration can be set via environment variables with `IPTVPORTAL_` prefix:

```bash
export IPTVPORTAL_DOMAIN=operator
export IPTVPORTAL_USERNAME=admin
export IPTVPORTAL_PASSWORD=secret
export IPTVPORTAL_TIMEOUT=30.0
export IPTVPORTAL_MAX_RETRIES=3
export IPTVPORTAL_VERIFY_SSL=true

# Editor configuration
export EDITOR=vim
export VISUAL=code
```

## Troubleshooting

### Authentication Fails

```bash
# Check configuration
iptvportal config show

# Test authentication
iptvportal auth

# Verify credentials in .env file
cat .env
```

### Query Syntax Errors

```bash
# Use dry-run to see the generated JSONSQL
iptvportal sql -q "YOUR_QUERY" --dry-run

# Or transpile separately
iptvportal transpile "YOUR_QUERY"
```

### Connection Timeout

```bash
# Increase timeout
iptvportal config set timeout 60

# Or set via environment variable
export IPTVPORTAL_TIMEOUT=60
```

### Editor Not Found

```bash
# Set EDITOR environment variable
export EDITOR=nano

# Or use VISUAL
export VISUAL=vim

# Check available editors
which vim nano emacs code
```

## Tips and Best Practices

1. **Use SQL mode for complex queries** - It's more readable and familiar
2. **Always use dry-run first** for UPDATE and DELETE operations
3. **Use editor mode** for multi-line or complex queries
4. **Use --show-request** when developing integrations or debugging
5. **Set appropriate timeout** based on query complexity
6. **Use RETURNING clause** to get affected row IDs
7. **Keep credentials in .env file** for security
8. **Use config init wizard** for first-time setup
9. **Test with LIMIT** before running large queries
10. **Use transpile command** to learn JSONSQL format
11. **Disable auto schema mapping** with `--no-map-schema` for debugging raw field positions

## Command Cheat Sheet

```bash
# Configuration
iptvportal config init              # Interactive setup
iptvportal config show              # View config
iptvportal config set <key> <val>   # Set value
iptvportal config get <key>         # Get value

# Authentication
iptvportal auth                     # Check status
iptvportal auth --renew            # Force re-auth

# SQL Queries
iptvportal sql -q "SELECT ..."                    # Execute SQL
iptvportal sql -e                                 # Open editor
iptvportal sql -q "SELECT ..." --dry-run         # Preview
iptvportal sql -q "SELECT ..." --show-request    # Show request+result
iptvportal sql -q "SELECT ..." -f json           # JSON output

# JSONSQL Queries
iptvportal jsonsql select --from table --limit 10     # Native JSONSQL
iptvportal jsonsql select -e                           # Editor mode
iptvportal jsonsql insert --into table --columns ...  # Insert
iptvportal jsonsql update --table t --set '{...}'     # Update
iptvportal jsonsql delete --from table --where ...    # Delete

# Transpiler
iptvportal transpile "SELECT ..."              # SQL to JSONSQL
iptvportal transpile --file query.sql         # From file
iptvportal transpile "SELECT ..." -f yaml     # YAML output
```

## Integration with Scripts

### Bash Script Example

```bash
#!/bin/bash

# Get all active subscribers
iptvportal sql -q "
  SELECT id, username 
  FROM subscriber 
  WHERE disabled = false
" --format json > active_subscribers.json

# Process results
cat active_subscribers.json | jq '.[] | .username'
```

### Python Script Example

```python
import subprocess
import json

# Execute query via CLI
result = subprocess.run(
    ["iptvportal", "sql", "-q", 
     "SELECT * FROM subscriber LIMIT 10",
     "--format", "json"],
    capture_output=True,
    text=True
)

# Parse JSON output
data = json.loads(result.stdout)
for row in data:
    print(f"ID: {row['id']}, Username: {row['username']}")
```

### Using with jq

```bash
# Extract specific fields
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5" -f json | \
  jq '.[] | {id, username}'

# Filter results
iptvportal sql -q "SELECT * FROM subscriber" -f json | \
  jq '.[] | select(.disabled == false)'

# Count results
iptvportal sql -q "SELECT * FROM subscriber" -f json | \
  jq 'length'
```

## See Also

- [JSONSQL Documentation](jsonsql.md)
- [Python API Documentation](../README.md)
- [IPTVPortal API Documentation](https://iptvportal.cloud/support/api/)
