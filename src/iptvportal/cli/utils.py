"""CLI utilities and helpers."""

import json
from typing import Any

import orjson
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from iptvportal.config.settings import IPTVPortalSettings
from iptvportal.core.client import IPTVPortalClient

console = Console()


def load_config(config_file: str | None = None) -> IPTVPortalSettings:
    """
    Load configuration from file or environment using Dynaconf.

    Args:
        config_file: Optional path to config file (currently unused, uses Dynaconf auto-discovery)

    Returns:
        IPTVPortalSettings instance populated from Dynaconf configuration
    """
    from pathlib import Path
    from iptvportal.config.project import get_conf
    
    # Get Dynaconf configuration
    conf = get_conf()
    
    # Map Dynaconf settings to IPTVPortalSettings
    # Priority: explicit values from config > environment variables > defaults
    settings_kwargs = {}
    
    # Core connection parameters - try top-level first, then core.* namespace
    settings_kwargs["domain"] = conf.get("domain") or conf.get("core.domain", "")
    settings_kwargs["username"] = conf.get("username") or conf.get("core.username", "")
    settings_kwargs["password"] = conf.get("password") or conf.get("core.password", "")
    
    # HTTP settings
    settings_kwargs["timeout"] = float(conf.get("timeout") or conf.get("core.timeout", 30.0))
    settings_kwargs["max_retries"] = int(conf.get("max_retries") or conf.get("core.max_retries", 3))
    settings_kwargs["retry_delay"] = float(conf.get("core.retry_delay", 1.0))
    settings_kwargs["verify_ssl"] = bool(conf.get("verify_ssl") if conf.get("verify_ssl") is not None else conf.get("core.verify_ssl", True))
    
    # Session management
    settings_kwargs["session_cache"] = bool(conf.get("core.session_cache", True))
    settings_kwargs["session_ttl"] = int(conf.get("core.session_ttl", 3600))
    
    # Logging
    settings_kwargs["log_level"] = conf.get("core.log_level", "INFO")
    settings_kwargs["log_requests"] = bool(conf.get("core.log_requests", False))
    settings_kwargs["log_responses"] = bool(conf.get("core.log_responses", False))
    
    # Schema configuration - from adapters namespace
    # Resolve schema_file path relative to current working directory
    schema_file = conf.get("adapters.schema_file")
    if schema_file:
        schema_path = Path(schema_file)
        # If relative path, resolve from current working directory
        if not schema_path.is_absolute():
            schema_path = Path.cwd() / schema_path
        # Only set if the file exists, otherwise leave as None to avoid errors
        if schema_path.exists():
            settings_kwargs["schema_file"] = str(schema_path)
        else:
            # Try as-is (maybe it's relative to execution context)
            settings_kwargs["schema_file"] = schema_file
    else:
        settings_kwargs["schema_file"] = None
    
    settings_kwargs["schema_format"] = conf.get("adapters.schema_format", "yaml")
    settings_kwargs["auto_load_schemas"] = bool(conf.get("adapters.auto_load_schemas", True))
    
    # Query caching - from adapters namespace
    settings_kwargs["enable_query_cache"] = bool(conf.get("adapters.enable_query_cache", True))
    settings_kwargs["cache_ttl"] = int(conf.get("adapters.cache_ttl", 300))
    settings_kwargs["cache_max_size"] = int(conf.get("adapters.cache_max_size", 1000))
    
    # Query optimization
    settings_kwargs["auto_order_by_id"] = bool(conf.get("adapters.auto_order_by_id") if conf.get("adapters.auto_order_by_id") is not None else conf.get("cli.auto_order_by_id", True))
    
    # SQLite cache settings - from sync namespace
    settings_kwargs["cache_db_path"] = conf.get("sync.cache_db_path", "~/.iptvportal/cache.db")
    settings_kwargs["enable_persistent_cache"] = bool(conf.get("sync.enable_persistent_cache", True))
    settings_kwargs["cache_db_journal_mode"] = conf.get("sync.cache_db_journal_mode", "WAL")
    settings_kwargs["cache_db_page_size"] = int(conf.get("sync.cache_db_page_size", 4096))
    settings_kwargs["cache_db_cache_size"] = int(conf.get("sync.cache_db_cache_size", -64000))
    
    # Sync behavior
    settings_kwargs["default_sync_strategy"] = conf.get("sync.default_sync_strategy", "full")
    settings_kwargs["default_sync_ttl"] = int(conf.get("sync.default_sync_ttl", 3600))
    settings_kwargs["default_chunk_size"] = int(conf.get("sync.default_chunk_size", 1000))
    settings_kwargs["auto_sync_on_startup"] = bool(conf.get("sync.auto_sync_on_startup", False))
    settings_kwargs["auto_sync_stale_tables"] = bool(conf.get("sync.auto_sync_stale_tables", True))
    settings_kwargs["max_concurrent_syncs"] = int(conf.get("sync.max_concurrent_syncs", 3))
    
    # Maintenance
    settings_kwargs["auto_vacuum_enabled"] = bool(conf.get("sync.auto_vacuum_enabled", True))
    settings_kwargs["vacuum_threshold_mb"] = int(conf.get("sync.vacuum_threshold_mb", 100))
    settings_kwargs["auto_analyze_enabled"] = bool(conf.get("sync.auto_analyze_enabled", True))
    settings_kwargs["analyze_interval_hours"] = int(conf.get("sync.analyze_interval_hours", 24))
    
    return IPTVPortalSettings(**settings_kwargs)


