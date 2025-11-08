# CLI Configuration Guide

## Overview

The IPTVPortal CLI provides extensive configuration options to customize behavior, set defaults, and enable safety guardrails. Configuration can be loaded from files, environment variables, or command-line arguments.

## Configuration Hierarchy

Settings are loaded in priority order (highest to lowest):

1. **Command-line arguments** - Explicit flags override everything
2. **Environment variables** - `IPTVPORTAL_CLI_*` prefix
3. **Config file** - Explicit `--config` path
4. **Default config file** - `~/.iptvportal/cli-config.yaml`
5. **Built-in defaults** - Sensible defaults from `CLISettings`

## Quick Start

### Generate Default Configuration

```bash
# Create ~/.iptvportal/cli-config.yaml with all options documented
python -c "from iptvportal.config import create_default_cli_config; create_default_cli_config()"
```

### Load Configuration

```python
from iptvportal.config import load_cli_config, save_cli_config, CLISettings

# Load from default location or environment
config = load_cli_config()

# Load from specific file
config = load_cli_config("./my-config.yaml")

# Create custom config
config = CLISettings(
    default_format="json",
    max_limit=5000,
    confirm_destructive_queries=True
)

# Save configuration
save_cli_config(config, format="yaml")
```

## Configuration Categories

### 1. Output Defaults

Control how query results are displayed.

```yaml
# Output format: table, json, yaml, csv
default_format: table

# Table rendering style
default_table_style: default  # simple, github, grid, fancy_grid, pipe, orgtbl, rst, mediawiki

# Table appearance
max_table_width: null  # null = terminal width
truncate_strings: true
max_string_length: 50
show_row_numbers: false
colorize_output: true
```

**Example: Prefer JSON output**

```yaml
default_format: json
colorize_output: true
```

### 2. Query Safety & Guardrails

Protect against dangerous queries and mistakes.

```yaml
# Enable all safety checks
enable_guardrails: true

# Require LIMIT on SELECT (prevents full table scans)
require_limit_on_select: false

# Auto-add LIMIT if not specified
default_limit: null  # null = no auto-limit

# Maximum allowed LIMIT value
max_limit: 10000

# Warn when LIMIT exceeds threshold
warn_large_limit: 1000

# Confirm destructive operations
confirm_destructive_queries: true  # UPDATE/DELETE without WHERE
confirm_large_updates: true
large_update_threshold: 100  # rows

# Always preview before execution
dry_run_first: false
```

**Example: Safe Production Settings**

```yaml
enable_guardrails: true
require_limit_on_select: true
default_limit: 100
max_limit: 1000
confirm_destructive_queries: true
confirm_large_updates: true
large_update_threshold: 50
```

**Example: Fast Development Settings**

```yaml
enable_guardrails: false
require_limit_on_select: false
confirm_destructive_queries: false
max_limit: 100000
```

### 3. Performance & Caching

Optimize performance with intelligent caching.

```yaml
# Query result caching
enable_query_cache: true
cache_ttl_seconds: 300  # 5 minutes
cache_max_size_mb: 100
cache_location: ~/.iptvportal/cache

# Schema caching
enable_schema_cache: true
schema_cache_ttl_seconds: 3600  # 1 hour
```

**Example: Aggressive Caching**

```yaml
enable_query_cache: true
cache_ttl_seconds: 3600  # 1 hour
cache_max_size_mb: 500
enable_schema_cache: true
schema_cache_ttl_seconds: 86400  # 24 hours
```

**Example: Disable Caching**

```yaml
enable_query_cache: false
cache_ttl_seconds: 0
enable_schema_cache: false
```

### 4. Editor & Input

Customize the `--edit` experience.

```yaml
# Text editor (null = $EDITOR environment variable)
default_editor: null  # or "vim", "nano", "code", etc.

# Editor features
editor_syntax_highlighting: true
save_query_history: true
query_history_size: 1000
query_history_location: ~/.iptvportal/query-history.txt
```

**Example: VS Code Integration**

```yaml
default_editor: code
editor_syntax_highlighting: true
save_query_history: true
query_history_size: 5000
```

### 5. Transpiler Behavior

Control SQL to JSONSQL transpilation.

```yaml
# SQL dialect
transpiler_dialect: postgres  # postgres, mysql, sqlite, tsql, oracle

# Auto-optimization
auto_order_by_id: true

# SQL features
preserve_sql_comments: false
validate_jsonsql: true
```

