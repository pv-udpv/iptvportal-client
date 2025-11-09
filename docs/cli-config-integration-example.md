# CLI Configuration Integration Example

## How to Integrate CLISettings into Existing Commands

This guide shows practical examples of integrating the new `CLISettings` configuration system into existing CLI commands.

## Step 1: Update Command Signature

### Before (sql.py)

```python
@sql_app.callback(invoke_without_command=True)
def sql_main(
    ctx: typer.Context,
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    format: str = typer.Option("table", "--format", "-f"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    config_file: Optional[str] = typer.Option(None, "--config"),
) -> None:
    """Execute SQL query."""
    pass
```

### After (with CLISettings)

```python
from iptvportal.config import load_cli_config

@sql_app.callback(invoke_without_command=True)
def sql_main(
    ctx: typer.Context,
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    format: Optional[str] = typer.Option(None, "--format", "-f"),  # Now optional
    dry_run: Optional[bool] = typer.Option(None, "--dry-run"),  # Now optional
    limit: Optional[int] = typer.Option(None, "--limit"),  # Override auto-limit
    config_file: Optional[str] = typer.Option(None, "--config"),
) -> None:
    """Execute SQL query."""
    # Load configuration (file -> env -> defaults)
    cli_config = load_cli_config(config_file)
    
    # Use config defaults, allow CLI overrides
    output_format = format or cli_config.default_format
    dry_run_mode = dry_run if dry_run is not None else cli_config.dry_run_first
    
    # Rest of implementation...
```

## Step 2: Implement Guardrails

### Check LIMIT Requirements

```python
def validate_query_safety(query: str, cli_config: CLISettings) -> str:
    """
    Apply safety guardrails to SQL query.
    
    Returns:
        Modified query with applied guardrails
        
    Raises:
        typer.Exit if query violates safety rules
    """
    if not cli_config.enable_guardrails:
        return query
    
    query_upper = query.upper()
    
    # Check if SELECT query
    if query_upper.strip().startswith("SELECT"):
        # Require LIMIT?
        if cli_config.require_limit_on_select and "LIMIT" not in query_upper:
            if cli_config.default_limit:
                # Auto-add LIMIT
                console.print(
                    f"[yellow]Auto-adding LIMIT {cli_config.default_limit}[/yellow]"
                )
                query += f" LIMIT {cli_config.default_limit}"
            else:
                console.print(
                    "[bold red]Error:[/bold red] SELECT queries require LIMIT clause. "
                    f"Add LIMIT or set default_limit in config."
                )
                raise typer.Exit(1)
        
        # Check LIMIT value
        if "LIMIT" in query_upper:
            import re
            match = re.search(r"LIMIT\s+(\d+)", query_upper)
            if match:
                limit_value = int(match.group(1))
                
                # Check max limit
                if limit_value > cli_config.max_limit:
                    console.print(
                        f"[bold red]Error:[/bold red] LIMIT {limit_value} exceeds "
                        f"maximum of {cli_config.max_limit}"
                    )
                    raise typer.Exit(1)
                
                # Warn large limit
                if limit_value > cli_config.warn_large_limit:
                    console.print(
                        f"[yellow]Warning:[/yellow] LIMIT {limit_value} exceeds "
                        f"recommended threshold of {cli_config.warn_large_limit}"
                    )
    
    # Check destructive queries
    if any(query_upper.strip().startswith(cmd) for cmd in ["UPDATE", "DELETE"]):
        if "WHERE" not in query_upper:
            if cli_config.confirm_destructive_queries:
                if not typer.confirm(
                    f"⚠️  {query_upper.split()[0]} without WHERE affects ALL rows. Continue?"
                ):
                    console.print("[yellow]Query cancelled[/yellow]")
                    raise typer.Exit(0)
    
    return query


# Usage in sql_main:
def sql_main(...):
    cli_config = load_cli_config(config_file)
    
    # Apply guardrails
    query = validate_query_safety(sql_query, cli_config)
    
    # Continue with transpilation and execution...
```

### Confirm Large Updates

```python
def confirm_large_operation(
    row_count: int,
    operation: str,
    cli_config: CLISettings
) -> bool:
    """
    Confirm large UPDATE/DELETE operations.
    
    Args:
        row_count: Number of affected rows
        operation: "UPDATE" or "DELETE"
        cli_config: CLI configuration
        
    Returns:
        True if confirmed or not needed, False otherwise
    """
    if not cli_config.confirm_large_updates:
        return True
    
    if row_count > cli_config.large_update_threshold:
        return typer.confirm(
            f"⚠️  This {operation} will affect {row_count} rows. Continue?"
        )
    
    return True


# Usage:
def execute_update_query(query: str, cli_config: CLISettings):
    # First get count of affected rows (dry run)
    count_query = query.replace("UPDATE", "SELECT COUNT(*) FROM", 1)
    row_count = execute_count_query(count_query)
    
    # Confirm if large
    if not confirm_large_operation(row_count, "UPDATE", cli_config):
        console.print("[yellow]Update cancelled[/yellow]")
        raise typer.Exit(0)
    
    # Proceed with update
    result = execute_query(query)
    return result
```

