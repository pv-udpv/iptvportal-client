# CLI Architecture - Service-Oriented Design

## Overview

The IPTVPortal CLI uses a service-oriented architecture with automatic service discovery. Each service is implemented as a Python package with a `__cli__.py` module that exposes a Typer app.

## Service Discovery

The CLI automatically discovers and registers services at startup using the `discover_cli_modules()` function:

```python
from iptvportal.cli.discovery import discover_cli_modules

# Auto-discover all services in iptvportal package
discovered = discover_cli_modules("iptvportal", verbose=False)

# Each service becomes a top-level CLI command
for service_name, service_app in discovered.items():
    app.add_typer(service_app, name=service_name)
```

### Discovery Convention

A service is any package under `iptvportal/` that contains a `__cli__.py` module with an `app` attribute:

```
src/iptvportal/
├── cache/
│   ├── __init__.py
│   └── __cli__.py         # Exports: app = typer.Typer(...)
├── schema/
│   ├── __init__.py
│   └── __cli__.py         # Exports: app = typer.Typer(...)
├── jsonsql/
│   ├── __init__.py
│   └── __cli__.py         # Exports: app = typer.Typer(...)
└── config/
    ├── __init__.py
    └── __cli__.py         # Exports: app = typer.Typer(...)
```

## Service Structure

### Available Services

#### 1. **config** - Global Configuration Management
- Location: `src/iptvportal/config/__cli__.py`
- Commands: `show`, `get`, `set`, `init`, `conf`, `inspect`
- Purpose: Manage global application settings and dynaconf integration

#### 2. **cache** - Query Result Cache Management
- Location: `src/iptvportal/cache/__cli__.py`
- Commands: `status`, `clear`, `vacuum`
- Config: `cache config show/get/set`
- Purpose: Manage in-memory query result cache

#### 3. **schema** - Table Schema Management
- Location: `src/iptvportal/schema/__cli__.py`
- Commands: `list`, `show`, `introspect`, `validate`, `export`, etc.
- Config: `schema config show/get/set`
- Purpose: Manage table field mappings and metadata

#### 4. **jsonsql** - API Operations
- Location: `src/iptvportal/jsonsql/__cli__.py`
- Subcommands:
  - `auth` - Authentication management
  - `sql` - SQL query execution (subapp)
  - `select/insert/update/delete` - Native JSONSQL operations
  - `utils` - Offline utilities (transpile, validate, format)
  - `config` - JSONSQL/API configuration
- Purpose: All API-related operations

#### 5. **sync** - SQLite Sync Cache Management
- Location: `src/iptvportal/cli/commands/sync.py`
- Commands: `init`, `register`, `run`, `status`, `clear`, etc.
- Purpose: Manage local SQLite sync cache
- Note: Not auto-discovered; manually registered for backwards compatibility

## Hierarchical Configuration

Each service can have its own `config` subcommand for service-specific settings:

```bash
# Global configuration
iptvportal config show

# Service-specific configuration
iptvportal cache config show      # Cache-specific settings
iptvportal schema config show     # Schema-specific settings
iptvportal jsonsql config show    # JSONSQL/API settings
```

### Configuration Precedence

Configuration is resolved with the following precedence (highest to lowest):

1. **Runtime flags**: `--timeout 60`
2. **Service config**: `iptvportal cache config set timeout 60`
3. **Global config**: `iptvportal config set timeout 30`
4. **Defaults**: From `config/settings.yaml`

Example:
```bash
# Set global timeout
iptvportal config set timeout 30

# Override for cache service
iptvportal cache config set timeout 60

# Override at runtime
iptvportal cache status --timeout 120
```

## Creating a New Service

To add a new service to the CLI:

1. **Create a package under `src/iptvportal/`**:
   ```bash
   mkdir -p src/iptvportal/myservice
   touch src/iptvportal/myservice/__init__.py
   ```

