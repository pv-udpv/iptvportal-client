# IPTVPortal CLI Documentation

Comprehensive guide to using the IPTVPortal command-line interface.

> **Note**: The CLI now uses a service-oriented architecture with auto-discovery.  
> See [CLI Architecture](cli-architecture.md) for details on the service design.

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
iptvportal jsonsql auth

# 3. Run your first SQL query
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# Or use native JSONSQL
iptvportal jsonsql select --from subscriber --limit 5
 
# (New) Schema mapping ON by default: column names shown using schema (auto-generated if missing)
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"               # mapped
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --no-map-schema  # disable mapping
iptvportal jsonsql select --from subscriber --limit 5                # mapped
iptvportal jsonsql select --from subscriber --limit 5 --no-map-schema # disable mapping
```

## Service Structure

The CLI is organized into services, each handling a specific domain:

- **config**: Global configuration management
- **cache**: Query result cache management
- **schema**: Table schema management
- **jsonsql**: API operations (auth, SQL, JSONSQL, utilities)
- **sync**: SQLite sync cache management

Each service has its own commands and optional `config` subcommand for service-specific settings.

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

Creates a `~/.iptvportal/cli-config.yaml` with your settings (optionally creates a `.env` file in the current directory if selected).

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

### Service-Specific Configuration

Each service can have its own configuration:

```bash
# Cache configuration
iptvportal cache config show
iptvportal cache config get ttl

# Schema configuration
iptvportal schema config show
iptvportal schema config get file

# JSONSQL/API configuration
iptvportal jsonsql config show
iptvportal jsonsql config get timeout
```

## Authentication

### Check Authentication Status

```bash
iptvportal jsonsql auth
```

Shows:
- Domain and username
- Auth and API URLs
- Session ID (after successful connection)
- Connection status

### Force Re-authentication

```bash
iptvportal jsonsql auth --renew
```

## Query Commands

The CLI provides SQL and JSONSQL query capabilities under the `jsonsql` service:

1. **`iptvportal jsonsql sql`** - Execute SQL queries (auto-transpiled to JSONSQL)
2. **`iptvportal jsonsql select/insert/update/delete`** - Execute native JSONSQL queries

### SQL Subcommand

Execute SQL queries that are automatically transpiled to JSONSQL.

#### Basic Usage

```bash
# Direct query with --query or -q
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10"

# Multi-line query
iptvportal jsonsql sql --query "
  SELECT id, username, email 
  FROM subscriber 
  WHERE disabled = false 
  LIMIT 20
"

# Open editor to write query
iptvportal jsonsql sql --edit
iptvportal jsonsql sql -e
```

#### Output Formats

```bash
# Table format (default)
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# JSON format
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --format json
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" -f json

# YAML format
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" -f yaml
```

#### Dry-Run Mode

Preview the transpiled JSONSQL without executing:

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber WHERE disabled = false" --dry-run
```

Shows:
- Original SQL query
- Transpiled JSONSQL
- Complete JSON-RPC request
- "Query will NOT be executed" message

#### Show Request Mode

Execute query and show both the request and result:

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --show-request
```

Shows:
- JSON-RPC request sent to API
- Query result

#### SQL Examples

```bash
# Simple SELECT
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 10"

# With WHERE clause
iptvportal jsonsql sql -q "SELECT id, username FROM subscriber WHERE disabled = false"

# With JOIN
iptvportal jsonsql sql -q "
  SELECT s.username, COUNT(t.id) as device_count 
  FROM subscriber s 
  JOIN terminal t ON s.id = t.subscriber_id 
  GROUP BY s.username
"

# Complex JOIN with EPG data
iptvportal jsonsql sql -q "
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
iptvportal jsonsql sql -q "INSERT INTO package (name, paid) VALUES ('Premium', true) RETURNING id"

# UPDATE
iptvportal jsonsql sql -q "UPDATE subscriber SET disabled = true WHERE username = 'test' RETURNING id"

# DELETE
iptvportal jsonsql sql -q "DELETE FROM terminal WHERE id = 123 RETURNING id"

# Aggregate functions
iptvportal jsonsql sql -q "SELECT COUNT(*) FROM media"
iptvportal jsonsql sql -q "SELECT COUNT(id) FROM subscriber"
iptvportal jsonsql sql -q "SELECT COUNT(DISTINCT inet_addr) FROM media"

