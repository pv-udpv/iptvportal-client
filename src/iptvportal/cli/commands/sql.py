"""SQL subapp for executing SQL queries via transpiler."""

import typer
from rich.console import Console

from iptvportal.cli.core.editor import open_sql_editor
from iptvportal.cli.formatters import (
    display_result,
    display_dry_run,
    display_request_and_result,
)
from iptvportal.cli.utils import execute_query
from iptvportal.exceptions import IPTVPortalError
from iptvportal.transpiler import SQLTranspiler

console = Console()

sql_app = typer.Typer(
    name="sql",
    help="Execute SQL queries (auto-transpiled to JSONSQL)",
    no_args_is_help=True,
)


@sql_app.callback(invoke_without_command=True)
def sql_main(
    ctx: typer.Context,
    query: str | None = typer.Option(None, "--query", "-q", help="SQL query to execute"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write SQL query"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show transpiled query without executing"
    ),
    show_request: bool = typer.Option(
        False, "--show-request", help="Show JSON-RPC request along with result"
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, yaml",
    ),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    map_schema: bool = typer.Option(
        True,
        "--map-schema/--no-map-schema",
        "-m/-M",
        help=(
            "Enable or disable schema-based column mapping for results "
            "(auto-generate schema if missing)"
        ),
    ),
) -> None:
    """
    Execute SQL query (auto-transpiled to JSONSQL).

    Examples:
        # Execute SQL query directly
        iptvportal sql --query "SELECT * FROM subscriber LIMIT 10"
        iptvportal sql -q "SELECT id, username FROM subscriber WHERE disabled = false"

        # Open editor to write query
        iptvportal sql --edit
        iptvportal sql -e

        # Dry-run mode (show transpiled JSONSQL without executing)
        iptvportal sql -q "SELECT * FROM subscriber" --dry-run

        # Different output formats
        iptvportal sql -q "SELECT * FROM subscriber" --format json
        iptvportal sql -q "SELECT * FROM subscriber" -f yaml

    # Disable schema mapping (if you need raw column inference)
    iptvportal sql -q "SELECT * FROM media LIMIT 10" --no-map-schema
    iptvportal sql -q "SELECT * FROM media" -M
    """
    # If no subcommand and ctx is being invoked
    if ctx.invoked_subcommand is not None:
        return

    try:
        sql_query: str | None = None

        # Get SQL query from --query or --edit
        if edit:
            if query:
                console.print("[yellow]Warning: --query will be ignored when using --edit[/yellow]")
            sql_query = open_sql_editor()
        elif query:
            sql_query = query
        else:
            console.print("[red]Error: Either --query/-q or --edit/-e is required[/red]")
            raise typer.Exit(1)

        # Transpile SQL to JSONSQL
        transpiler = SQLTranspiler()
        result = transpiler.transpile(sql_query)

        # Determine method from transpiled result
        method = result.get("_method", "select")  # Default to select if not specified
        if "_method" in result:
            del result["_method"]

        # Infer method from JSONSQL structure if _method not present
        if "into" in result:
            method = "insert"
        elif "table" in result and "set" in result:
            method = "update"
        elif "from" in result and any(k in result for k in ["data", "where", "order_by", "limit"]):
            method = "select"

        if dry_run:
            # Show transpiled query without executing
            display_dry_run(result, method, sql=sql_query, format_type=output_format)
        else:
            # Execute query with optional schema mapping
            query_result = execute_query(method, result, config_file, use_schema_mapping=map_schema)

            if show_request:
                # Show request and result
                display_request_and_result(
                    result, method, query_result, sql=sql_query, format_type=output_format
                )
            else:
                # Show only result
                display_result(query_result, output_format)

    except IPTVPortalError as e:
        console.print(f"[bold red]Query failed:[/bold red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1) from e
