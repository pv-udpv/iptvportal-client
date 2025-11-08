"""Config command for managing configuration."""

import typer
from rich.console import Console
from rich.table import Table

from iptvportal.config import IPTVPortalSettings

console = Console()
config_app = typer.Typer(name="config", help="Manage configuration")


@config_app.command(name="show")
def show_command() -> None:
    """
    Show current configuration.

    Examples:
        iptvportal config show
    """
    try:
        settings = IPTVPortalSettings()

        console.print("\n[bold cyan]IPTVPortal Configuration[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="white")
        table.add_column("Value", style="green")

        table.add_row("Domain", settings.domain)
        table.add_row("Username", settings.username)
        table.add_row("Password", "***" if settings.password else "not set")
        table.add_row("Auth URL", settings.auth_url)
        table.add_row("API URL", settings.api_url)
        table.add_row("Timeout", f"{settings.timeout}s")
        table.add_row("Max Retries", str(settings.max_retries))
        table.add_row("Retry Delay", f"{settings.retry_delay}s")
        table.add_row("Verify SSL", str(settings.verify_ssl))
        table.add_row("Session Cache", str(settings.session_cache))
        table.add_row("Session TTL", f"{settings.session_ttl}s")
        table.add_row("Log Level", settings.log_level)
        table.add_row("Log Requests", str(settings.log_requests))
        table.add_row("Log Responses", str(settings.log_responses))

        console.print(table)
        console.print()
        console.print(
            "[dim]Configuration is loaded from environment variables with IPTVPORTAL_ prefix[/dim]"
        )
        console.print("[dim]or from .env file in the current directory[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(1)


@config_app.command(name="init")
def init_command() -> None:
    """
    Initialize configuration interactively.

    Examples:
        iptvportal config init
    """
    console.print("\n[bold cyan]IPTVPortal Configuration Wizard[/bold cyan]\n")
    console.print("This wizard will help you create a .env file with your configuration.\n")

    # Prompt for required settings
    domain = typer.prompt("Operator domain (e.g., 'operator' for operator.admin.iptvportal.ru)")
    username = typer.prompt("Admin username")
    password = typer.prompt("Admin password", hide_input=True)

    # Optional settings
    console.print("\n[dim]Optional settings (press Enter to use defaults):[/dim]\n")

    timeout = typer.prompt("Request timeout in seconds", default="30.0")
    max_retries = typer.prompt("Maximum retry attempts", default="3")
    verify_ssl = typer.confirm("Verify SSL certificates?", default=True)

    # Create .env file
    env_content = f"""# IPTVPortal Configuration
IPTVPORTAL_DOMAIN={domain}
IPTVPORTAL_USERNAME={username}
IPTVPORTAL_PASSWORD={password}
IPTVPORTAL_TIMEOUT={timeout}
IPTVPORTAL_MAX_RETRIES={max_retries}
IPTVPORTAL_VERIFY_SSL={str(verify_ssl).lower()}
"""

    with open(".env", "w") as f:
        f.write(env_content)

    console.print("\n[green]✓ Configuration saved to .env file[/green]")
    console.print("\n[dim]You can now use the iptvportal CLI commands.[/dim]\n")


@config_app.command(name="set")
def set_command(
    key: str = typer.Argument(..., help="Configuration key (e.g., domain, username)"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """
    Set a configuration value in .env file.

    Examples:
        iptvportal config set domain operator
        iptvportal config set timeout 60
    """
    # Read existing .env file
    try:
        with open(".env") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    # Update or add the key
    key_upper = f"IPTVPORTAL_{key.upper()}"
    key_found = False

    for i, line in enumerate(lines):
        if line.startswith(f"{key_upper}="):
            lines[i] = f"{key_upper}={value}\n"
            key_found = True
            break

    if not key_found:
        lines.append(f"{key_upper}={value}\n")

    # Write back to .env file
    with open(".env", "w") as f:
        f.writelines(lines)

    console.print(f"[green]✓ Set {key} = {value}[/green]")


@config_app.command(name="get")
def get_command(
    key: str = typer.Argument(..., help="Configuration key (e.g., domain, username)"),
) -> None:
    """
    Get a configuration value.

    Examples:
        iptvportal config get domain
        iptvportal config get timeout
    """
    try:
        settings = IPTVPortalSettings()
        value = getattr(settings, key, None)

        if value is None:
            console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
        else:
            # Hide password
            if key == "password":
                console.print(f"{key} = ***")
            else:
                console.print(f"{key} = {value}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