# Complex aggregates
iptvportal jsonsql sql -q "
  SELECT 
    COUNT(*) AS total_count, 
    COUNT(DISTINCT inet_addr) AS unique_addrs 
  FROM media
"

# Group by with aggregates
iptvportal jsonsql sql -q "
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
iptvportal jsonsql sql -q "SELECT COUNT(*) FROM tv_channel" --dry-run
# Transpiles to: {"function": "count", "args": ["*"]}
```

**COUNT(field)** - Counts non-null values in a specific field (uses string format):
```bash
iptvportal jsonsql sql -q "SELECT COUNT(id) FROM media" --dry-run
# Transpiles to: {"function": "count", "args": "id"}
```

**COUNT(DISTINCT field)** - Counts unique values (uses nested function format):
```bash
iptvportal jsonsql sql -q "SELECT COUNT(DISTINCT mac_addr) FROM terminal" --dry-run
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
iptvportal jsonsql sql -q "
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

# With debug mode
iptvportal jsonsql insert \
  --into package \
  --columns "name,paid" \
  --values '[["Test", true]]' \
  --debug
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

# With debug mode
iptvportal jsonsql update \
  --table subscriber \
  --set '{"disabled": true}' \
  --where '{"eq": ["id", 123]}' \
  --debug
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

# With debug mode
iptvportal jsonsql delete \
  --from terminal \
  --where '{"eq": ["id", 456]}' \
  --debug
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
iptvportal jsonsql utils transpile "SELECT * FROM subscriber"

# With WHERE clause
iptvportal jsonsql utils transpile "SELECT id, username FROM subscriber WHERE disabled = false"

# Complex query with JOIN
iptvportal jsonsql utils transpile "
  SELECT s.username, t.mac_addr 
  FROM subscriber s 
  JOIN terminal t ON s.id = t.subscriber_id 
  WHERE s.disabled = false
"
```

### Output Formats

```bash
# JSON format (default)
iptvportal jsonsql utils transpile "SELECT * FROM subscriber"

# YAML format
iptvportal jsonsql utils transpile "SELECT * FROM subscriber" --format yaml
```

### From File

```bash
# Read SQL from file
iptvportal jsonsql utils transpile --file query.sql

# With specific format
iptvportal jsonsql utils transpile --file query.sql --format yaml
```

## Output Formats

All query commands support multiple output formats:

### Table Format (Default for SELECT)

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5"

# Output (schema-mapped by default):
# ┏━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
# ┃ id ┃ username ┃ disabled ┃
# ┡━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
# │ 1  │ test123  │ false    │
# │ 2  │ user456  │ false    │
# └────┴──────────┴──────────┘
# Disable mapping if you need raw positional inference:
# iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --no-map-schema
```

### JSON Format

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 2" --format json

# Output (schema-mapped keys):
# [
#   {"id": 1, "username": "test123", "disabled": false},
#   {"id": 2, "username": "user456", "disabled": false}
# ]
```

### YAML Format

```bash
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 2" -f yaml

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
iptvportal jsonsql sql -q "SELECT * FROM subscriber WHERE disabled = false" --dry-run

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
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --show-request

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

### Debug Mode

Enable detailed step-by-step logging for troubleshooting and understanding query execution flow.

**Available in:** `sql` and all `jsonsql` commands (select, insert, update, delete)

```bash
# Basic debug mode (human-readable text format)
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" --debug

# Debug with JSON format
iptvportal jsonsql sql -q "SELECT * FROM subscriber" --debug --debug-format json

# Debug with YAML format
iptvportal jsonsql sql -q "SELECT * FROM media LIMIT 10" --debug --debug-format yaml

# Save debug logs to file
iptvportal jsonsql sql -q "SELECT * FROM terminal" --debug --debug-file debug.log

# Works with dry-run mode too
iptvportal jsonsql sql -q "SELECT * FROM subscriber" --dry-run --debug

# Debug mode also works with jsonsql commands
iptvportal jsonsql select --from subscriber --limit 5 --debug
iptvportal jsonsql insert --into package --columns "name" --values '[["test"]]' --debug
iptvportal jsonsql update --table subscriber --set '{"disabled": true}' --where '{"eq": ["id", 1]}' --debug
iptvportal jsonsql delete --from terminal --where '{"eq": ["id", 123]}' --debug
```

