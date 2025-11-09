"""Main CLI entry point."""

import contextlib

import typer
from rich.console import Console

from iptvportal.cli.commands.auth import auth_command
from iptvportal.cli.commands.cache import cache_app
from iptvportal.cli.commands.config import config_app
from iptvportal.cli.commands.jsonsql import jsonsql_app
from iptvportal.cli.commands.schema import schema_app
from iptvportal.cli.commands.sql import sql_app
from iptvportal.cli.commands.sync import app as sync_app
from iptvportal.cli.commands.transpile import transpile_command

console = Console()

app = typer.Typer(
    name="iptvportal",
    help="IPTVPortal JSONSQL API Client CLI",
    no_args_is_help=True,
)

# Register commands
app.command(name="auth", help="Check authentication or renew session")(auth_command)
app.command(name="transpile", help="Transpile SQL to JSONSQL format")(transpile_command)

# Register subapps
app.add_typer(config_app, name="config")
app.add_typer(sql_app, name="sql")
app.add_typer(jsonsql_app, name="jsonsql")
app.add_typer(schema_app, name="schema")
app.add_typer(cache_app, name="cache")
app.add_typer(sync_app, name="sync")

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
