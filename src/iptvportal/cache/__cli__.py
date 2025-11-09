"""Cache service CLI commands."""

import typer
from rich.console import Console
from rich.table import Table

from iptvportal.cli.utils import load_config
from iptvportal.core.client import IPTVPortalClient

console = Console()
app = typer.Typer(name="cache", help="Cache management service")


@app.command()
def status(
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Show cache status and statistics."""
    settings = load_config(config_file)

    if not settings.enable_query_cache:
        console.print("[yellow]Query cache is disabled in settings[/yellow]")
        return

    try:
        with IPTVPortalClient(settings) as client:
            if not client._cache:
                console.print("[yellow]Cache is not initialized[/yellow]")
                return

            # Get statistics
            stats = client._cache.get_stats()

            # Display statistics in a table
            table = Table(
                title="Query Cache Statistics", show_header=True, header_style="bold cyan"
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="green")

            table.add_row("Cache Size", f"{stats['size']} / {stats['max_size']}")
            table.add_row("Hit Rate", f"{stats['hit_rate']}%")
            table.add_row("Cache Hits", str(stats["hits"]))
            table.add_row("Cache Misses", str(stats["misses"]))
            table.add_row("Total Requests", str(stats["total_requests"]))
            table.add_row("Evictions", str(stats["evictions"]))

            console.print(table)

            # Display cache efficiency assessment
            if stats["total_requests"] > 0:
                if stats["hit_rate"] >= 80:
                    console.print("\n[green]✓ Cache is performing well![/green]")
                elif stats["hit_rate"] >= 50:
                    console.print("\n[yellow]⚠ Cache hit rate could be improved[/yellow]")
                else:
                    console.print(
                        "\n[red]⚠ Low cache hit rate - consider adjusting cache settings[/red]"
                    )

    except Exception as e:
        console.print(f"[red]Error getting cache status:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def clear(
    table: str | None = typer.Argument(
        None, help="Table name to clear (omit for all tables)"
    ),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """
    Clear the query result cache.

    Examples:
        # Clear all cached results
        iptvportal cache clear

        # Clear cache for specific table
        iptvportal cache clear subscriber
    """
    settings = load_config(config_file)

    if not settings.enable_query_cache:
        console.print("[yellow]Query cache is disabled in settings[/yellow]")
        return

    try:
        with IPTVPortalClient(settings) as client:
            if not client._cache:
                console.print("[yellow]Cache is not initialized[/yellow]")
                return

            # Clear cache
            cleared_count = client._cache.clear(table_name=table)

            if table:
                console.print(
                    f"[green]✓ Cleared {cleared_count} cached entries for table: {table}[/green]"
                )
            else:
                console.print(f"[green]✓ Cleared {cleared_count} cached entries[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def vacuum(
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Optimize cache database (for sync cache)."""
    console.print("[yellow]Cache vacuum is available via 'iptvportal sync vacuum'[/yellow]")
    console.print("[dim]This command manages query result cache only[/dim]")


# Cache-specific configuration
config_app = typer.Typer(name="config", help="Cache configuration")


@config_app.command(name="show")
def config_show(
    path: str | None = typer.Argument(None, help="Config path (e.g., 'cache.ttl')"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Show cache configuration."""
    settings = load_config(config_file)

    # Display cache configuration
    table = Table(title="Cache Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", justify="right")

    if path:
        # Show specific setting
        console.print(f"[yellow]Specific cache config path '{path}' not yet implemented[/yellow]")
    else:
        # Show all cache settings
        table.add_row(
            "Enabled", "[green]Yes[/green]" if settings.enable_query_cache else "[red]No[/red]"
        )
        table.add_row("Max Size", str(settings.cache_max_size))
        table.add_row("TTL", f"{settings.cache_ttl} seconds")

        console.print(table)

        if settings.enable_query_cache:
            console.print("\n[dim]Cache stores query results to avoid repeated API calls[/dim]")
            console.print("[dim]Only SELECT queries are cached[/dim]")
        else:
            console.print(
                "\n[yellow]Set IPTVPORTAL_ENABLE_QUERY_CACHE=true to enable caching[/yellow]"
            )


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., 'ttl', 'max_size')"),
    value: str = typer.Argument(..., help="Config value"),
) -> None:
    """Set cache configuration value."""
    console.print(
        f"[yellow]Runtime cache config setting not yet implemented: cache.{key} = {value}[/yellow]"
    )
    console.print("[dim]Use environment variables: IPTVPORTAL_CACHE_TTL, etc.[/dim]")


@config_app.command(name="get")
def config_get(
    key: str = typer.Argument(..., help="Config key"),
    config_file: str | None = typer.Option(None, "--config", help="Config file path"),
) -> None:
    """Get cache configuration value."""
    settings = load_config(config_file)

    # Map key to setting attribute
    key_map = {
        "enabled": "enable_query_cache",
        "ttl": "cache_ttl",
        "max_size": "cache_max_size",
    }

    attr = key_map.get(key, f"cache_{key}")

    if hasattr(settings, attr):
        value = getattr(settings, attr)
        console.print(f"cache.{key} = {value}")
    else:
        console.print(f"[yellow]Unknown cache config key: {key}[/yellow]")
        console.print("[dim]Available keys: enabled, ttl, max_size[/dim]")


app.add_typer(config_app)