def parse_json_param(param: str | None) -> Any:
    """
    Parse JSON string parameter.

    Args:
        param: JSON string

    Returns:
        Parsed Python object
    """
    if param is None:
        return None

    try:
        return orjson.loads(param)
    except Exception as e:
        console.print(f"[red]Error parsing JSON:[/red] {e}")
        raise


def build_jsonrpc_request(
    method: str, params: dict[str, Any], request_id: int = 1
) -> dict[str, Any]:
    """
    Build JSON-RPC 2.0 request.

    Args:
        method: RPC method name
        params: Method parameters
        request_id: Request ID

    Returns:
        JSON-RPC request dict
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }


def extract_table_name(params: dict[str, Any], method: str) -> str | None:
    """
    Extract table name from query parameters.

    Args:
        params: Query parameters (JSONSQL)
        method: Query method (select, insert, update, delete)

    Returns:
        Table name or None if not found
    """
    # Try different parameter keys based on method
    if method == "select":
        from_value = params.get("from")
        # Handle JOIN queries where from is a list
        if isinstance(from_value, list):
            if from_value and isinstance(from_value[0], dict):
                # Extract table name from first element
                return from_value[0].get("table")
            return None
        return from_value
    if method == "insert":
        return params.get("into")
    if method in ("update", "delete"):
        return params.get("table")

    # Fallback: try common keys
    for key in ("from", "table", "into"):
        if key in params:
            value = params[key]
            # Handle if it's a list (JOIN queries)
            if isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Extract table name from first element
                    table_name = value[0].get("table")
                    if table_name:
                        return table_name.lower()
            # Handle if it's a string (table name)
            elif isinstance(value, str):
                return value.lower()

    return None


def execute_query(
    method: str,
    params: dict[str, Any],
    config_file: str | None = None,
    use_schema_mapping: bool = False,
    debug_logger: Any = None,
) -> Any:
    """
    Execute query through IPTVPortal client.

    Args:
        method: Query method (select, insert, update, delete)
        params: Query parameters
        config_file: Optional config file path
        use_schema_mapping: Whether to use schema-based result mapping
        debug_logger: Optional debug logger instance

    Returns:
        Query result (raw or schema-mapped)
    """
    settings = load_config(config_file)

    if debug_logger:
        debug_logger.log("config", settings.model_dump(), "Configuration")

    with IPTVPortalClient(settings) as client:
        request = build_jsonrpc_request(method, params)

        if debug_logger:
            debug_logger.log("jsonrpc_request", request, "JSON-RPC Request")

        # Use schema mapping if enabled and schemas are available
        if use_schema_mapping and method == "select":
            # Extract table name from params
            table_name = extract_table_name(params, method)

            if debug_logger:
                debug_logger.log("table_name", table_name, "Extracted Table Name")

            if not table_name:
                console.print(
                    "[yellow]Warning: Could not extract table name for schema mapping[/yellow]"
                )
                return client.execute(request)

            # Check if schema exists for this table
            if client.schema_registry.has(table_name):
                console.print(f"[dim]Using existing schema for table: {table_name}[/dim]")
                if debug_logger:
                    debug_logger.log("schema_status", "using_existing", "Schema Status")
                return client.execute_mapped(request, table_name=table_name)
            # Auto-generate schema from first result row
            console.print(f"[cyan]Auto-generating schema for table: {table_name}[/cyan]")

            if debug_logger:
                debug_logger.log("schema_status", "auto_generating", "Schema Status")

            # Execute query to get sample result
            result = client.execute(request)

            # Check if we have results to generate schema from
            if result and isinstance(result, list) and len(result) > 0:
                # Import TableSchema here to avoid circular imports
                from iptvportal.schema import TableSchema

                # Get first row as sample
                sample_row = result[0]

                # Auto-generate schema
                schema = TableSchema.auto_generate(table_name, sample_row)

                if debug_logger:
                    debug_logger.log(
                        "generated_schema",
                        {
                            "table": table_name,
                            "total_fields": schema.total_fields,
                            "fields": list(schema.fields.keys()),
                        },
                        "Generated Schema",
                    )

                # Register for future use
                client.schema_registry.register(schema)

                console.print(
                    f"[green]✓ Generated schema with {schema.total_fields} fields[/green]"
                )

                # Map all results using the generated schema
                return [schema.map_row_to_dict(row) for row in result]
            console.print("[yellow]Warning: No results to generate schema from[/yellow]")
            return result

        return client.execute(request)


def display_json(data: Any, title: str | None = None) -> None:
    """
    Display data as formatted JSON with syntax highlighting.

    Args:
        data: Data to display
        title: Optional title
    """
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)


def display_error(message: str, exception: Exception | None = None) -> None:
    """
    Display error message.

    Args:
        message: Error message
        exception: Optional exception object
    """
    console.print(f"[bold red]Error:[/bold red] {message}")
    if exception:
        console.print(f"[red]{exception}[/red]")
