"""JSONSQL commands (select, insert, update, delete) and API subcommands."""

import json
from typing import Any

import typer
from rich.console import Console

from iptvportal.cli.core.editor import open_jsonsql_editor
from iptvportal.cli.formatters import (
    display_dry_run,
    display_request_and_result,
    display_result,
)
from iptvportal.cli.utils import execute_query, parse_json_param
from iptvportal.exceptions import IPTVPortalError

console = Console()
jsonsql_app = typer.Typer(
    name="jsonsql",
    help="JSONSQL API operations and queries",
    no_args_is_help=True,
)


def build_select_params(
    data: str | None,
    from_: str | None,
    where: str | None,
    order_by: str | None,
    limit: int | None,
    offset: int | None,
    distinct: bool,
    group_by: str | None,
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
    data: str | None = typer.Option(None, "--data", help="Columns to select (comma-separated)"),
    from_: str | None = typer.Option(None, "--from", help="Table name"),
    where: str | None = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    order_by: str | None = typer.Option(None, "--order-by", help="ORDER BY column"),
    limit: int | None = typer.Option(None, "--limit", help="LIMIT rows"),
    offset: int | None = typer.Option(None, "--offset", help="OFFSET rows"),
    distinct: bool = typer.Option(False, "--distinct", help="SELECT DISTINCT"),
    group_by: str | None = typer.Option(None, "--group-by", help="GROUP BY column"),
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(
        False,
        "--show-request",
        help="Show JSON-RPC request along with result",
    ),
    output_format: str = typer.Option("table", "--format", help="Output format: table, json, yaml"),
    map_schema: bool = typer.Option(
        True,
        "--map-schema/--no-map-schema",
        help=(
            "Enable or disable schema-based column mapping for results "
            "(auto-generate schema if missing)"
        ),
    ),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    # Debug options
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed step-by-step logging",
    ),
    debug_format: str = typer.Option(
        "text",
        "--debug-format",
        help="Debug output format: text, json, yaml",
    ),
    debug_file: str | None = typer.Option(
        None,
        "--debug-file",
        help="Save debug logs to file",
    ),
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

        # Debug mode
        iptvportal jsonsql select --from subscriber --limit 5 --debug
    """
    from iptvportal.cli.debug import DebugLogger

    # Initialize debug logger
    debug_logger = DebugLogger(
        enabled=debug,
        format_type=debug_format,
        output_file=debug_file,
    )

    try:
        if edit:
            # Editor mode: open editor for JSONSQL input
            if any([data, from_, where, order_by, limit, offset, distinct, group_by]):
                console.print(
                    "[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]"
                )

            # Provide template
            template = json.dumps(
                {
                    "data": ["*"],
                    "from": "table_name",
                    "where": {"eq": ["column", "value"]},
                    "limit": 10,
                },
                indent=2,
            )

            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
            debug_logger.log("jsonsql_input", params, "JSONSQL Input (from editor)")
        else:
            # Native mode: build JSONSQL from parameters
            if not from_:
                console.print("[red]Error: --from is required when not using --edit[/red]")
                raise typer.Exit(1)

            params = build_select_params(
                data, from_, where, order_by, limit, offset, distinct, group_by
            )
            debug_logger.log("jsonsql_params", params, "JSONSQL Parameters (from CLI)")

        if dry_run:
            # Show what would be executed
            display_dry_run(params, "select", sql=None, format_type=output_format)
        else:
            # Execute query with optional schema mapping
            debug_logger.log("executing", "Executing SELECT query...", "Execution")
            result: Any = execute_query(
                "select",
                params,
                config_file,
                use_schema_mapping=map_schema,
                debug_logger=debug_logger,
            )
            debug_logger.log("result", result, "Query Result")

            if show_request:
                # Show request and result
                display_request_and_result(
                    params, "select", result, sql=None, format_type=output_format
                )
            else:
                # Show only result
                display_result(result, output_format)

        # Save debug logs to file if specified
        debug_logger.save_to_file()

    except IPTVPortalError as e:
        debug_logger.exception(e, "IPTVPortal error occurred")
        if debug:
            console.print(f"\n[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e
    except Exception as e:
        debug_logger.exception(e, "Unexpected error occurred")
        if debug:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e


@jsonsql_app.command(name="insert")
def insert_command(
    # Native JSONSQL parameters
    into: str | None = typer.Option(None, "--into", help="Table name"),
    columns: str | None = typer.Option(None, "--columns", help="Column names (comma-separated)"),
    values: str | None = typer.Option(None, "--values", help="Values (JSON array of arrays)"),
    returning: str | None = typer.Option(None, "--returning", help="Columns to return"),
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(
        False,
        "--show-request",
        help="Show JSON-RPC request along with result",
    ),
    output_format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    # Debug options
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed step-by-step logging",
    ),
    debug_format: str = typer.Option(
        "text",
        "--debug-format",
        help="Debug output format: text, json, yaml",
    ),
    debug_file: str | None = typer.Option(
        None,
        "--debug-file",
        help="Save debug logs to file",
    ),
) -> None:
    """
    Execute INSERT query.

    Examples:
        # Native mode
        iptvportal jsonsql insert --into package --columns "name,paid" --values '[["movie", true]]' --returning id

        # Editor mode
        iptvportal jsonsql insert --edit

        # Debug mode
        iptvportal jsonsql insert --into package --columns "name,paid" --values '[["movie", true]]' --debug
    """
    from iptvportal.cli.debug import DebugLogger

    # Initialize debug logger
    debug_logger = DebugLogger(
        enabled=debug,
        format_type=debug_format,
        output_file=debug_file,
    )

    try:
        if edit:
            # Editor mode
            if any([into, columns, values, returning]):
                console.print(
                    "[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]"
                )

            template = json.dumps(
                {
                    "into": "table_name",
                    "columns": ["column1", "column2"],
                    "values": [["value1", "value2"]],
                    "returning": "id",
                },
                indent=2,
            )

            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
            debug_logger.log("jsonsql_input", params, "JSONSQL Input (from editor)")
        else:
            # Native mode
            if not into or not columns or not values:
                console.print(
                    "[red]Error: --into, --columns, and --values are required when not using --edit[/red]"
                )
                raise typer.Exit(1)

            params = {
                "into": into,
                "columns": [col.strip() for col in columns.split(",")],
                "values": parse_json_param(values),
            }

            if returning:
                params["returning"] = returning

            debug_logger.log("jsonsql_params", params, "JSONSQL Parameters (from CLI)")

        if dry_run:
            display_dry_run(params, "insert", sql=None, format_type=output_format)
        else:
            debug_logger.log("executing", "Executing INSERT query...", "Execution")
            result = execute_query("insert", params, config_file, debug_logger=debug_logger)
            debug_logger.log("result", result, "Query Result")

            if show_request:
                display_request_and_result(
                    params, "insert", result, sql=None, format_type=output_format
                )
            else:
                display_result(result, output_format)

        # Save debug logs to file if specified
        debug_logger.save_to_file()

    except IPTVPortalError as e:
        debug_logger.exception(e, "IPTVPortal error occurred")
        if debug:
            console.print(f"\n[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e
    except Exception as e:
        debug_logger.exception(e, "Unexpected error occurred")
        if debug:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e


@jsonsql_app.command(name="update")
def update_command(
    # Native JSONSQL parameters
    table: str | None = typer.Option(None, "--table", help="Table name"),
    set_: str | None = typer.Option(None, "--set", help="SET clause (JSON object)"),
    where: str | None = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    returning: str | None = typer.Option(None, "--returning", help="Columns to return"),
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(
        False,
        "--show-request",
        help="Show JSON-RPC request along with result",
    ),
    output_format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    # Debug options
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed step-by-step logging",
    ),
    debug_format: str = typer.Option(
        "text",
        "--debug-format",
        help="Debug output format: text, json, yaml",
    ),
    debug_file: str | None = typer.Option(
        None,
        "--debug-file",
        help="Save debug logs to file",
    ),
) -> None:
    """
    Execute UPDATE query.

    Examples:
        # Native mode
        iptvportal jsonsql update --table subscriber --set '{"disabled": true}' --where '{"eq": ["username", "test"]}'

        # Editor mode
        iptvportal jsonsql update --edit

        # Debug mode
        iptvportal jsonsql update --table subscriber --set '{"disabled": true}' --where '{"eq": ["username", "test"]}' --debug
    """
    from iptvportal.cli.debug import DebugLogger

    # Initialize debug logger
    debug_logger = DebugLogger(
        enabled=debug,
        format_type=debug_format,
        output_file=debug_file,
    )

    try:
        if edit:
            # Editor mode
            if any([table, set_, where, returning]):
                console.print(
                    "[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]"
                )

            template = json.dumps(
                {"table": "table_name", "set": {"column": "value"}, "where": {"eq": ["id", 123]}},
                indent=2,
            )

            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
            debug_logger.log("jsonsql_input", params, "JSONSQL Input (from editor)")
        else:
            # Native mode
            if not table or not set_:
                console.print(
                    "[red]Error: --table and --set are required when not using --edit[/red]"
                )
                raise typer.Exit(1)

            params = {
                "table": table,
                "set": parse_json_param(set_),
            }

            if where:
                params["where"] = parse_json_param(where)

            if returning:
                params["returning"] = returning

            debug_logger.log("jsonsql_params", params, "JSONSQL Parameters (from CLI)")

        if dry_run:
            display_dry_run(params, "update", sql=None, format_type=output_format)
        else:
            debug_logger.log("executing", "Executing UPDATE query...", "Execution")
            result = execute_query("update", params, config_file, debug_logger=debug_logger)
            debug_logger.log("result", result, "Query Result")

            if show_request:
                display_request_and_result(
                    params, "update", result, sql=None, format_type=output_format
                )
            else:
                display_result(result, output_format)

        # Save debug logs to file if specified
        debug_logger.save_to_file()

    except IPTVPortalError as e:
        debug_logger.exception(e, "IPTVPortal error occurred")
        if debug:
            console.print(f"\n[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e
    except Exception as e:
        debug_logger.exception(e, "Unexpected error occurred")
        if debug:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e


# Utilities subcommands (offline helpers)
utils_app = typer.Typer(name="utils", help="JSONSQL utilities")


@utils_app.command(name="transpile")
def utils_transpile(
    sql: str | None = typer.Argument(None, help="SQL query to transpile"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    file: str | None = typer.Option(None, "--file", help="Read SQL from file instead"),
) -> None:
    """
    Transpile SQL to JSONSQL format without executing it.
    """
    from iptvportal.cli.commands.transpile import transpile_command as transpile_impl

    if sql is None and file is None:
        console.print("[red]Error: Either SQL query or --file is required[/red]")
        raise typer.Exit(1)

    try:
        if file:
            with open(file) as f:
                sql_content = f.read()
            transpile_impl(sql=sql_content, format=format, file=None)
        else:
            transpile_impl(sql=sql or "", format=format, file=None)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)
    except PermissionError:
        console.print(f"[red]Error:[/red] Permission denied reading file: {file}")
        raise typer.Exit(1)
    except OSError as exc:
        console.print(f"[red]Error:[/red] Failed to read file: {exc}")
        raise typer.Exit(1)


# JSONSQL-specific configuration placeholder
config_app = typer.Typer(name="config", help="JSONSQL configuration")


@jsonsql_app.command(name="delete")
def delete_command(
    # Native JSONSQL parameters
    from_: str | None = typer.Option(None, "--from", help="Table name"),
    where: str | None = typer.Option(None, "--where", help="WHERE condition (JSONSQL format)"),
    returning: str | None = typer.Option(None, "--returning", help="Columns to return"),
    # Editor mode
    edit: bool = typer.Option(False, "--edit", "-e", help="Open editor to write JSONSQL query"),
    # Common options
    dry_run: bool = typer.Option(False, "--dry-run", help="Show query without executing"),
    show_request: bool = typer.Option(
        False,
        "--show-request",
        help="Show JSON-RPC request along with result",
    ),
    output_format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
    # Debug options
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed step-by-step logging",
    ),
    debug_format: str = typer.Option(
        "text",
        "--debug-format",
        help="Debug output format: text, json, yaml",
    ),
    debug_file: str | None = typer.Option(
        None,
        "--debug-file",
        help="Save debug logs to file",
    ),
) -> None:
    """
    Execute DELETE query.

    Examples:
        # Native mode
        iptvportal jsonsql delete --from terminal --where '{"eq": ["id", 123]}'

        # Editor mode
        iptvportal jsonsql delete --edit

        # Debug mode
        iptvportal jsonsql delete --from terminal --where '{"eq": ["id", 123]}' --debug
    """
    from iptvportal.cli.debug import DebugLogger

    # Initialize debug logger
    debug_logger = DebugLogger(
        enabled=debug,
        format_type=debug_format,
        output_file=debug_file,
    )

    try:
        if edit:
            # Editor mode
            if any([from_, where, returning]):
                console.print(
                    "[yellow]Warning: CLI parameters will be ignored when using --edit[/yellow]"
                )

            template = json.dumps({"from": "table_name", "where": {"eq": ["id", 123]}}, indent=2)

            jsonsql_str = open_jsonsql_editor(template)
            params = json.loads(jsonsql_str)
            debug_logger.log("jsonsql_input", params, "JSONSQL Input (from editor)")
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

            debug_logger.log("jsonsql_params", params, "JSONSQL Parameters (from CLI)")

        if dry_run:
            display_dry_run(params, "delete", sql=None, format_type=output_format)
        else:
            debug_logger.log("executing", "Executing DELETE query...", "Execution")
            result = execute_query("delete", params, config_file, debug_logger=debug_logger)
            debug_logger.log("result", result, "Query Result")

            if show_request:
                display_request_and_result(
                    params, "delete", result, sql=None, format_type=output_format
                )
            else:
                display_result(result, output_format)

        # Save debug logs to file if specified
        debug_logger.save_to_file()

    except IPTVPortalError as e:
        debug_logger.exception(e, "IPTVPortal error occurred")
        if debug:
            console.print(f"\n[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Query failed:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e
    except Exception as e:
        debug_logger.exception(e, "Unexpected error occurred")
        if debug:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]See debug output above for details[/yellow]")
        else:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")
            console.print("[yellow]Tip: Use --debug flag for detailed error information[/yellow]")
        raise typer.Exit(1) from e


# Register subcommands under jsonsql
# These imports are at the end to avoid circular dependencies
def _register_subcommands() -> None:
    """Register API subcommands under jsonsql."""
    from iptvportal.cli.commands.auth import auth_command
    from iptvportal.cli.commands.schema import schema_app
    from iptvportal.cli.commands.sql import sql_app
    from iptvportal.cli.commands.transpile import transpile_command

    # Register as subcommands
    jsonsql_app.command(name="auth", help="Check authentication or renew session")(auth_command)
    jsonsql_app.command(name="transpile", help="Transpile SQL to JSONSQL format")(
        transpile_command
    )
    jsonsql_app.add_typer(utils_app, name="utils")
    jsonsql_app.add_typer(config_app, name="config")
    jsonsql_app.add_typer(sql_app, name="sql")
    jsonsql_app.add_typer(schema_app, name="schema")


# Register subcommands when module is imported
_register_subcommands()
