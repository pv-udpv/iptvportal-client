# Configuration Generation (`config generate`)

## Overview

The `iptvportal config generate` command (formerly `inspect`) is a code introspection tool that scans Python modules for settings classes (Pydantic BaseSettings, dynaconf configurations) and generates corresponding YAML configuration files. It can also generate example configuration templates.

## Usage

```bash
iptvportal config generate [OPTIONS]
```

## Options

- `--scope TEXT`: Directory to start scanning for settings classes (default: `src`)
- `--ignore TEXT`: Patterns to ignore during scanning (can be specified multiple times)
- `--settings-context TEXT`: Base path in settings tree where discovered settings should be attached (e.g., `sync`, `cli.advanced`)
- `--strategy [single|per-module|file-per-module]`: File generation strategy (default: `file-per-module`)
  - `single`: Generate one settings.yaml with all settings
  - `per-module`: Generate one file per Python module
  - `file-per-module`: Generate one file per settings class
- `--output TEXT, -o TEXT`: Output directory for generated configuration files (default: `config/generated`)
- `--template TEXT`: Generate template: env, yaml (overrides code scanning)
- `--dry-run`: Show what would be generated without creating files

## Examples

### Basic Usage

Scan the `src` directory and generate one file per settings class:

```bash
iptvportal config generate
```

Output:
```
Configuration Inspection

Scanning: /path/to/src
Ignoring: test_*, *_test.py, __pycache__, .*
Strategy: file-per-module

Found 2 settings class(es):

┌──────────────────────┬─────────────────────┬────────┐
│ Class                │ Module              │ Fields │
├──────────────────────┼─────────────────────┼────────┤
│ IPTVPortalSettings   │ iptvportal.config   │ 34     │
│ CLISettings          │ iptvportal.config   │ 58     │
└──────────────────────┴─────────────────────┴────────┘

✓ Generated 2 file(s) in config/generated

  • config/generated/iptv_portal.settings.yaml
  • config/generated/cli.settings.yaml
```

### Scan Specific Directory

Scan a specific module directory:

```bash
iptvportal config generate --scope src/iptvportal/sync --output config/sync
```

### Generate Single File

Generate a single settings.yaml with all discovered settings:

```bash
iptvportal config generate --strategy single --output config
```

### Ignore Test Files

Explicitly ignore test files and specific patterns:

```bash
iptvportal config generate --ignore "test_*" --ignore "*_test.py" --ignore "conftest.py"
```

### Settings Context

Attach discovered settings to a specific path in the settings tree:

```bash
iptvportal config generate --settings-context sync.advanced
```

This will nest all generated settings under `sync.advanced` in the YAML:

```yaml
sync:
  advanced:
    subscriber:
      field1: value1
      field2: value2
```

### Dry Run

Preview what would be generated without creating files:

```bash
iptvportal config generate --dry-run
```

Output:
```
Configuration Inspection

... (scanning output) ...

Dry run - no files will be created

Would generate:

• IPTVPortalSettings
  iptvportal.config
  IPTVPortal API client configuration.
  Fields: domain, username, password, timeout, max_retries
    ...and 29 more

• CLISettings
  iptvportal.config
  CLI-specific configuration with defaults and guardrails.
  Fields: default_format, default_table_style, max_table_width, truncate_strings, max_string_length
    ...and 53 more
```

### Strategy Options

#### file-per-module (default)

One YAML file per settings class:

```bash
iptvportal config generate --strategy file-per-module
```

Output:
```
config/generated/
├── iptv_portal.settings.yaml
└── cli.settings.yaml
```

#### per-module

One YAML file per Python module (all classes from the same module in one file):

```bash
iptvportal config generate --strategy per-module
```

Output:
```
config/generated/
└── config.settings.yaml  # Contains both IPTVPortalSettings and CLISettings
```

#### single

One settings.yaml with all discovered settings:

```bash
iptvportal config generate --strategy single
```

Output:
```
config/generated/
└── settings.yaml  # Contains all settings from all classes
```

## Generated File Format

Generated YAML files include:
- Header comment with source module and class
- Docstring from the settings class (if present)
- All fields with their default values or type-appropriate placeholders

Example generated file:

```yaml
# Generated from: iptvportal.config.IPTVPortalSettings
# IPTVPortal API client configuration.
# 
# Configuration is loaded from:
# - Environment variables (IPTVPORTAL_ prefix)
# - .env file
# - Direct constructor arguments

domain: ''
username: ''
password: ''
timeout: 30.0
max_retries: 3
retry_delay: 1.0
verify_ssl: true
session_cache: true
session_ttl: 3600
log_level: INFO
log_requests: false
log_responses: false
# ... more fields ...
```

## Use Cases

### 1. Initial Configuration Setup

Generate configuration files from existing settings classes:

```bash
iptvportal config generate --output config/schemas
```

### 2. Documentation

Generate YAML examples for documentation:

```bash
iptvportal config generate --strategy single --dry-run > docs/config-reference.txt
```

### 3. Migration

Generate configuration files when migrating from hardcoded settings to file-based config:

```bash
iptvportal config generate --scope src/old_module --output config/migrated
```

### 4. Module-Specific Config

Generate configuration for a specific module:

```bash
iptvportal config generate --scope src/iptvportal/sync --settings-context sync
```

## Tips

1. **Review Generated Files**: Always review and adjust generated files before using them in production
2. **Use --dry-run**: Preview generation before creating files
3. **Ignore Patterns**: Use `--ignore` to skip test files, __pycache__, etc.
4. **Settings Context**: Use `--settings-context` to organize generated settings in a hierarchy
5. **Strategy Selection**: 
   - Use `file-per-module` for granular control
   - Use `per-module` to group related settings
   - Use `single` for simple projects

## Integration with Dynaconf

Generated files can be used with the dynaconf-based configuration system:

1. Generate configuration files:
   ```bash
   iptvportal config generate --output config/schemas
   ```

2. Review and adjust the generated files

3. The files are automatically discovered and loaded by `project_conf.py`:
   ```python
   from iptvportal.project_conf import get_conf
   
   conf = get_conf()
   # Access generated settings
   ```

4. View loaded configuration:
   ```bash
   iptvportal config show --files
   ```

## Template Generation

Generate example configuration templates without code scanning:

### Generate .env Template

```bash
# Generate .env example in current directory
iptvportal config generate --template env

# Custom output location
iptvportal config generate --template env --output .env.production
```

### Generate YAML Template

```bash
# Generate YAML example
iptvportal config generate --template yaml

# Custom output location
iptvportal config generate --template yaml --output config/custom.yaml
```

These templates provide starting points for configuration without needing to scan code.

## Troubleshooting

### No Settings Classes Found

If no settings classes are discovered:
- Check that your settings classes inherit from `BaseSettings`
- Verify the `--scope` path is correct
- Ensure Python files are not being ignored

### Import Errors

The command uses AST parsing, so it doesn't require importing modules. If you see import errors, they are from other parts of the CLI and can be ignored for the inspect command.

### YAML Serialization Errors

If generated YAML has issues:
- Check for non-serializable default values in your settings classes
- Review the generated file and adjust manually if needed

## See Also

- `iptvportal config show` - View current configuration
- `iptvportal config validate` - Validate configuration
- [Configuration Documentation](configuration.md)
