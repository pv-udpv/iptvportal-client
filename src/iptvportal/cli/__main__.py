"""Main CLI entry point with auto-discovery."""

import contextlib

import typer
from rich.console import Console

from iptvportal.cli.commands.cache import cache_app
from iptvportal.cli.commands.config import config_app
from iptvportal.cli.commands.jsonsql import jsonsql_app
from iptvportal.cli.commands.sync import app as sync_app
from iptvportal.cli.discovery import discover_cli_modules

console = Console()

app = typer.Typer(
    name="iptvportal",
    help="IPTVPortal JSONSQL API Client CLI",
    no_args_is_help=True,
)

# Register infrastructure commands (top-level)
app.add_typer(config_app, name="config")
app.add_typer(cache_app, name="cache")
# Auto-discover and register all service CLI modules
discovered = discover_cli_modules("iptvportal", verbose=False)
for service_name, service_app in discovered.items():
    app.add_typer(service_app, name=service_name)

# Keep sync subapp from old structure for backwards compatibility
from iptvportal.cli.commands.sync import app as sync_app

app.add_typer(sync_app, name="sync")

# Register API operations under jsonsql hierarchy
# (jsonsql_app includes: select, insert, update, delete, auth, sql, transpile, schema)
app.add_typer(jsonsql_app, name="jsonsql")


# Deprecated command redirects (hidden from help)
@app.command(name="auth", hidden=True)
def auth_deprecated() -> None:
    """Deprecated: use 'iptvportal jsonsql auth' instead."""
    console.print("[yellow]Command moved:[/yellow] iptvportal auth → iptvportal jsonsql auth")
    console.print("[dim]Run: iptvportal jsonsql auth[/dim]")
    raise typer.Exit(1)


@app.command(name="transpile", hidden=True)
def transpile_deprecated() -> None:
    """Deprecated: use 'iptvportal jsonsql transpile' instead."""
    console.print(
        "[yellow]Command moved:[/yellow] iptvportal transpile → iptvportal jsonsql transpile"
    )
    console.print("[dim]Run: iptvportal jsonsql transpile <sql>[/dim]")
    raise typer.Exit(1)


@app.command(name="sql", hidden=True)
def sql_deprecated() -> None:
    """Deprecated: use 'iptvportal jsonsql sql' instead."""
    console.print("[yellow]Command moved:[/yellow] iptvportal sql → iptvportal jsonsql sql")
    console.print("[dim]Run: iptvportal jsonsql sql --query 'SELECT ...'[/dim]")
    raise typer.Exit(1)


@app.command(name="schema", hidden=True)
def schema_deprecated() -> None:
    """Deprecated: use 'iptvportal jsonsql schema' instead."""
    console.print("[yellow]Command moved:[/yellow] iptvportal schema → iptvportal jsonsql schema")
    console.print("[dim]Run: iptvportal jsonsql schema show[/dim]")
    raise typer.Exit(1)

# Define typer Option defaults at module level to avoid calling functions in parameter defaults
LOG_LEVEL_OPTION = typer.Option(
    None,
    "--log-level",
    help="Set global logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
LOG_JSON_OPTION = typer.Option(
    False,
    "--log-json",
    help="Output logs in JSON format",
)
LOG_FILE_OPTION = typer.Option(
    None,
    "--log-file",
    help="Write logs to file",
)
VERBOSE_OPTION = typer.Option(
    None,
    "--verbose",
    "-v",
    help="Enable DEBUG logging for specific module (can be used multiple times)",
)
QUIET_OPTION = typer.Option(
    None,
    "--quiet",
    "-q",
    help="Set WARNING level for specific module (can be used multiple times)",
)


@app.callback()
def global_options(
    ctx: typer.Context,
    log_level: str | None = LOG_LEVEL_OPTION,
    log_json: bool = LOG_JSON_OPTION,
    log_file: str | None = LOG_FILE_OPTION,
    verbose: list[str] | None = VERBOSE_OPTION,
    quiet: list[str] | None = QUIET_OPTION,
) -> None:
    """
    Global CLI options for logging control.

    Applies options to the dynaconf configuration in-memory and reconfigures logging.
    This is best-effort and will not raise on failure.
    """
    try:
        from iptvportal.config import reconfigure_logging, set_module_log_level, set_value
    except Exception:
        # If config/logging not available, skip CLI-level logging changes
        return

    # Apply global log level
    if log_level:
        with contextlib.suppress(Exception):
            set_value("logging.level", str(log_level).upper())

    # Enable JSON formatting (for file output) and a top-level flag
    if log_json:
        with contextlib.suppress(Exception):
            set_value("logging.json", True)
            set_value("logging.handlers.file.json_format", True)

    # Enable file output and set path
    if log_file:
        with contextlib.suppress(Exception):
            set_value("logging.handlers.file.enabled", True)
            set_value("logging.handlers.file.path", str(log_file))

    # Per-module verbose/quiet adjustments
    if verbose:
        for module in verbose:
            with contextlib.suppress(Exception):
                # set runtime logger level immediately and persist to config
                set_module_log_level(module, "DEBUG")

    if quiet:
        for module in quiet:
            with contextlib.suppress(Exception):
                set_module_log_level(module, "WARNING")

    # Reconfigure logging to apply changes
    with contextlib.suppress(Exception):
        reconfigure_logging()


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
