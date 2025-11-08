"""Output formatters for CLI."""

import json
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

def format_table(data: list[dict[str, Any]], title: str | None = None) -> None:
    """
    Display data as a table.
    
    Args:
        data: List of dictionaries to display
        title: Optional table title
    """
    if not data:
        console.print("[yellow]No results[/yellow]")
        return

    # Get columns from first row
    columns = list(data[0].keys())

    # Create table
    table = Table(title=title, show_header=True, header_style="bold cyan")

    for col in columns:
        table.add_column(col, style="white")

    # Add rows
    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)

def format_json(data: Any, title: str | None = None) -> None:
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

def format_yaml(data: Any, title: str | None = None) -> None:
    """
    Display data as formatted YAML with syntax highlighting.
    
    Args:
        data: Data to display
        title: Optional title
    """
    yaml_str = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)

    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)

def display_result(result: Any, format_type: str = "table") -> None:
    """
    Display query result in specified format.
    
    Args:
        result: Query result
        format_type: Output format (table, json, yaml)
    """
    if format_type == "json":
        format_json(result)
    elif format_type == "yaml":
        format_yaml(result)
    elif format_type == "table":
        if isinstance(result, list) and result and isinstance(result[0], dict):
            format_table(result)
        else:
            # Fallback to JSON for non-tabular data
            format_json(result)
    else:
        console.print(f"[red]Unknown format: {format_type}[/red]")

def display_dry_run(
    jsonsql: dict[str, Any],
    method: str,
    sql: str | None = None,
    format_type: str = "json",
) -> None:
    """
    Display dry-run information.
    
    Args:
        jsonsql: JSONSQL query
        method: Query method
        sql: Original SQL query (if from --from-sql)
        format_type: Output format
    """
    console.print("\n[bold yellow]DRY RUN MODE[/bold yellow]\n")

    if sql:
        console.print("[bold]SQL Input:[/bold]")
        syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print()

    console.print("[bold]Transpiled JSONSQL:[/bold]")
    if format_type == "yaml":
        format_yaml(jsonsql)
    else:
        format_json(jsonsql)

    console.print()
    console.print("[bold]JSON-RPC Request:[/bold]")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": jsonsql,
    }

    if format_type == "yaml":
        format_yaml(request)
    else:
        format_json(request)

    console.print()
    console.print("[yellow]→ Query will NOT be executed (dry-run mode)[/yellow]\n")

def display_request_and_result(
    jsonsql: dict[str, Any],
    method: str,
    result: Any,
    sql: str | None = None,
    format_type: str = "json",
) -> None:
    """
    Display JSON-RPC request and query result.
    
    Args:
        jsonsql: JSONSQL query
        method: Query method
        result: Query result
        sql: Original SQL query (if from SQL mode)
        format_type: Output format
    """
    console.print("\n[bold cyan]REQUEST[/bold cyan]\n")

    if sql:
        console.print("[bold]SQL Input:[/bold]")
        syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print()

    console.print("[bold]JSON-RPC Request:[/bold]")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": jsonsql,
    }

    if format_type == "yaml":
        format_yaml(request)
    else:
        format_json(request)

    console.print("\n[bold cyan]RESULT[/bold cyan]\n")
    display_result(result, format_type)
