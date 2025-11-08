"""Auth command for CLI."""

from typing import Optional

import typer
from rich.console import Console

from iptvportal.config import IPTVPortalSettings
from iptvportal.client import IPTVPortalClient
from iptvportal.exceptions import IPTVPortalError

console = Console()

def auth_command(
    renew: bool = typer.Option(False, "--renew", help="Force re-authentication"),
    config_file: Optional[str] = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Check authentication status or renew session.
    
    Examples:
        iptvportal auth              # Check current session
        iptvportal auth --renew      # Force re-authentication
    """
    try:
        # Load configuration
        if config_file:
            console.print("[yellow]Custom config file support not yet implemented[/yellow]")
        
        settings = IPTVPortalSettings()
        
        console.print("\n[bold cyan]IPTVPortal Authentication[/bold cyan]\n")
        console.print(f"[bold]Domain:[/bold] {settings.domain}")
        console.print(f"[bold]Username:[/bold] {settings.username}")
        console.print(f"[bold]Auth URL:[/bold] {settings.auth_url}")
        console.print(f"[bold]API URL:[/bold] {settings.api_url}")
        console.print()
        
        # Test connection
        console.print("[bold]Testing connection...[/bold]")
        
        with IPTVPortalClient(settings) as client:
            console.print("[green]✓ Authentication successful[/green]")
            console.print(f"[bold]Session ID:[/bold] {client._session_id}")
            console.print()
            console.print("[green]Connection is working properly[/green]")
            
    except IPTVPortalError as e:
        console.print(f"\n[bold red]Authentication failed:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(1)
