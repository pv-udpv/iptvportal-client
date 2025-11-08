"""JSONSQL commands (select, insert, update, delete)."""

import json
from typing import Optional

import typer
from rich.console import Console

from iptvportal.cli.utils import parse_json_param, execute_query
from iptvportal.cli.formatters import display_result, display_dry_run, display_request_and_result
from iptvportal.cli.core.editor import open_jsonsql_editor
from iptvportal.exceptions import IPTVPortalError

console = Console()
jsonsql_app = typer.Typer(name="jsonsql", help="Execute native JSONSQL queries")

def build_select_params(
    data: Optional[str],
    from_: Optional[str],
    where: Optional[str],
    order_by: Optional[str],
    limit: Optional[int],
    offset: Optional[int],
    distinct: bool,
    group_by: Optional[str],
) -> dict:
    """Build SELECT query parameters."""
    params = {}
    
    if data:
        # Parse comma-separated columns
        params["data"] = [col.strip() for col in data.split(",")]
    else:
        params["data"] = ["*"]
    
    if from_:
        params["from"] = from_
    
    if where:
        params["where"] = parse_json_param(where)
    
    if order_by:
        params["order_by"] = order_by
    
    if limit is not None:
        params["limit"] = limit
    
    if offset is not None:
        params["offset"] = offset
    
    if distinct:
        params["distinct"] = True
    
    if group_by:
        params["group_by"] = group_by
    
    return params