**Debug output includes:**
- SQL input (for sql command)
- Transpilation step (SQL → JSONSQL)
- Transpiled JSONSQL query
- Detected query method
- Configuration being used
- JSON-RPC request built
- Table name extraction (for schema mapping)
- Query execution and results
- Full traceback for errors

**Debug formats:**
- `text` (default): Human-readable format with syntax highlighting
- `json`: Machine-readable JSON for automation
- `yaml`: YAML format for better readability

**Use cases:**
- Troubleshooting query errors
- Understanding SQL to JSONSQL transpilation
- Debugging schema mapping issues
- Verifying JOIN query handling
- Learning the query execution flow
- Integration testing and automation

**Error handling in debug mode:**
When an error occurs:
- **Without --debug**: Shows concise error message with suggestion to use `--debug`
- **With --debug**: Shows full exception traceback and debug logs for all steps

**Example debug output:**

```
[DEBUG] SQL Input
SELECT id, username FROM subscriber LIMIT 5

[DEBUG] Transpilation
Transpiling SQL to JSONSQL...

[DEBUG] Transpiled JSONSQL
{
  "data": ["id", "username"],
  "from": "subscriber",
  "order_by": "id",
  "limit": 5
}

[DEBUG] Detected Method
select

[DEBUG] JSON-RPC Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "select",
  "params": {
    "data": ["id", "username"],
    "from": "subscriber",
    "order_by": "id",
    "limit": 5
  }
}
```

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
iptvportal jsonsql sql --edit
iptvportal jsonsql sql -e

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

## Schema Management

The `schema` command provides powerful introspection and analysis tools for understanding your database structure.

### Introspect Table Structure

Automatically analyze a table's structure with comprehensive metadata:

```bash
# Simple table introspection (using positional argument)
iptvportal schema introspect tv_channel

# Using --table option (equivalent)
iptvportal schema introspect --table tv_channel

# SQL-based introspection
iptvportal schema introspect --from-sql="SELECT * FROM tv_channel"

# With manual field mappings
iptvportal schema introspect --table media --fields="0:id,1:name,2:url,3:duration"

# Save schema to file
iptvportal schema introspect tv_channel --save
iptvportal schema introspect media --save --output schemas/media-schema.yaml

# Skip metadata gathering (faster)
iptvportal schema introspect tv_channel --no-metadata

# Skip DuckDB analysis
iptvportal schema introspect tv_channel --no-duckdb-analysis

# Custom sample size for analysis
iptvportal schema introspect media --sample-size 5000

# NEW: Introspect and sync to local cache
iptvportal schema introspect tv_channel --sync

# NEW: Introspect, sync with custom chunk size and analyze from cache
iptvportal schema introspect tv_program --fields='0:channel_id,1:start,2:stop' --sync --sync-chunk=5000

# NEW: Sync with ordering and analyze synced data
iptvportal schema introspect media --sync --order-by-fields='id:asc' --analyze-from-cache

# NEW: Sync with timeout (0 = no timeout)
iptvportal schema introspect tv_channel --sync --sync-run-timeout=300
```

### What Gets Analyzed

**Automatic Field Detection:**
- Field names inferred from data patterns (email, URL, UUID, phone, etc.)
- Field types (integer, string, boolean, float, datetime, json)
- Position mapping for query results

**Metadata Collection:**
- **Row Count**: Total number of rows in the table
- **Field Count**: Number of columns in the schema
- **ID Ranges**: MIN(id) and MAX(id) for primary keys
- **Timestamp Ranges**: MIN/MAX for datetime fields

**DuckDB Statistical Analysis** (optional, requires `pip install iptvportal-client[analysis]`):
- **Data Types**: Precise type inference
- **Null Percentage**: How many values are NULL
- **Unique Counts**: Number of distinct values per column
- **Cardinality**: Uniqueness ratio (0-1)
- **Numeric Stats**: Min, Max, Average for numeric columns
- **String Stats**: Min/Max/Average length for text columns
- **Top Values**: Most common values for low-cardinality columns

**Smart Sync Configuration:**
- Recommended chunk sizes based on table size
- WHERE clauses for soft deletes and flag fields
- Incremental sync settings for large tables
- Cache strategies and TTL recommendations