**Example: MySQL Compatibility**

```yaml
transpiler_dialect: mysql
auto_order_by_id: true
validate_jsonsql: true
```

### 6. Schema Mapping

Auto-detect and use table schemas.

```yaml
# Schema detection
auto_detect_schema: true
schema_directory: ~/.iptvportal/schemas

# Use mapping by default (without --map-schema flag)
prefer_mapped_results: false
```

**Example: Always Use Schema Mapping**

```yaml
auto_detect_schema: true
schema_directory: ./schemas
prefer_mapped_results: true
```

### 7. Logging & Debug

Control verbosity and debugging output.

```yaml
# Logging
verbose: false
log_queries: false
query_log_location: ~/.iptvportal/query.log
log_level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Query metrics
show_execution_time: true
show_row_count: true
```

**Example: Debug Mode**

```yaml
verbose: true
log_queries: true
log_level: DEBUG
show_execution_time: true
show_row_count: true
```

### 8. Session & Auth

Manage authentication sessions.

```yaml
# Session caching
session_cache_enabled: true
session_cache_location: ~/.iptvportal/session-cache
auto_renew_session: true
```

### 9. Advanced Features

Enable power-user features.

```yaml
# Autocomplete
enable_autocomplete: true
autocomplete_cache_ttl: 3600

# Query analysis
enable_query_explain: false

# Parallel execution
parallel_query_threshold: 5
max_parallel_queries: 10
```

**Example: Power User Setup**

```yaml
enable_autocomplete: true
enable_query_explain: true
parallel_query_threshold: 3
max_parallel_queries: 20
```

### 10. Export Settings

Configure result exports.

```yaml
# Export configuration
export_directory: ./exports
export_timestamp_format: "%Y%m%d_%H%M%S"

# Compression
compress_exports: false
compress_threshold_mb: 10
```

**Example: Auto-Compress Large Exports**

```yaml
export_directory: ~/data/exports
compress_exports: true
compress_threshold_mb: 5
export_timestamp_format: "%Y-%m-%d_%H-%M-%S"
```

### 11. Notifications

Get notified about long-running queries.

```yaml
# Desktop notifications
enable_notifications: false
notification_threshold_seconds: 30
play_sound_on_complete: false
```

**Example: Enable Notifications**

```yaml
enable_notifications: true
notification_threshold_seconds: 10
play_sound_on_complete: true
```

### 12. Pager Settings

Use a pager for large outputs.

```yaml
# Pager configuration
use_pager: false
pager_threshold_lines: 100
pager_command: null  # null = $PAGER or 'less -R'
```

**Example: Always Use Less**

```yaml
use_pager: true
pager_threshold_lines: 50
pager_command: "less -R -S -X"
```

## Environment Variables

All settings can be overridden with environment variables using the `IPTVPORTAL_CLI_` prefix:

```bash
# Override default format
export IPTVPORTAL_CLI_DEFAULT_FORMAT=json

# Set max limit
export IPTVPORTAL_CLI_MAX_LIMIT=5000

# Enable verbose mode
export IPTVPORTAL_CLI_VERBOSE=true

# Specify config file
export IPTVPORTAL_CLI_CONFIG=/path/to/config.yaml
```

## Command-Line Overrides

Command-line flags always take precedence:

```bash
# Override config with --format
iptvportal sql -q "SELECT * FROM subscriber" --format json

# Even if config has default_format: table

# Override with environment
IPTVPORTAL_CLI_MAX_LIMIT=100 iptvportal sql -q "SELECT * FROM subscriber LIMIT 1000"
# Will warn because 1000 > 100
```

## Configuration Profiles

Create multiple configuration profiles for different environments:

```bash
# Development profile
~/.iptvportal/cli-config-dev.yaml

# Production profile (strict)
~/.iptvportal/cli-config-prod.yaml

# Testing profile (permissive)
~/.iptvportal/cli-config-test.yaml
```

Load specific profile:

```bash
# Use production config
iptvportal sql --config ~/.iptvportal/cli-config-prod.yaml -q "SELECT * FROM subscriber"

# Use dev config
export IPTVPORTAL_CLI_CONFIG=~/.iptvportal/cli-config-dev.yaml
iptvportal sql -q "SELECT * FROM subscriber"
```

