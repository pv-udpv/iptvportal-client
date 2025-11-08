# Dynaconf Configuration System - CLI Examples

## Overview

The IPTVPortal client now uses dynaconf for modular, hierarchical configuration management. This allows for:

- **Modular configuration**: Split settings across multiple files
- **Schema-specific overrides**: Each schema (subscriber, terminal, package) can have its own settings
- **Environment variable support**: Override any setting via `IPTVPORTAL_` prefix
- **Runtime modification**: Change settings during runtime (not persisted)

## Configuration Files

### Main Configuration
`config/settings.yaml` - Core settings organized by module:
- `core`: Connection, HTTP, session, logging
- `cli`: Output formats, safety guardrails, caching
- `sync`: SQLite cache, sync strategies, maintenance
- `adapters`: Schema and query optimization

### Schema-Specific Settings
Settings in `config/schemas/*.settings.yaml` override main settings for specific tables:
- `subscriber.settings.yaml`: Incremental sync, 30-minute TTL, high priority
- `terminal.settings.yaml`: Full sync, 2-hour TTL, medium priority  
- `package.settings.yaml`: On-demand sync, 24-hour TTL, low priority

## CLI Commands

### Show All Configuration

```bash
# Show all settings as YAML (default)
iptvportal config conf

# Show as JSON
iptvportal config conf --format json

# Show as tree view
iptvportal config conf --format tree
```

### Show Specific Configuration Section

```bash
# Show core settings
iptvportal config conf core

# Show CLI settings
iptvportal config conf cli

# Show sync settings
iptvportal config conf sync

# Show schema-specific settings
iptvportal config conf sync.subscriber
iptvportal config conf sync.terminal
iptvportal config conf sync.package
```

### Show Configuration Files

```bash
# List all loaded configuration files
iptvportal config conf --files
```

Output:
```
Configuration Files:

  1. /path/to/config/settings.yaml
  2. /path/to/config/schemas/package.settings.yaml
  3. /path/to/config/schemas/subscriber.settings.yaml
  4. /path/to/config/schemas/terminal.settings.yaml
```

### Set Configuration at Runtime

```bash
# Set timeout to 60 seconds (runtime only, not persisted)
iptvportal config conf core.timeout --set 60.0

# Enable verbose mode
iptvportal config conf cli.verbose --set true

# Change max limit
iptvportal config conf cli.max_limit --set 5000
```

**Note**: Runtime changes are **not persisted** to disk. To make permanent changes, edit the YAML files directly.

## Environment Variable Overrides

Any configuration value can be overridden using environment variables with the `IPTVPORTAL_` prefix:

```bash
# Override core timeout
export IPTVPORTAL_CORE__TIMEOUT=60.0

# Override CLI verbose mode
export IPTVPORTAL_CLI__VERBOSE=true

# Override subscriber sync TTL
export IPTVPORTAL_SYNC__SUBSCRIBER__TTL=900

# Run with overrides
iptvportal config conf core.timeout
iptvportal config conf cli.verbose
iptvportal config conf sync.subscriber.ttl
```

**Note**: Use double underscores (`__`) to represent nested keys.

## Python API Examples

### Get Configuration Instance

```python
from iptvportal.project_conf import get_conf

# Get configuration object
conf = get_conf()

# Access settings with dot notation
print(conf.core.timeout)           # 30.0
print(conf.cli.max_limit)          # 10000
print(conf.sync.subscriber.strategy)  # 'incremental'
```

### Get Specific Values

```python
from iptvportal.project_conf import get_value

# Get value by key path
timeout = get_value('core.timeout')
max_limit = get_value('cli.max_limit')
subscriber_ttl = get_value('sync.subscriber.ttl')

# With default value
custom_setting = get_value('custom.key', default='fallback')
```

### Set Values at Runtime

```python
from iptvportal.project_conf import set_value, get_value

# Set value (runtime only)
set_value('core.timeout', 120.0)

# Verify change
new_timeout = get_value('core.timeout')
print(f"New timeout: {new_timeout}")  # 120.0
```

### List Settings

```python
from iptvportal.project_conf import list_settings

# Get all settings as dict
all_settings = list_settings()

# Get specific section
core_settings = list_settings('core')
cli_settings = list_settings('cli')
sync_settings = list_settings('sync')
```

### Get Configuration Files

```python
from iptvportal.project_conf import get_config_files

# List all loaded config files
files = get_config_files()
for file_path in files:
    print(file_path)
```

### Reload Configuration

```python
from iptvportal.project_conf import reload_conf

# Reload from disk (useful after editing files)
conf = reload_conf()
```

## Configuration Overlay Examples

### Example 1: Subscriber Override

Global sync strategy is "full", but subscriber uses "incremental":

```python
from iptvportal.project_conf import get_conf

conf = get_conf()

# Global default
print(conf.sync.default_sync_strategy)  # 'full'

# Subscriber override
print(conf.sync.subscriber.strategy)    # 'incremental'
```

### Example 2: Different TTLs per Schema

Each schema has its own cache TTL:

```python
from iptvportal.project_conf import get_conf

conf = get_conf()

print(conf.sync.subscriber.ttl)  # 1800 (30 minutes)
print(conf.sync.terminal.ttl)    # 7200 (2 hours)
print(conf.sync.package.ttl)     # 86400 (24 hours)
```

### Example 3: Priority-based Sync

Schemas have different sync priorities:

```python
from iptvportal.project_conf import get_conf

conf = get_conf()

print(conf.sync.subscriber.priority)  # 1 (high)
print(conf.sync.terminal.priority)    # 2 (medium)
print(conf.sync.package.priority)     # 3 (low)
```

## Testing Configuration

### Unit Tests

Run configuration tests:
```bash
pytest tests/test_project_conf.py -v
```

### Manual Validation

Run standalone validation script:
```bash
python test_conf_standalone.py
```

## Best Practices

1. **Use environment variables for secrets**: Don't store passwords in YAML files
   ```bash
   export IPTVPORTAL_CORE__PASSWORD=my_secret_password
   ```

2. **Schema-specific settings in separate files**: Keep schema settings in `config/schemas/*.settings.yaml`

3. **Document custom settings**: Add comments to YAML files explaining custom values

4. **Test configuration changes**: Use `--dry-run` mode to test before applying changes

5. **Reload after editing files**: Call `reload_conf()` after manual file edits

## Troubleshooting

### Configuration not loading

Check that files exist:
```bash
iptvportal config conf --files
```

### Value not taking effect

1. Check environment variables (they override files)
2. Verify YAML syntax is correct
3. Reload configuration: `reload_conf()`

### Key not found

Use `get_value()` with default:
```python
value = get_value('possibly.missing.key', default='fallback')
```

## Migration from Old Config

The old `config.py` with Pydantic Settings is still available for backward compatibility. New code should use `project_conf` for enhanced features:

```python
# Old way (still works)
from iptvportal.config import IPTVPortalSettings
settings = IPTVPortalSettings()

# New way (recommended)
from iptvportal.project_conf import get_conf
conf = get_conf()
```
