"""Main CLI entry point."""

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

def main() -> None:
    """Main entry point."""
    app()

if __name__ == "__main__":
    main()