## Example Configurations

### Conservative Production Config

```yaml
# ~/.iptvportal/cli-config-prod.yaml
default_format: table
default_limit: 100
max_limit: 1000
require_limit_on_select: true
confirm_destructive_queries: true
confirm_large_updates: true
large_update_threshold: 10
enable_guardrails: true
dry_run_first: true
log_queries: true
query_log_location: /var/log/iptvportal/queries.log
```

### Fast Development Config

```yaml
# ~/.iptvportal/cli-config-dev.yaml
default_format: json
max_limit: 100000
require_limit_on_select: false
confirm_destructive_queries: false
enable_guardrails: false
verbose: true
log_level: DEBUG
enable_query_cache: true
cache_ttl_seconds: 3600
```

### Data Analysis Config

```yaml
# ~/.iptvportal/cli-config-analysis.yaml
default_format: csv
export_directory: ~/data/exports
compress_exports: true
compress_threshold_mb: 5
use_pager: true
pager_threshold_lines: 50
show_execution_time: true
enable_query_cache: true
cache_ttl_seconds: 7200
prefer_mapped_results: true
```

## Guardrail Examples

### Prevent Accidental Full Table Scans

```yaml
require_limit_on_select: true
default_limit: 100
```

```bash
# This will fail
iptvportal sql -q "SELECT * FROM subscriber"
# Error: SELECT queries require LIMIT clause

# This works
iptvportal sql -q "SELECT * FROM subscriber LIMIT 100"
```

### Confirm Dangerous Operations

```yaml
confirm_destructive_queries: true
```

```bash
# This prompts for confirmation
iptvportal sql -q "DELETE FROM subscriber"
# Warning: DELETE without WHERE clause affects all rows. Continue? [y/N]
```

### Warn About Large Limits

```yaml
warn_large_limit: 1000
max_limit: 10000
```

```bash
# This warns
iptvportal sql -q "SELECT * FROM subscriber LIMIT 5000"
# Warning: LIMIT 5000 exceeds recommended threshold of 1000

# This fails
iptvportal sql -q "SELECT * FROM subscriber LIMIT 50000"
# Error: LIMIT 50000 exceeds maximum of 10000
```

## API Reference

### CLISettings Class

```python
from iptvportal.config import CLISettings

# Create with defaults
config = CLISettings()

# Create with overrides
config = CLISettings(
    default_format="json",
    max_limit=5000,
    enable_guardrails=True
)

# Access settings
print(config.default_format)  # "json"
print(config.max_limit)  # 5000

# Export to dict
data = config.model_dump()
```

### Helper Functions

```python
from iptvportal.config import (
    load_cli_config,
    save_cli_config,
    create_default_cli_config
)

# Load configuration
config = load_cli_config()
config = load_cli_config("./my-config.yaml")

# Save configuration
save_cli_config(config)
save_cli_config(config, "output.yaml", format="yaml")
save_cli_config(config, "output.json", format="json")

# Create default config file
create_default_cli_config()
```

## Best Practices

1. **Use profiles** - Create separate configs for dev/prod/test
2. **Enable guardrails in production** - Prevent accidents
3. **Cache aggressively for analysis** - Speed up repeated queries
4. **Log queries in production** - Audit trail
5. **Use pager for large results** - Better UX
6. **Set reasonable limits** - Protect against runaway queries
7. **Confirm destructive operations** - Safety first
8. **Enable notifications for long queries** - Better awareness

## Troubleshooting

### Config not loading

```bash
# Check which config file is being used
iptvportal config show

# Verify config file syntax
python -c "from iptvportal.config import load_cli_config; print(load_cli_config())"

# Use explicit config path
iptvportal sql --config ./my-config.yaml -q "SELECT 1"
```

### Environment variables not working

```bash
# Check env vars
env | grep IPTVPORTAL_CLI

# Test override
IPTVPORTAL_CLI_VERBOSE=true iptvportal sql -q "SELECT 1"
```

### Validation errors

```yaml
# Invalid: max_limit too high
max_limit: 2000000  # Error: max 1000000

# Fix:
max_limit: 100000  # Valid
```

## See Also

- [CLI Documentation](./cli.md)
- [Configuration Management Commands](./cli.md#config-commands)
- [IPTVPortal Settings](../src/iptvportal/config.py)