@jsonsql_app.command(name="select")
def select_command(
    # Native JSONSQL parameters
    data: Optional[str] = typer.Option(None, "--data", help="Columns to select (comma-separated)"),
    from_: Optional[str] = typer.Option(None, "--from", help="Table name"),
    where: Optional[str] = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    order_by: Optional[str] = typer.Option(None, "--order-by", help="ORDER BY column"),
    limit: Optional[int] = typer.Option(None, "--limit", help="LIMIT rows"),
    offset: Optional[int] = typer.Option(None, "--offset", help="OFFSET rows"),
    distinct: bool = typer.Option(False, "--distinct", help="SELECT DISTINCT"),
    group_by: Optional[str] = typer.Option(None, "--group-by", help="GROUP BY column"),
    
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(False, "--show-request", help="Show JSON-RPC request along with result"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, yaml"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Execute SELECT query.
    
    Examples:
        # Native JSONSQL mode
        iptvportal jsonsql select --data "id,username" --from subscriber --limit 10
        iptvportal jsonsql select --from subscriber --where '{"eq": ["disabled", false]}'
        
        # Editor mode
        iptvportal jsonsql select --edit
        
        # With dry-run
        iptvportal jsonsql select --from subscriber --limit 5 --dry-run
    """
    try:
        if edit:
            # Editor mode: open editor for JSONSQL input
            if any([data, from_, where, order_by, limit, offset, distinct, group_by]):
                console.print("[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]")
            
            # Provide template
            template = json.dumps({
                "data": ["*"],
                "from": "table_name",
                "where": {"eq": ["column", "value"]},
                "limit": 10
            }, indent=2)
            
            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
        else:
            # Native mode: build JSONSQL from parameters
            if not from_:
                console.print("[red]Error: --from is required when not using --edit[/red]")
                raise typer.Exit(1)
            
            params = build_select_params(data, from_, where, order_by, limit, offset, distinct, group_by)
        
        if dry_run:
            # Show what would be executed
            display_dry_run(params, "select", sql=None, format_type=format)
        else:
            # Execute query
            result = execute_query("select", params, config_file)
            
            if show_request:
                # Show request and result
                display_request_and_result(params, "select", result, sql=None, format_type=format)
            else:
                # Show only result
                display_result(result, format)
            
    except IPTVPortalError as e:
        console.print(f"[bold red]Query failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)

@jsonsql_app.command(name="insert")
def insert_command(
    # Native JSONSQL parameters
    into: Optional[str] = typer.Option(None, "--into", help="Table name"),
    columns: Optional[str] = typer.Option(None, "--columns", help="Column names (comma-separated)"),
    values: Optional[str] = typer.Option(None, "--values", help="Values (JSON array of arrays)"),
    returning: Optional[str] = typer.Option(None, "--returning", help="Columns to return"),
    
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(False, "--show-request", help="Show JSON-RPC request along with result"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Execute INSERT query.
    
    Examples:
        # Native mode
        iptvportal jsonsql insert --into package --columns "name,paid" --values '[["movie", true]]' --returning id
        
        # Editor mode
        iptvportal jsonsql insert --edit
    """
    try:
        if edit:
            # Editor mode
            if any([into, columns, values, returning]):
                console.print("[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]")
            
            template = json.dumps({
                "into": "table_name",
                "columns": ["column1", "column2"],
                "values": [["value1", "value2"]],
                "returning": "id"
            }, indent=2)
            
            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
        else:
            # Native mode
            if not into or not columns or not values:
                console.print("[red]Error: --into, --columns, and --values are required when not using --edit[/red]")
                raise typer.Exit(1)
            
            params = {
                "into": into,
                "columns": [col.strip() for col in columns.split(",")],
                "values": parse_json_param(values),
            }
            
            if returning:
                params["returning"] = returning
        
        if dry_run:
            display_dry_run(params, "insert", sql=None, format_type=format)
        else:
            result = execute_query("insert", params, config_file)
            
            if show_request:
                display_request_and_result(params, "insert", result, sql=None, format_type=format)
            else:
                display_result(result, format)
            
    except IPTVPortalError as e:
        console.print(f"[bold red]Query failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)

@jsonsql_app.command(name="update")
def update_command(
    # Native JSONSQL parameters
    table: Optional[str] = typer.Option(None, "--table", help="Table name"),
    set_: Optional[str] = typer.Option(None, "--set", help="SET clause (JSON object)"),
    where: Optional[str] = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    returning: Optional[str] = typer.Option(None, "--returning", help="Columns to return"),
    
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(False, "--show-request", help="Show JSON-RPC request along with result"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Execute UPDATE query.
    
    Examples:
        # Native mode
        iptvportal jsonsql update --table subscriber --set '{"disabled": true}' --where '{"eq": ["username", "test"]}'
        
        # Editor mode
        iptvportal jsonsql update --edit
    """
    try:
        if edit:
            # Editor mode
            if any([table, set_, where, returning]):
                console.print("[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]")
            
            template = json.dumps({
                "table": "table_name",
                "set": {"column": "value"},
                "where": {"eq": ["id", 123]}
            }, indent=2)
            
            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
        else:
            # Native mode
            if not table or not set_:
                console.print("[red]Error: --table and --set are required when not using --edit[/red]")
                raise typer.Exit(1)
            
            params = {
                "table": table,
                "set": parse_json_param(set_),
            }
            
            if where:
                params["where"] = parse_json_param(where)
            
            if returning:
                params["returning"] = returning
        
        if dry_run:
            display_dry_run(params, "update", sql=None, format_type=format)
        else:
            result = execute_query("update", params, config_file)
            
            if show_request:
                display_request_and_result(params, "update", result, sql=None, format_type=format)
            else:
                display_result(result, format)
            
    except IPTVPortalError as e:
        console.print(f"[bold red]Query failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)

@jsonsql_app.command(name="delete")
def delete_command(
    # Native JSONSQL parameters
    from_: Optional[str] = typer.Option(None, "--from", help="Table name"),
    where: Optional[str] = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    returning: Optional[str] = typer.Option(None, "--returning", help="Columns to return"),
    
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(False, "--show-request", help="Show JSON-RPC request along with result"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Execute DELETE query.
    
    Examples:
        # Native mode
        iptvportal jsonsql delete --from terminal --where '{"eq": ["id", 123]}'
        
        # Editor mode
        iptvportal jsonsql delete --edit
    """
    try:
        if edit:
            # Editor mode
            if any([from_, where, returning]):
                console.print("[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]")
            
            template = json.dumps({
                "from": "table_name",
                "where": {"eq": ["id", 123]}
            }, indent=2)
            
            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
        else:
            # Native mode
            if not from_:
                console.print("[red]Error: --from is required when not using --edit[/red]")
                raise typer.Exit(1)
            
            params = {"from": from_}
            
            if where:
                params["where"] = parse_json_param(where)
            
            if returning:
                params["returning"] = returning
        
        if dry_run:
            display_dry_run(params, "delete", sql=None, format_type=format)
        else:
            result = execute_query("delete", params, config_file)
            
            if show_request:
                display_request_and_result(params, "delete", result, sql=None, format_type=format)
            else:
                display_result(result, format)
            
    except IPTVPortalError as e:
        console.print(f"[bold red]Query failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)