## Step 3: Use Configuration for Output

### Format Results with Config

```python
def display_result_with_config(
    result: Any,
    cli_config: CLISettings,
    format_override: Optional[str] = None
) -> None:
    """Display query result using CLI configuration."""
    from rich.table import Table
    from rich.console import Console
    import time
    
    console = Console()
    output_format = format_override or cli_config.default_format
    
    # Show execution time if enabled
    start_time = time.time()
    
    # Format based on config
    if output_format == "table":
        table = Table(
            show_header=True,
            show_lines=cli_config.default_table_style in ["grid", "fancy_grid"],
            row_styles=["dim", ""] if cli_config.colorize_output else None,
        )
        
        # Truncate strings if enabled
        if cli_config.truncate_strings:
            result = truncate_result_strings(result, cli_config.max_string_length)
        
        # Add row numbers if enabled
        if cli_config.show_row_numbers:
            table.add_column("#", style="dim")
        
        # Add data columns
        for col in result.columns:
            table.add_column(col)
        
        # Add rows
        for idx, row in enumerate(result.rows):
            if cli_config.show_row_numbers:
                table.add_row(str(idx + 1), *row)
            else:
                table.add_row(*row)
        
        console.print(table)
    
    elif output_format == "json":
        format_json(result)
    elif output_format == "yaml":
        format_yaml(result)
    elif output_format == "csv":
        format_csv(result)
    
    # Show metrics if enabled
    if cli_config.show_execution_time:
        elapsed = time.time() - start_time
        console.print(f"\n[dim]Execution time: {elapsed:.3f}s[/dim]")
    
    if cli_config.show_row_count:
        console.print(f"[dim]Rows: {len(result.rows)}[/dim]")
```

## Step 4: Implement Caching

### Query Result Cache

```python
from functools import lru_cache
import hashlib
import pickle
from pathlib import Path

class QueryCache:
    """Simple query result cache."""
    
    def __init__(self, cli_config: CLISettings):
        self.config = cli_config
        self.cache_dir = Path(cli_config.cache_location).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, query: str) -> str:
        """Generate cache key from query."""
        return hashlib.sha256(query.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Any]:
        """Get cached result if available and not stale."""
        if not self.config.enable_query_cache:
            return None
        
        cache_key = self.get_cache_key(query)
        cache_file = self.cache_dir / f"{cache_key}.cache"
        
        if not cache_file.exists():
            return None
        
        # Check if stale
        import time
        age = time.time() - cache_file.stat().st_mtime
        if age > self.config.cache_ttl_seconds:
            cache_file.unlink()  # Remove stale cache
            return None
        
        # Load from cache
        try:
            return pickle.loads(cache_file.read_bytes())
        except Exception:
            cache_file.unlink()
            return None
    
    def set(self, query: str, result: Any) -> None:
        """Cache query result."""
        if not self.config.enable_query_cache:
            return
        
        cache_key = self.get_cache_key(query)
        cache_file = self.cache_dir / f"{cache_key}.cache"
        
        try:
            cache_file.write_bytes(pickle.dumps(result))
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to cache result: {e}[/yellow]")


# Usage in sql_main:
def sql_main(...):
    cli_config = load_cli_config(config_file)
    cache = QueryCache(cli_config)
    
    # Try cache first
    cached_result = cache.get(sql_query)
    if cached_result:
        console.print("[dim]Using cached result[/dim]")
        display_result_with_config(cached_result, cli_config)
        return
    
    # Execute query
    result = execute_query(sql_query)
    
    # Cache result
    cache.set(sql_query, result)
    
    display_result_with_config(result, cli_config)
```

## Step 5: Add Pager Support

### Use Pager for Large Outputs

```python
import subprocess
import os

def display_with_pager(
    content: str,
    cli_config: CLISettings
) -> None:
    """Display content using pager if enabled and threshold met."""
    lines = content.count('\n')
    
    # Check if pager should be used
    if not cli_config.use_pager or lines < cli_config.pager_threshold_lines:
        console.print(content)
        return
    
    # Get pager command
    pager_cmd = cli_config.pager_command
    if not pager_cmd:
        pager_cmd = os.environ.get('PAGER', 'less -R')
    
    try:
        # Use pager
        process = subprocess.Popen(
            pager_cmd.split(),
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=content)
    except Exception as e:
        # Fall back to direct print
        console.print(f"[yellow]Warning: Pager failed: {e}[/yellow]")
        console.print(content)
```