**NEW: Sync Integration** (with `--sync` flag):
- Automatically syncs table to local SQLite cache after introspection
- Uses introspected schema and auto-generated sync configuration
- Supports custom sync options:
  - `--sync-chunk`: Override auto-generated chunk size
  - `--order-by-fields`: Specify ordering (e.g., 'id:asc')
  - `--sync-run-timeout`: Set timeout in seconds (0 = no timeout)
  - `--analyze-from-cache`: Run DuckDB analysis on synced cache data for comprehensive statistics
- Progress reporting during sync
- Can analyze more than sample data when using `--analyze-from-cache`

### Example Output

```bash
$ iptvportal schema introspect tv_channel

Introspecting table: tv_channel
Gathering metadata (row count, ID ranges, timestamps)...
Performing DuckDB analysis (sample size: 1000)...
✓ Introspection complete

Table:            tv_channel
Field Count:      8
Row Count:        1,234
Max ID:           1234
Min ID:           1
Analyzed At:      2025-11-09T02:43:55

Detected Fields:

Pos  Name          Type     Description
---  ------------  -------  ------------------
0    id            integer  Auto-detected field
1    name          string   Auto-detected field
2    url           string   Auto-detected field
3    epg_id        string   Auto-detected field
4    enabled       boolean  Auto-detected field
5    created_at    datetime Auto-detected field
6    updated_at    datetime Auto-detected field
7    logo_url      string   Auto-detected field

DuckDB Statistical Analysis:

  id:
    Type: BIGINT
    Null %: 0.00%
    Unique: 1234 (100.00% cardinality)
    Range: [1 .. 1234]
    Average: 617.50

  name:
    Type: VARCHAR
    Null %: 0.00%
    Unique: 1234 (100.00% cardinality)
    Length: [3 .. 45]
    Avg Length: 18.23

  enabled:
    Type: BOOLEAN
    Null %: 0.00%
    Unique: 2 (0.16% cardinality)
    Top Values:
      • true: 1150
      • false: 84

Auto-generated Sync Guardrails:

Sync Limit:       2,468
Chunk Size:       5,000
Cache Strategy:   full
Auto Sync:        Yes
Cache TTL:        1800s
```

### Example Output with Sync

```bash
$ iptvportal schema introspect tv_channel --sync --analyze-from-cache

Introspecting table: tv_channel
Gathering metadata (row count, ID ranges, timestamps)...
Performing DuckDB analysis (sample size: 1000)...
✓ Introspection complete

Table:            tv_channel
Field Count:      8
Row Count:        1,234
Max ID:           1234
Min ID:           1

Syncing table tv_channel to local cache...

Progress: 1/1 chunks, 1,234 rows, 2.3s elapsed

✓ Sync complete!
  Rows fetched: 1,234
  Rows inserted: 1,234
  Chunks processed: 1
  Duration: 2.45s

Performing DuckDB analysis on synced cache data...

DuckDB Analysis (from cache):

  id:
    Type: BIGINT
    Null %: 0.00%
    Unique: 1234 (100.00% cardinality)
    Range: [1 .. 1234]

  name:
    Type: VARCHAR
    Null %: 0.00%
    Unique: 1234 (100.00% cardinality)
    Length: [3 .. 45]
    Avg Length: 18.23

  enabled:
    Type: BOOLEAN
    Unique: 2 (0.16% cardinality)
    Top Values:
      • true: 1150
      • false: 84
```

### Other Schema Commands

```bash
# List all loaded schemas
iptvportal schema list

# Show detailed schema info
iptvportal schema show tv_channel

# Generate schema from SQL query
iptvportal schema from-sql -q "SELECT * FROM media LIMIT 10"

# Validate field mappings
iptvportal schema validate-mapping subscriber -m "0:id,1:username,2:email"

# Export schema to file
iptvportal schema export tv_channel -o schemas/tv-channel.yaml

# Import schemas from file
iptvportal schema import schemas.yaml

# Validate schema file
iptvportal schema validate schemas.yaml

# Generate ORM models
iptvportal schema generate-models schemas.yaml --format sqlmodel
```

## Common Use Cases

### 1. Check Active Subscribers

```bash
iptvportal jsonsql sql -q "
  SELECT id, username, email 
  FROM subscriber 
  WHERE disabled = false 
  LIMIT 20
"
```

### 2. Count Devices per Subscriber

```bash
iptvportal jsonsql sql -q "
  SELECT subscriber_id, COUNT(*) as device_count 
  FROM terminal 
  GROUP BY subscriber_id 
  ORDER BY device_count DESC
"
```

