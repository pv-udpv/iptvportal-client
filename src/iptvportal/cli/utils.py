"""CLI utilities and helpers."""

import json
from typing import Any

import orjson
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from iptvportal.client import IPTVPortalClient
from iptvportal.config import IPTVPortalSettings

console = Console()


def load_config(config_file: str | None = None) -> IPTVPortalSettings:
    """
    Load configuration from file or environment.
    
    Args:
        config_file: Optional path to config file
        
    Returns:
        IPTVPortalSettings instance
    """
    if config_file:
        # TODO: Load from YAML file when needed
        pass

    return IPTVPortalSettings()


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


def build_jsonrpc_request(method: str, params: dict[str, Any], request_id: int = 1) -> dict[str, Any]:
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
        return params.get("from")
    if method == "insert":
        return params.get("into")
    if method in ("update", "delete"):
        return params.get("table")

    # Fallback: try common keys
    for key in ("from", "table", "into"):
        if key in params:
            value = params[key]
            # Handle if it's a string (table name)
            if isinstance(value, str):
                return value.lower()

    return None

def execute_query(
    method: str,
    params: dict[str, Any],
    config_file: str | None = None,
    use_schema_mapping: bool = False,
) -> Any:
    """
    Execute query through IPTVPortal client.
    
    Args:
        method: Query method (select, insert, update, delete)
        params: Query parameters
        config_file: Optional config file path
        use_schema_mapping: Whether to use schema-based result mapping
        
    Returns:
        Query result (raw or schema-mapped)
    """
    settings = load_config(config_file)

    with IPTVPortalClient(settings) as client:
        request = build_jsonrpc_request(method, params)

        # Use schema mapping if enabled and schemas are available
        if use_schema_mapping and method == "select":
            # Extract table name from params
            table_name = extract_table_name(params, method)

            if not table_name:
                console.print("[yellow]Warning: Could not extract table name for schema mapping[/yellow]")
                return client.execute(request)

            # Check if schema exists for this table
            if client.schema_registry.has(table_name):
                console.print(f"[dim]Using existing schema for table: {table_name}[/dim]")
                return client.execute_mapped(request, table_name=table_name)
            # Auto-generate schema from first result row
            console.print(f"[cyan]Auto-generating schema for table: {table_name}[/cyan]")

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

                # Register for future use
                client.schema_registry.register(schema)

                console.print(f"[green]✓ Generated schema with {schema.total_fields} fields[/green]")

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