## Step 6: Complete Example

### Full Integration in sql.py

```python
"""SQL command with full CLISettings integration."""

from typing import Optional
import typer
from rich.console import Console

from iptvportal.config import load_cli_config, CLISettings
from iptvportal.jsonsql import SQLTranspiler
from iptvportal.cli.utils import execute_query

console = Console()

def validate_query_safety(query: str, cli_config: CLISettings) -> str:
    """Apply safety guardrails."""
    # Implementation from Step 2...
    return query

def display_result_with_config(result: Any, cli_config: CLISettings) -> None:
    """Display result using config."""
    # Implementation from Step 3...
    pass

@sql_app.callback(invoke_without_command=True)
def sql_main(
    ctx: typer.Context,
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    format: Optional[str] = typer.Option(None, "--format", "-f"),
    dry_run: Optional[bool] = typer.Option(None, "--dry-run"),
    config_file: Optional[str] = typer.Option(None, "--config"),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Execute SQL query with full configuration support."""
    
    try:
        # 1. Load configuration
        cli_config = load_cli_config(config_file)
        
        if cli_config.verbose:
            console.print(f"[dim]Loaded config from: {config_file or 'defaults'}[/dim]")
        
        # 2. Get query
        if not query:
            console.print("[red]Error: --query required[/red]")
            raise typer.Exit(1)
        
        # 3. Apply guardrails
        query = validate_query_safety(query, cli_config)
        
        # 4. Transpile
        transpiler = SQLTranspiler(
            dialect=cli_config.transpiler_dialect,
            auto_order_by_id=cli_config.auto_order_by_id
        )
        jsonsql = transpiler.transpile(query)
        
        # 5. Dry run if configured
        should_dry_run = dry_run if dry_run is not None else cli_config.dry_run_first
        if should_dry_run:
            console.print("[bold cyan]Dry Run - Transpiled Query:[/bold cyan]")
            console.print_json(data=jsonsql)
            return
        
        # 6. Check cache
        cache = QueryCache(cli_config) if not no_cache else None
        if cache:
            cached = cache.get(query)
            if cached:
                console.print("[dim]📦 Using cached result[/dim]")
                display_result_with_config(cached, cli_config, format)
                return
        
        # 7. Execute query
        import time
        start = time.time()
        
        result = execute_query(jsonsql)
        
        elapsed = time.time() - start
        
        # 8. Cache result
        if cache:
            cache.set(query, result)
        
        # 9. Display result
        display_result_with_config(result, cli_config, format)
        
        # 10. Show metrics
        if cli_config.show_execution_time:
            console.print(f"\n[dim]⏱️  {elapsed:.3f}s[/dim]")
        
        # 11. Notify if long query
        if cli_config.enable_notifications and elapsed > cli_config.notification_threshold_seconds:
            send_notification("Query Complete", f"Finished in {elapsed:.1f}s")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
```

## Configuration File Example

Create `~/.iptvportal/cli-config.yaml`:

```yaml
# Production-safe defaults
enable_guardrails: true
require_limit_on_select: true
default_limit: 100
max_limit: 1000
warn_large_limit: 500

# Output preferences
default_format: table
colorize_output: true
show_execution_time: true
show_row_count: true

# Performance
enable_query_cache: true
cache_ttl_seconds: 300
cache_location: ~/.iptvportal/cache

# Transpiler
transpiler_dialect: postgres
auto_order_by_id: true

# Safety
confirm_destructive_queries: true
confirm_large_updates: true
large_update_threshold: 50
```

## Testing the Integration

```bash
# 1. Create config
python -c "from iptvportal.config import create_default_cli_config; create_default_cli_config()"

# 2. Edit ~/.iptvportal/cli-config.yaml to your preferences

# 3. Test with default config
iptvportal sql -q "SELECT * FROM subscriber"
# Auto-adds LIMIT 100 (from default_limit)

# 4. Override with flag
iptvportal sql -q "SELECT * FROM subscriber LIMIT 500" --format json

# 5. Use different profile
iptvportal sql --config ./prod-config.yaml -q "SELECT * FROM subscriber"

# 6. Test caching
iptvportal sql -q "SELECT COUNT(*) FROM subscriber"
# Second run uses cache (shows "📦 Using cached result")
```

## Summary

This integration provides:

1. **Backward compatibility** - CLI flags still work
2. **Configuration precedence** - CLI > Env > File > Defaults
3. **Safety guardrails** - Automatic checks and confirmations
4. **Performance** - Caching and optimization
5. **User experience** - Customizable output and behavior
6. **Flexibility** - Multiple profiles for different scenarios

The key is to load `CLISettings` early, apply its defaults, allow CLI overrides, and use it throughout the command execution pipeline.