### 3. Find Subscribers Without Devices

```bash
iptvportal jsonsql sql -q "
  SELECT s.id, s.username 
  FROM subscriber s 
  LEFT JOIN terminal t ON s.id = t.subscriber_id 
  WHERE t.id IS NULL
"
```

### 4. Disable Test Accounts (with Dry-Run)

```bash
# Preview first
iptvportal jsonsql sql -q "
  UPDATE subscriber 
  SET disabled = true 
  WHERE username LIKE 'test%' 
  RETURNING id
" --dry-run

# Execute after review
iptvportal jsonsql sql -q "
  UPDATE subscriber 
  SET disabled = true 
  WHERE username LIKE 'test%' 
  RETURNING id
"
```

### 5. Clean Old Terminal Sessions

```bash
iptvportal jsonsql sql -q "
  DELETE FROM terminal_playlog 
  WHERE start < '2020-01-01 00:00:00' 
  RETURNING id
"
```

### 6. Complex Query Development

```bash
# Use editor for complex queries
iptvportal jsonsql sql --edit

# Or break into steps with dry-run
iptvportal jsonsql sql -q "YOUR_COMPLEX_QUERY" --dry-run
iptvportal jsonsql utils transpile "YOUR_COMPLEX_QUERY"  # Check JSONSQL
iptvportal jsonsql sql -q "YOUR_COMPLEX_QUERY"      # Execute
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
iptvportal jsonsql auth

# Verify credentials in .env file
cat .env
```

### Query Syntax Errors

```bash
# Use dry-run to see the generated JSONSQL
iptvportal jsonsql sql -q "YOUR_QUERY" --dry-run

# Or transpile separately
iptvportal jsonsql utils transpile "YOUR_QUERY"
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
12. **Run schema introspect before syncing** to get optimal sync configuration
13. **Install DuckDB for detailed analysis**: `pip install iptvportal-client[analysis]`

## Command Cheat Sheet

```bash
# Configuration
iptvportal config init              # Interactive setup
iptvportal config show              # View config
iptvportal config set <key> <val>   # Set value
iptvportal config get <key>         # Get value

# Authentication
iptvportal jsonsql auth                     # Check status
iptvportal auth --renew            # Force re-auth

# SQL Queries
iptvportal jsonsql sql -q "SELECT ..."                    # Execute SQL
iptvportal jsonsql sql -e                                 # Open editor
iptvportal jsonsql sql -q "SELECT ..." --dry-run         # Preview
iptvportal jsonsql sql -q "SELECT ..." --show-request    # Show request+result
iptvportal jsonsql sql -q "SELECT ..." -f json           # JSON output

# JSONSQL Queries
iptvportal jsonsql select --from table --limit 10     # Native JSONSQL
iptvportal jsonsql select -e                           # Editor mode
iptvportal jsonsql insert --into table --columns ...  # Insert
iptvportal jsonsql update --table t --set '{...}'     # Update
iptvportal jsonsql delete --from table --where ...    # Delete

# Transpiler
iptvportal jsonsql utils transpile "SELECT ..."              # SQL to JSONSQL
iptvportal jsonsql utils transpile --file query.sql         # From file
iptvportal jsonsql utils transpile "SELECT ..." -f yaml     # YAML output

# Schema Management
iptvportal schema introspect tv_channel                    # Analyze table
iptvportal schema introspect --table media                 # Alt syntax
iptvportal schema introspect --from-sql="SELECT * FROM t"  # SQL-based
iptvportal schema list                                     # List schemas
iptvportal schema show table_name                          # Show details
iptvportal schema from-sql -q "SELECT ..." --save          # Generate & save
```

## Integration with Scripts

### Bash Script Example

```bash
#!/bin/bash

# Get all active subscribers
iptvportal jsonsql sql -q "
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
iptvportal jsonsql sql -q "SELECT * FROM subscriber LIMIT 5" -f json | \
  jq '.[] | {id, username}'

# Filter results
iptvportal jsonsql sql -q "SELECT * FROM subscriber" -f json | \
  jq '.[] | select(.disabled == false)'

# Count results
iptvportal jsonsql sql -q "SELECT * FROM subscriber" -f json | \
  jq 'length'
```

## See Also

- [JSONSQL Documentation](jsonsql.md)
- [Python API Documentation](../README.md)
- [IPTVPortal API Documentation](https://iptvportal.cloud/support/api/)
