"""JSONSQL service CLI commands."""

import json

import typer
from rich.console import Console

console = Console()
app = typer.Typer(name="jsonsql", help="JSONSQL API operations")


# Import and register auth command
@app.command(name="auth")
def auth_command(
    renew: bool = typer.Option(False, "--renew", help="Force re-authentication"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Check authentication status or renew session.

    Examples:
        iptvportal jsonsql auth              # Check current session
        iptvportal jsonsql auth --renew      # Force re-authentication
    """
    from iptvportal.cli.commands.auth import auth_command as auth_impl

    auth_impl(renew=renew, config_file=config_file)


# Register SQL command as a subcommand
from iptvportal.cli.commands.sql import sql_app

app.add_typer(sql_app, name="sql")


# Native JSONSQL commands (keep existing)
from iptvportal.cli.commands.jsonsql import (
    delete_command,
    insert_command,
    select_command,
    update_command,
)

app.command(name="select")(select_command)
app.command(name="insert")(insert_command)
app.command(name="update")(update_command)
app.command(name="delete")(delete_command)


# Utilities subcommand
utils_app = typer.Typer(name="utils", help="JSONSQL utilities (offline)")


@utils_app.command(name="transpile")
def transpile_command(
    sql: str | None = typer.Argument(None, help="SQL query to transpile"),
    format: str = typer.Option("json", "--format", help="Output format: json, yaml"),
    file: str | None = typer.Option(None, "--file", help="Read SQL from file instead"),
) -> None:
    """
    Transpile SQL to JSONSQL format (without executing).

    Examples:
        iptvportal jsonsql utils transpile "SELECT * FROM subscriber"
        iptvportal jsonsql utils transpile --file query.sql --format yaml
    """
    from iptvportal.cli.commands.transpile import transpile_command as transpile_impl

    if sql is None and file is None:
        console.print("[red]Error: Either SQL query or --file is required[/red]")
        raise typer.Exit(1)

    transpile_impl(sql=sql or "", format=format, file=file)


@utils_app.command(name="validate")
def validate_command(query: str = typer.Argument(..., help="JSONSQL query to validate")) -> None:
    """
    Validate JSONSQL syntax.

    Examples:
        iptvportal jsonsql utils validate '{"from": "subscriber", "data": ["*"]}'
    """
    try:
        parsed = json.loads(query)
        console.print("[green]✓ Valid JSONSQL syntax[/green]")
        console.print(f"[dim]Method detected: {_detect_method(parsed)}[/dim]")
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ Validation error: {e}[/red]")
        raise typer.Exit(1)


@utils_app.command(name="format")
def format_cmd(
    query: str = typer.Argument(..., help="JSONSQL query to format"),
    indent: int = typer.Option(2, "--indent", help="Indentation spaces"),
) -> None:
    """
    Pretty-print JSONSQL.

    Examples:
        iptvportal jsonsql utils format '{"from":"subscriber","data":["*"]}'
    """
    try:
        parsed = json.loads(query)
        formatted = json.dumps(parsed, indent=indent)
        console.print(formatted)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON: {e}[/red]")
        raise typer.Exit(1)


def _detect_method(jsonsql: dict) -> str:
    """Detect JSONSQL method from structure."""
    if "into" in jsonsql:
        return "insert"
    elif "table" in jsonsql and "set" in jsonsql:
        return "update"
    elif "from" in jsonsql and ("data" in jsonsql or "where" in jsonsql):
        return "select"
    elif "from" in jsonsql:
        return "delete"
    return "unknown"


app.add_typer(utils_app)


# JSONSQL-specific configuration
config_app = typer.Typer(name="config", help="JSONSQL configuration")


@config_app.command(name="show")
def config_show(
    path: str | None = typer.Argument(None, help="Config path"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Show JSONSQL/API configuration."""
    from iptvportal.cli.utils import load_config
    from rich.table import Table

    settings = load_config(config_file)

    # Display JSONSQL/API configuration
    table = Table(title="JSONSQL API Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", justify="right")

    if path:
        console.print(f"[yellow]Specific config path '{path}' not yet implemented[/yellow]")
    else:
        # Show API settings
        table.add_row("API URL", settings.api_url)
        table.add_row("Auth URL", settings.auth_url)
        table.add_row("Timeout", f"{settings.timeout}s")
        table.add_row("Max Retries", str(settings.max_retries))
        table.add_row("Retry Delay", f"{settings.retry_delay}s")
        table.add_row("Verify SSL", str(settings.verify_ssl))

        console.print(table)


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value"),
) -> None:
    """Set JSONSQL configuration value."""
    console.print(
        f"[yellow]Runtime jsonsql config setting not yet implemented: jsonsql.{key} = {value}[/yellow]"
    )
    console.print("[dim]Use environment variables or configuration files[/dim]")


@config_app.command(name="get")
def config_get(
    key: str = typer.Argument(..., help="Config key"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Get JSONSQL configuration value."""
    from iptvportal.cli.utils import load_config

    settings = load_config(config_file)

    # Map common keys to settings attributes
    key_map = {
        "api_url": "api_url",
        "auth_url": "auth_url",
        "timeout": "timeout",
        "max_retries": "max_retries",
        "retry_delay": "retry_delay",
        "verify_ssl": "verify_ssl",
    }

    attr = key_map.get(key)

    if attr and hasattr(settings, attr):
        value = getattr(settings, attr)
        console.print(f"jsonsql.{key} = {value}")
    else:
        console.print(f"[yellow]Unknown jsonsql config key: {key}[/yellow]")
        console.print(
            "[dim]Available keys: api_url, auth_url, timeout, max_retries, retry_delay, verify_ssl[/dim]"
        )


app.add_typer(config_app)