2. **Create `__cli__.py` with service commands**:
   ```python
   # src/iptvportal/myservice/__cli__.py
   import typer
   from rich.console import Console

   console = Console()
   app = typer.Typer(name="myservice", help="My service description")

   @app.command()
   def status() -> None:
       """Show service status."""
       console.print("[green]Service is running[/green]")

   # Optional: Add config subcommand
   config_app = typer.Typer(name="config", help="Service configuration")

   @config_app.command(name="show")
   def config_show() -> None:
       """Show service configuration."""
       console.print("Service config here")

   app.add_typer(config_app)
   ```

3. **Service is auto-discovered**:
   ```bash
   iptvportal myservice status
   iptvportal myservice config show
   ```

No registration code needed - the discovery system handles it automatically!

## Benefits

### Convention over Configuration
- No manual registration of services
- Consistent structure across all services
- Easy to understand and maintain

### Modularity
- Each service is self-contained
- Services can be developed independently
- Easy to add or remove services

### Consistency
- All services follow the same patterns
- Predictable command structure
- Uniform help text and error handling

### Scalability
- Add new services without modifying core CLI code
- Services can have complex subcommand hierarchies
- Each service can have its own configuration

## Migration Notes

### Old Structure → New Structure

| Old Command | New Command |
|------------|-------------|
| `iptvportal auth` | `iptvportal jsonsql auth` |
| `iptvportal transpile <sql>` | `iptvportal jsonsql utils transpile <sql>` |
| `iptvportal sql -q <sql>` | `iptvportal jsonsql sql -q <sql>` |

### Backwards Compatibility

For backwards compatibility during transition:
- Old command imports can remain in `cli/commands/`
- Services can import and re-export from old locations
- Deprecation warnings can be added gradually

## Technical Implementation

### Auto-Discovery Function

```python
# src/iptvportal/cli/discovery.py
def discover_cli_modules(
    package_name: str = "iptvportal",
    verbose: bool = False,
) -> dict[str, Any]:
    """Auto-discover __cli__.py modules in all subpackages."""
    discovered = {}
    
    package = importlib.import_module(package_name)
    package_path = Path(package.__file__).parent
    
    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
        if is_pkg:
            cli_module_name = f"{package_name}.{module_name}.__cli__"
            try:
                cli_module = importlib.import_module(cli_module_name)
                if hasattr(cli_module, "app"):
                    discovered[module_name] = cli_module.app
            except (ImportError, AttributeError):
                pass  # No __cli__.py or no app attribute
    
    return discovered
```

### Main CLI Integration

```python
# src/iptvportal/cli/__main__.py
from iptvportal.cli.discovery import discover_cli_modules

app = typer.Typer(
    name="iptvportal",
    help="IPTVPortal JSONSQL API Client CLI",
    no_args_is_help=True,
)

# Auto-discover and register all service CLI modules
discovered = discover_cli_modules("iptvportal", verbose=False)
for service_name, service_app in discovered.items():
    app.add_typer(service_app, name=service_name)
```

## Testing

Services should include their own tests:

```python
# tests/test_myservice_cli.py
from typer.testing import CliRunner
from iptvportal.cli.__main__ import app

runner = CliRunner()

def test_myservice_status():
    """Test myservice status command."""
    result = runner.invoke(app, ["myservice", "status"])
    assert result.exit_code == 0
    assert "running" in result.stdout.lower()
```

## Future Enhancements

Potential improvements to the service architecture:

1. **Service Metadata**: Add version, author, and dependencies to `__cli__.py`
2. **Service Discovery Hooks**: Allow services to register initialization hooks
3. **Service Dependencies**: Define inter-service dependencies
4. **Dynamic Service Loading**: Load services from external packages
5. **Service Configuration Schema**: Define and validate service-specific config
6. **Service Health Checks**: Built-in health check commands for all services
7. **Service Documentation**: Auto-generate docs from service commands

## See Also

- [CLI Commands Reference](cli.md) - Complete command documentation
- [Configuration Guide](configuration.md) - Configuration system details
- [Architecture Overview](architecture.md) - Overall system architecture
